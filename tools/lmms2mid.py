#!/usr/bin/env python3
"""Convert an LMMS project (.mmpz or .mmp) into a MIDI file for cmsynth.

Usage: tools/lmms2mid.py <project.mmpz> [out.mid]

Every instrument track gets its own MIDI channel and a cmsynth patch, sent as
CCs at the start of the file.  The patch is picked from SONGS below for tracks
that need something specific, otherwise from the track's General MIDI program
(sound fonts) or, for LMMS's own synths, from the track name and note range.
Drums (sound font bank 128, or drum samples recognised by their file name) are
split over several channels, one per kind of drum, because a channel only has
one patch: kick, snare, hats, cymbals and toms each get a drum patch of their
own.  Beat/Bassline patterns are expanded where they are placed in the song.

Volume automation on a track becomes CC 7.  When there are more tracks than
channels, tracks with the same patch share a channel.  Output goes to
midi/<project>.mid by default.
"""
import os
import sys
import xml.etree.ElementTree as ET
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demos           # noqa: E402
import make_midis      # noqa: E402  (sets demos.LEVEL for files)

LMMS_TICKS_PER_BEAT = 48             # 192 per 4/4 bar
LMMS_STEP_TICKS = 12                 # A Beat/Bassline step (1/16)

# Patches in demos.patch() units, on top of the firmware defaults
PATCHES = {
    'bass': dict(osc1_range="8'", osc1_wave='saw', osc2_range="8'", osc2_wave='square', osc2_detune=0.05,
                 osc2_level=0.6, osc3_range="16'", osc3_wave='tri', osc3_level=0.4, osc3_on=1,
                 cutoff=320, emphasis=0.3, contour=0.5, kbd=1, f_attack=0.001, f_decay=0.25, f_sustain=0.2,
                 l_attack=0.002, l_decay=0.3, l_sustain=0.7, decay_sw=0, drive=0.2),
    'synthbass': dict(osc1_range="8'", osc1_wave='saw', osc2_range="8'", osc2_wave='saw', osc2_detune=0.1,
                      cutoff=450, emphasis=0.6, contour=0.6, kbd=1, f_attack=0.001, f_decay=0.2, f_sustain=0.1,
                      l_attack=0.002, l_decay=0.3, l_sustain=0.7, decay_sw=0, drive=0.3),
    'pluck': dict(osc1_range="8'", osc1_wave='narrow', osc2_on=0, cutoff=600, emphasis=0.7, contour=0.7, kbd=3,
                  f_attack=0.001, f_decay=0.18, f_sustain=0.0, l_attack=0.001, l_decay=0.4, l_sustain=0.0,
                  decay_sw=1),
    'organ': dict(osc1_range="8'", osc1_wave='square', osc2_range="4'", osc2_wave='square', osc2_detune=0.0,
                  osc2_level=0.5, osc3_range="16'", osc3_wave='tri', osc3_level=0.4, osc3_on=1,
                  cutoff=3000, emphasis=0.0, contour=0.0, kbd=2, l_attack=0.003, l_decay=0.08, l_sustain=1.0,
                  decay_sw=1),
    'pad': dict(osc1_range="8'", osc1_wave='trisaw', osc2_range="8'", osc2_wave='saw', osc2_detune=-0.12,
                osc1_level=0.6, osc2_level=0.5, cutoff=1000, emphasis=0.15, contour=0.2, kbd=2,
                f_attack=0.3, f_decay=1.0, f_sustain=0.7, l_attack=0.15, l_decay=0.8, l_sustain=0.9, decay_sw=1),
    'brass': dict(osc1_range="8'", osc1_wave='saw', osc2_range="8'", osc2_wave='saw', osc2_detune=0.08,
                  cutoff=500, emphasis=0.2, contour=0.6, kbd=2, f_attack=0.06, f_decay=0.4, f_sustain=0.5,
                  l_attack=0.02, l_decay=0.3, l_sustain=0.9, decay_sw=1),
    'reed': dict(osc1_range="8'", osc1_wave='wide', osc2_range="8'", osc2_wave='tri', osc2_level=0.6,
                 osc2_detune=0.04, cutoff=1500, emphasis=0.15, contour=0.2, kbd=2, f_decay=0.5, f_sustain=0.6,
                 l_attack=0.02, l_decay=0.3, l_sustain=0.8, decay_sw=1),
    'lead': dict(osc1_range="8'", osc1_wave='saw', osc2_range="8'", osc2_wave='square', osc2_detune=0.06,
                 osc2_level=0.6, cutoff=1800, emphasis=0.35, contour=0.3, kbd=2, f_decay=0.6, f_sustain=0.6,
                 l_attack=0.01, l_decay=0.5, l_sustain=0.9, decay_sw=1),
    # The original Popcorn was a Moog. Measured from the record: each note is a ~45 ms
    # blip, ~12 ms attack then -20 dB 25 ms later, a square with weak even harmonics
    # through a filter at ~3.5x the note (3rd harmonic -14 dB, 5th -26 dB), no sweep.
    'popcorn': dict(osc1_range="8'", osc1_wave='square', osc2_range="8'", osc2_wave='saw', osc2_detune=0.0,
                    osc1_level=0.9, osc2_level=0.25, cutoff=950, emphasis=0.1, contour=0.1, kbd=3,
                    f_attack=0.001, f_decay=0.03, f_sustain=0.0, l_attack=0.012, l_decay=0.035, l_sustain=0.0,
                    decay_sw=1, volume=1.0),
    # Bowed string leads: a soft attack and a short release that joins legato notes
    'violin': dict(osc1_range="8'", osc1_wave='saw', osc2_range="8'", osc2_wave='saw', osc2_detune=0.08,
                   osc1_level=0.7, osc2_level=0.6, cutoff=1400, emphasis=0.15, contour=0.25, kbd=2,
                   f_attack=0.04, f_decay=0.5, f_sustain=0.6, l_attack=0.03, l_decay=0.25, l_sustain=0.85,
                   decay_sw=1),
    'cello': dict(osc1_range="8'", osc1_wave='saw', osc2_range="16'", osc2_wave='tri', osc2_level=0.4,
                  osc1_level=0.8, cutoff=500, emphasis=0.1, contour=0.3, kbd=1, f_attack=0.05, f_decay=0.6,
                  f_sustain=0.6, l_attack=0.04, l_decay=0.35, l_sustain=0.9, decay_sw=1),
    # TB-303 style (LMMS's LB302): one saw through a resonant, snappy filter
    'acid': dict(osc1_range="8'", osc1_wave='saw', osc2_on=0, cutoff=350, emphasis=0.75, contour=0.7, kbd=1,
                 f_attack=0.001, f_decay=0.15, f_sustain=0.05, l_attack=0.002, l_decay=0.2, l_sustain=0.8,
                 decay_sw=0, drive=0.3),
}

# Drum kit: each kind of drum on its own channel, (patch, note or None to keep the note)
DRUMS = {
    'kick': (dict(osc1_range="8'", osc1_wave='tri', osc1_level=0.8, osc2_on=0, cutoff=60, emphasis=0.85,
                  contour=0.7, kbd=0, f_attack=0.001, f_decay=0.05, f_sustain=0.0, l_attack=0.001,
                  l_decay=0.3, l_sustain=0.0, decay_sw=1, drive=0.4), 33),
    'snare': (dict(osc1_range="8'", osc1_wave='tri', osc1_level=0.5, osc2_on=0, noise_on=1, noise_level=1.0,
                   cutoff=2500, emphasis=0.2, contour=0.6, kbd=0, f_attack=0.001, f_decay=0.08, f_sustain=0.0,
                   l_attack=0.001, l_decay=0.15, l_sustain=0.0, decay_sw=1), 54),
    'hats': (dict(osc1_on=0, osc2_on=0, noise_on=1, noise_level=1.0, cutoff=6000, emphasis=0.4, contour=0.3,
                  kbd=3, f_attack=0.001, f_decay=0.05, f_sustain=0.0, l_attack=0.001, l_decay=0.06,
                  l_sustain=0.0, decay_sw=1), None),
    'cymbal': (dict(osc1_on=0, osc2_on=0, noise_on=1, noise_level=1.0, cutoff=8000, emphasis=0.5, contour=0.2,
                    kbd=0, f_attack=0.001, f_decay=0.5, f_sustain=0.0, l_attack=0.001, l_decay=0.7,
                    l_sustain=0.0, decay_sw=1), None),
    'toms': (dict(osc1_range="8'", osc1_wave='tri', osc1_level=0.8, osc2_on=0, cutoff=150, emphasis=0.8,
                  contour=0.6, kbd=3, f_attack=0.001, f_decay=0.08, f_sustain=0.0, l_attack=0.001,
                  l_decay=0.35, l_sustain=0.0, decay_sw=1, drive=0.3), None),
}
DRUM_KIND = {35: 'kick', 36: 'kick', 37: 'snare', 38: 'snare', 39: 'snare', 40: 'snare',
             41: 'toms', 43: 'toms', 45: 'toms', 47: 'toms', 48: 'toms', 50: 'toms',
             49: 'cymbal', 51: 'cymbal', 52: 'cymbal', 53: 'cymbal', 55: 'cymbal', 57: 'cymbal', 59: 'cymbal'}
DRUM_LEVEL = dict(kick=0.9, snare=0.6, hats=0.35, cymbal=0.3, toms=0.7)
# Drum samples by file name, first match wins
DRUM_SAMPLES = [('kick', ('kick', 'bassdrum', 'kik', 'k_')), ('snare', ('snare', 'clap', 'rim', 'sidestick', 's_')),
                ('hats', ('hat', 'hh', 'shaker')), ('cymbal', ('crash', 'ride', 'cymbal')),
                ('toms', ('tom', 'cga', 'conga', 'bongo'))]
# Fixed notes for drum samples (toms follow the sample's pitch)
DRUM_SAMPLE_NOTE = dict(kick=33, snare=54, hats=72, cymbal=72)
# Patches for other samples by file name, None = not converted (effects)
SAMPLES = [('mute_bass', 'bass'), ('bass', 'bass'), ('string', 'pad'), ('pad', 'pad'), ('chorus', 'pad'),
           ('piano', 'pluck'), ('instruments/', 'pluck')]
# Patches for synth tracks by name, first match wins
NAMES = [('bass', 'bass'), ('pad', 'pad'), ('string', 'pad'), ('choir', 'pad'), ('brass', 'brass'),
         ('brazz', 'brass'), ('reed', 'reed'), ('pipe', 'reed'), ('flute', 'reed'), ('organ', 'organ'),
         ('bell', 'pluck'), ('harp', 'pluck'), ('pluck', 'pluck'), ('piano', 'pluck'), ('twinkle', 'pluck'),
         ('drop', 'pluck'), ('arp', 'pluck'), ('lead', 'lead'), ('square', 'lead'), ('saw', 'lead')]

# Many channels add up: whole song level on top of each track's volume
SONG_LEVEL = 0.45
# Notes start this late, the patches are sent one channel at a time before that
LEAD_IN = 1.0
PATCH_SPACING = 0.05

# Per project overrides: track name -> patch name, or (patch name, extra settings), or 'skip'.
# The extra settings can include 'transpose' (semitones).  '_level' overrides SONG_LEVEL,
# '_name' names the MIDI file.
SONGS = {
    'popcorn2': {
        '_level': 0.4,
        'Popcorn': 'popcorn',
        'Bass 1': 'bass',
        'Synth Bass': 'synthbass',
        'Melody 2': ('pad', dict(l_attack=0.08)),
        'Arpeggio': 'pluck',
        'End Part': 'reed',
        'High Note': 'lead',
    },
    # Three violins in canon, each with its own colour and place, over the cello's ground bass
    'pachalbel canon in d - 4 voices': {
        '_name': 'canon',
        'Track 1': ('violin', dict(pan=-0.6)),
        'Track 2': ('violin', dict(osc2_wave='wide', osc2_detune=-0.06, cutoff=1200, pan=0.6)),
        'Track 3': ('violin', dict(osc1_wave='trisaw', cutoff=1700, emphasis=0.25, pan=0.0)),
        'Track 4': 'cello',
    },
    # mute_bass.ds sounds around A2, LMMS plays it 15 semitones up from its base note
    # Levels matched by recording the line out (peaks around -1 dBFS)
    'farbro-tectonic': {'_level': 0.8},
    'esoxlb-cpu': {'_level': 0.8},
    'socceroos-progress': {'_level': 0.38},
    'oglsdl-pptrip': {
        'mute_bass.ds': ('bass', dict(transpose=-24)),
    },
}


def gm_patch(program):
    """Default patch name for a General MIDI program number."""
    family = program // 8
    return {0: 'pluck', 1: 'pluck', 2: 'organ', 3: 'pluck', 4: 'bass', 5: 'pad', 6: 'pad', 7: 'brass',
            8: 'reed', 9: 'reed', 10: 'lead', 11: 'pad'}.get(family, 'pluck')


def drum_sample(src):
    """Kind of drum for a drum sample, or None."""
    name = src.lower().replace('\\', '/').split('/')[-1]
    if 'drum' not in src.lower():
        return None
    return next((kind for kind, keys in DRUM_SAMPLES if any(k in name for k in keys)), None)


def synth_patch(name, plugin, notes):
    """Patch name for a synth track from its name, plugin and notes."""
    lname = name.lower()
    keys = sorted(n[2] for n in notes)
    median = keys[len(keys) // 2]
    avg_len = sum(n[1] for n in notes) / len(notes)
    for key, patch in NAMES:
        if key in lname:
            if patch == 'bass' and plugin == 'lb302':
                return 'acid'
            if patch == 'pad' and avg_len < LMMS_TICKS_PER_BEAT:
                return 'synthbass' if median < 48 else 'pluck'   # Short notes, not really a pad
            return patch
    if plugin == 'lb302':
        return 'acid'
    if median < 48:
        return 'bass'
    if avg_len >= LMMS_TICKS_PER_BEAT and median >= 55:
        return 'pad'
    return 'lead'


def track_transpose(it):
    """Semitones to add to an LMMS key: LMMS plays A4 (MIDI 69) on the track's base note, and
    for TripleOscillator the loudest oscillator's coarse tuning."""
    shift = 69 - int(it.get('basenote', 57))
    osc = it.find('instrument/tripleoscillator')
    if osc is not None:
        # Loudest, and of equally loud ones the least transposed
        loudest = max(range(3), key=lambda i: (float(osc.get(f'vol{i}', 0)), -abs(float(osc.get(f'coarse{i}', 0)))))
        shift += round(float(osc.get(f'coarse{loudest}', 0)))
    return shift


def track_notes(track, placements):
    """(tick, length, key, volume) for an instrument track. placements is None for a song track,
    or for a Beat/Bassline track [(pattern index, song tick, length)] where the patterns are placed."""
    notes = []
    patterns = track.findall('pattern')

    def add(pat, offset, end=None, steps_len=None):
        for n in pat.findall('note'):
            t = offset + int(n.get('pos'))
            if end is not None and t >= end:
                continue
            length = int(n.get('len'))
            if length <= 0:
                length = LMMS_STEP_TICKS    # Step (one shot) note
            notes.append((t, length, int(n.get('key')), float(n.get('vol', 100))))

    if placements is None:
        for pat in patterns:
            add(pat, int(pat.get('pos')))
        return notes
    for index, pos, length, bb_len in placements:
        pat = next((p for p in patterns if int(p.get('pos')) == index * 192), None)
        if pat is None or not pat.findall('note'):
            continue
        for rep in range(0, length, bb_len):
            add(pat, pos + rep, end=pos + length)
    return notes


def load(path):
    data = open(path, 'rb').read()
    if path.endswith('.mmpz'):
        data = zlib.decompress(data[4:])        # Qt qCompress: 4 byte length, then zlib
    return ET.fromstring(data)


def model_value(elem, name, default):
    """An LMMS model is either an attribute or a child element (when automated)."""
    if elem.get(name) is not None:
        return float(elem.get(name)), None
    child = elem.find(name)
    if child is not None:
        return float(child.get('value', default)), child.get('id')
    return default, None


def convert(path):
    root = load(path)
    song = root.find('song')
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    overrides = SONGS.get(stem, {})
    head = next((h for h in root.iter('head') if h.get('bpm') or h.find('bpm') is not None), None)
    bpm, _ = model_value(head, 'bpm', 120) if head is not None else (120, None)
    tps = LMMS_TICKS_PER_BEAT * bpm / 60      # LMMS ticks per second

    # Automation: object id -> [(tick, value)]
    automation = {}
    for ap in song.iter('automationpattern'):
        pos = int(ap.get('pos', 0))
        for obj in ap.findall('object'):
            automation.setdefault(obj.get('id'), []).extend(
                (pos + int(t.get('pos')), float(t.get('value'))) for t in ap.findall('time'))

    seq = demos.Seq()
    song_level = overrides.get('_level', SONG_LEVEL)
    patch_time = [0.0]

    def send_patch(ch, p):
        seq.at(patch_time[0], demos.patch(ch, **p))
        patch_time[0] += PATCH_SPACING

    def sec(t): return LEAD_IN + t / tps
    # Drums on channels 10-14, tonal tracks on the rest
    drum_order = ['kick', 'snare', 'hats', 'cymbal', 'toms']
    free = [c for c in range(16) if not 9 <= c < 9 + len(drum_order)]
    drum_channels = {}
    report = []

    # All instrument tracks: song tracks, then the Beat/Bassline tracks expanded where placed
    tracks = []
    song_tracks = song.find('trackcontainer').findall('track')
    bb_tracks = [t for t in song_tracks if t.get('type') == '1']
    bb_container = next((t.find('bbtrack/trackcontainer') for t in bb_tracks
                         if t.find('bbtrack/trackcontainer') is not None), None)
    for track in song_tracks:
        if track.get('type') == '0':
            tracks.append((track, None))
    if bb_container is not None:
        inner = [t for t in bb_container.findall('track') if t.get('type') == '0']
        placements = []
        for index, bb in enumerate(bb_tracks):
            if bb.get('muted') == '1':
                continue
            # A Beat/Bassline loops at the length of its longest pattern (16 steps = 192 ticks)
            steps = [int(p.get('steps', 16)) for t in inner for p in t.findall('pattern')
                     if int(p.get('pos')) == index * 192]
            bb_len = max(steps, default=16) * LMMS_STEP_TICKS
            placements += [(index, int(c.get('pos')), int(c.get('len')), bb_len) for c in bb.findall('bbtco')
                           if c.get('muted') != '1']
        tracks += [(t, placements) for t in inner]
    # Muted tracks are left out, unless everything is muted (a project set up to play elsewhere)
    if any(t.get('muted') != '1' and track_notes(t, pl) for t, pl in tracks):
        tracks = [(t, pl) for t, pl in tracks if t.get('muted') != '1']

    channel_of = {}
    for track, placements in tracks:
        it = track.find('instrumenttrack')
        raw = track_notes(track, placements)
        if not raw:
            continue
        name = track.get('name')
        vol, vol_id = model_value(it, 'vol', 100)
        pan, _ = model_value(it, 'pan', 0)
        instrument = it.find('instrument')
        plugin = instrument.get('name') if instrument is not None else ''
        sf2 = it.find('.//sf2player')
        bank = int(sf2.get('bank', 0)) if sf2 is not None else 0
        program = int(sf2.get('patch', 0)) if sf2 is not None else 0
        afp = it.find('.//audiofileprocessor')
        sample = afp.get('src', '') if afp is not None else ''
        shift = track_transpose(it)
        spec = overrides.get(name)
        if isinstance(spec, tuple) and 'transpose' in spec[1]:
            spec = (spec[0], dict(spec[1]))
            shift += spec[1].pop('transpose')   # Samples: the sample's own pitch is unknown

        def vel(v, scale=1.0): return max(1, min(127, round(v * 64 / 100 * scale)))

        kind = drum_sample(sample) if plugin == 'audiofileprocessor' else None
        if bank == 128 or spec == 'drums' or (kind and spec is None):
            for t, length, key, v in raw:
                k = kind or DRUM_KIND.get(key + shift, 'hats')
                if k not in drum_channels:
                    ch = drum_channels[k] = 9 + drum_order.index(k)
                    p, _ = DRUMS[k]
                    # A kit track sets the level in the patch, drum sample tracks (several
                    # share a channel) put their volume into the velocity
                    send_patch(ch, {**p, 'volume': song_level * DRUM_LEVEL[k] * (1 if kind else vol / 100)})
                if kind:
                    note = DRUM_SAMPLE_NOTE.get(k, key + shift - 24)
                else:
                    note = DRUMS[k][1] or key + shift
                seq.note(sec(t), drum_channels[k], note, length / tps, vel(v, vol / 100 if kind else 1))
            report.append(f'{name}: drums ({kind or "kit"})')
            continue

        if spec is None:
            if plugin == 'audiofileprocessor':
                spec = next((pt for key, pt in SAMPLES if key in sample.lower()), None)
                if spec is None:
                    report.append(f'{name}: sample {sample}, not converted')
                    continue
            elif sf2 is not None:
                spec = gm_patch(program)
            else:
                spec = synth_patch(name, plugin, [(t, ln, k + shift, v) for t, ln, k, v in raw])
        if spec == 'skip':
            report.append(f'{name}: skipped')
            continue
        pname, extra = spec if isinstance(spec, tuple) else (spec, {})
        p = {**PATCHES[pname], **extra}
        level = p.pop('volume', 0.8)
        if free:
            ch = free.pop(0)
            channel_of.setdefault(pname, ch)
            send_patch(ch, {**p, 'volume': song_level * level * vol / 100, 'pan': p.get('pan', pan / 100)})
            shared = ''
        elif pname in channel_of:
            ch = channel_of[pname]
            shared = ' (shared)'
        else:
            print(f'{name}: out of MIDI channels, skipped', file=sys.stderr)
            continue
        for t, length, key, v in raw:
            seq.note(sec(t), ch, key + shift, length / tps, vel(v))
        # Volume automation -> CC 7
        for t, v in automation.get(vol_id, []) if vol_id and not shared else []:
            seq.at(sec(t), [(0xB0 | ch, 7, demos.lin(song_level * level * v / 100 * demos.LEVEL))])
        keys = sorted(k + shift for _, _, k, _ in raw)
        report.append(f'{name} [{plugin}]: channel {ch + 1}{shared}, {pname} patch, {len(raw)} notes, '
                      f'median note {keys[len(keys) // 2]}')

    end = max(t for t, _ in seq.ev)
    return seq, end, report, bpm


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    stem = os.path.splitext(os.path.basename(src))[0].lower()
    stem = SONGS.get(stem, {}).get('_name', stem)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), '..', 'midi', stem + '.mid')
    seq, length, report, bpm = convert(src)
    # Write the song's own tempo so bars line up in a DAW
    make_midis.TEMPO_US = round(60e6 / bpm)
    make_midis.TICKS_PER_S = make_midis.PPQ * 1e6 / make_midis.TEMPO_US
    with open(out, 'wb') as f:
        f.write(make_midis.smf(seq, stem))
    print('\n'.join(report))
    print(f'{os.path.relpath(out)}: {len(seq.ev)} events, {length:.1f} s')


if __name__ == '__main__':
    main()
