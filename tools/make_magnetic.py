#!/usr/bin/env python3
"""Jean-Michel Jarre's Magnetic Fields, pt. 2, rearranged for cmsynth.

Usage: tools/make_magnetic.py        (writes midi/magnetic-fields-2.mid)

The notes come from a General MIDI file (tools/magnetic-fields-2-source.mid,
"(C)1994 Heavenly Music", 51 s).  It is rearranged into a longer piece from its
own sections, at the original record's tempo (a bar of 1.25 s).  The patches
were matched against a rendering of the source file in LMMS (General MIDI
sounds), section by section: spectrum and the level each part adds (within
about 1 dB).  --plain OUT writes the source as it is, for that comparison:

  lead      bright square and saw with glide; the file's pitch bends and mod
            wheel pass through (the mod wheel scaled down for a gentle vibrato)
  strings   a string machine: three detuned saws, slow attack, long release
  arpeggio  the resonant sequencer pluck, its filter opening and closing
            over the sections
  bass      saw and square with a punchy filter
  pulse     piano-like (a General MIDI piano in the source), panned back and
            forth by the file's own pan automation
  drums     kick, snare, hi-hats (with choke), crash and splash from drumkit.py

The composition is Jean-Michel Jarre's and still under copyright: this is in
the repository for playing on the synth, and is not to be used in videos.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demos                # noqa: E402
import drumkit              # noqa: E402
import make_midis           # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'magnetic-fields-2-source.mid')
BPM = 192.0                 # the original record: a bar of four beats in 1.25 s
SOURCE_BPM = 182.0          # the source MIDI file's own tempo
BEAT = 60.0 / BPM
BAR = 4 * BEAT
SONG_LEVEL = 0.5


# ---------------------------------------------------------------------------
# Standard MIDI File reader (format 0 or 1), no third party modules

def varlen(d, i):
    v = 0
    while True:
        b = d[i]
        i += 1
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, i


def read_smf(path):
    """Notes [(beat, length, channel, key, velocity)] and controller events
    [(beat, channel, status, data1, data2)], channels 1-16."""
    d = open(path, 'rb').read()
    _, ntracks, div = struct.unpack('>HHH', d[8:14])
    i = 8 + struct.unpack('>I', d[4:8])[0]
    notes, ctrl, held = [], [], {}
    for _ in range(ntracks):
        length = struct.unpack('>I', d[i + 4:i + 8])[0]
        j, end, t, run = i + 8, i + 8 + length, 0, 0
        i = end
        while j < end:
            dt, j = varlen(d, j)
            t += dt
            b = d[j]
            if b == 0xFF:
                n, k = varlen(d, j + 2)
                j = k + n
                continue
            if b in (0xF0, 0xF7):
                n, k = varlen(d, j + 1)
                j = k + n
                continue
            if b & 0x80:
                run = b
                j += 1
            kind, ch = run & 0xF0, (run & 0x0F) + 1
            size = 1 if kind in (0xC0, 0xD0) else 2
            data = d[j:j + size]
            j += size
            beat = t / div
            if kind == 0x90 and data[1] > 0:
                held[(ch, data[0])] = (beat, data[1])
            elif kind in (0x80, 0x90):
                if (ch, data[0]) in held:
                    b0, vel = held.pop((ch, data[0]))
                    notes.append((b0, beat - b0, ch, data[0], vel))
            elif kind in (0xB0, 0xE0):
                ctrl.append((beat, ch, kind, data[0], data[1]))
    return sorted(notes), sorted(ctrl)


# ---------------------------------------------------------------------------
# Channels and patches (cmsynth channels 0-15)

LFO = dict(osc3_range='LO', osc3_wave='tri', osc3_kbd=0, osc3_detune=1.0, osc3_on=0, osc_mod=1, mod_mix=0.0)
PARTS = {
    # source channel: (name, cmsynth channel, patch)
    2: ('lead', 0, dict(osc1_range="8'", osc1_wave='square', osc1_level=0.6, osc2_range="8'", osc2_wave='saw',
                        osc2_detune=0.08, osc2_level=0.55, cutoff=4000, emphasis=0.3, contour=0.3, kbd=2,
                        f_attack=0.02, f_decay=0.5, f_sustain=0.6, l_attack=0.01, l_decay=0.4, l_sustain=0.9,
                        decay_sw=1, glide=1, glide_time=0.035, volume=0.8, pan=0.0, **LFO)),
    13: ('strings', 1, dict(osc1_range="8'", osc1_wave='saw', osc1_level=0.55, osc2_range="8'", osc2_wave='saw',
                            osc2_detune=0.14, osc2_level=0.5, osc3_range="8'", osc3_wave='saw', osc3_detune=-0.12,
                            osc3_level=0.45, osc3_on=1, cutoff=4500, emphasis=0.15, contour=0.1, kbd=2,
                            f_attack=0.3, f_decay=1.0, f_sustain=0.9, l_attack=0.15, l_decay=0.6, l_sustain=0.9,
                            decay_sw=1, volume=0.65, pan=0.0)),
    11: ('arpeggio', 2, dict(osc1_range="8'", osc1_wave='saw', osc1_level=0.7, osc2_range="8'", osc2_wave='square',
                             osc2_detune=0.05, osc2_level=0.5, cutoff=1200, emphasis=0.5, contour=0.5, kbd=2,
                             f_attack=0.001, f_decay=0.13, f_sustain=0.2, l_attack=0.002, l_decay=0.22,
                             l_sustain=0.4, decay_sw=1, volume=1.0, pan=0.0)),
    3: ('bass', 3, dict(osc1_range="8'", osc1_wave='saw', osc1_level=0.8, osc2_range="8'", osc2_wave='square',
                        osc2_detune=0.04, osc2_level=0.6, cutoff=1000, emphasis=0.3, contour=0.5, kbd=1,
                        f_attack=0.001, f_decay=0.15, f_sustain=0.2, l_attack=0.003, l_decay=0.3, l_sustain=0.6,
                        decay_sw=1, drive=0.3, volume=0.38, pan=0.0)),
    # The pulse: a General MIDI piano in the source, so piano-like: saw and
    # triangle at the note's own pitch, a filter that closes as it decays
    1: ('pulse', 4, dict(osc1_range="8'", osc1_wave='saw', osc1_level=0.7, osc2_range="8'", osc2_wave='tri',
                         osc2_level=0.5, cutoff=1200, emphasis=0.1, contour=0.4, kbd=2, f_attack=0.001,
                         f_decay=0.3, f_sustain=0.0, l_attack=0.001, l_decay=0.5, l_sustain=0.0, decay_sw=1,
                         volume=0.85, pan=0.0)),
    12: ('interlude', 5, dict(osc1_range="8'", osc1_wave='narrow', osc1_level=0.7, osc2_range="8'", osc2_wave='square',
                              osc2_detune=0.06, osc2_level=0.4, cutoff=1000, emphasis=0.35, contour=0.4, kbd=2,
                              f_attack=0.001, f_decay=0.2, f_sustain=0.3, l_attack=0.002, l_decay=0.35,
                              l_sustain=0.4, decay_sw=1, volume=0.22, pan=0.0)),
    5: ('ending', 6, dict(osc1_range="8'", osc1_wave='square', osc1_level=0.6, osc2_range="8'", osc2_wave='saw',
                          osc2_detune=0.1, osc2_level=0.5, cutoff=2500, emphasis=0.3, contour=0.4, kbd=2,
                          f_attack=0.01, f_decay=0.4, f_sustain=0.5, l_attack=0.005, l_decay=0.6, l_sustain=0.5,
                          decay_sw=1, volume=0.6, pan=0.0)),
}
# General MIDI drums -> kit drums on their own channels
DRUM_MAP = {35: 'kick', 36: 'kick', 38: 'snare', 40: 'snare', 42: 'hat', 44: 'pedal', 46: 'open_hat',
            49: 'crash', 57: 'crash', 52: 'splash', 55: 'splash'}
DRUM_CH = dict(kick=7, snare=8, hat=9, open_hat=10, crash=11, splash=12, pedal=13)
# Drum levels matched to a rendering of the source (hi-hats up front, a soft kick)
DRUM_LEVEL = dict(kick=0.5, snare=1.3, hat=1.9, open_hat=1.7, crash=1.3, splash=1.3, pedal=1.3)
# The original is brighter than the first try: the arpeggio's filter sweeps scaled up
ARP_BRIGHT = 1.8
# Mod wheel from the file -> vibrato depth (the file's values are for a GM synth)
MOD_SCALE = 0.35

# ---------------------------------------------------------------------------
# Arrangement: (first source bar, last source bar + 1, options)
#   arp:   arpeggio cutoff (start, end) in Hz over the section
#   mute:  parts left out

SECTIONS = [
    (0, 11, dict(arp=(500, 700))),                                    # intro: drums, pulse, then bass and arpeggio
    (7, 11, dict(arp=(700, 1300))),                                   # groove: the arpeggio opens up
    (7, 11, dict(arp=(1300, 2000))),
    (11, 27, dict(arp=(1100, 1100))),                                 # theme and interlude
    (27, 38, dict(arp=(700, 1200))),                                  # second part of the theme
    (11, 27, dict(arp=(1600, 1600))),                                 # theme again, arpeggio open
    (27, 39, dict(arp=(1400, 800))),                                  # second part and the ending
]


def build(sections=None, bpm=None):
    sections = sections or SECTIONS
    beat_s = 60.0 / (bpm or BPM)
    bar_s = 4 * beat_s
    notes, ctrl = read_smf(SOURCE)
    seq = demos.Seq()
    t = 0.0
    for src, (name, ch, p) in PARTS.items():
        p = dict(p)
        p['volume'] *= SONG_LEVEL
        seq.at(t, demos.patch(ch, **p) + [(0xB0 | ch, 1, 0)])
        t += 0.05
    for drum, ch in DRUM_CH.items():
        p = dict(drumkit.KIT[drum][2])
        p['volume'] *= SONG_LEVEL * DRUM_LEVEL.get(drum, 1.3)
        mod = p.pop('mod', 0)
        seq.at(t, demos.patch(ch, **p) + [(0xB0 | ch, 1, mod)])
        t += 0.05
    start = t + 0.5

    pos = start                 # time of the current section's first bar
    open_hat = None
    for b0, b1, opt in sections:
        mute = opt.get('mute', set())
        lo, hi = b0 * 4, b1 * 4

        def sec(beat):
            return pos + (beat - lo) * beat_s

        for beat, length, ch, key, vel in notes:
            if not lo <= beat < hi:
                continue
            if ch == 10:
                if 'drums' in mute or key not in DRUM_MAP:
                    continue
                drum = DRUM_MAP[key]
                dch, note = DRUM_CH[drum], drumkit.KIT[drum][1]
                t0 = sec(beat)
                if drum in ('hat', 'pedal') and open_hat:
                    seq.ev.append((max(t0, open_hat + 0.01), (0x80 | DRUM_CH['open_hat'], drumkit.KIT['open_hat'][1], 0)))
                    open_hat = None
                if drum == 'open_hat':
                    if open_hat:
                        seq.ev.append((t0, (0x80 | dch, note, 0)))
                    seq.ev.append((t0, (0x90 | dch, note, vel)))
                    open_hat = t0
                else:
                    seq.note(t0, dch, note, 0.05, vel)
                continue
            if ch not in PARTS or PARTS[ch][0] in mute:
                continue
            name, out, _ = PARTS[ch]
            seq.note(sec(beat), out, key, max(0.03, length * beat_s), vel)

        for beat, ch, kind, a, b in ctrl:
            if not lo <= beat < hi or ch not in PARTS or PARTS[ch][0] in mute:
                continue
            out = PARTS[ch][1]
            if kind == 0xE0:
                seq.at(sec(beat), [(0xE0 | out, a, b)])
            elif a == 10:                       # pan
                seq.at(sec(beat), [(0xB0 | out, 10, b)])
            elif a == 1:                        # mod wheel -> vibrato
                seq.at(sec(beat), [(0xB0 | out, 1, round(b * MOD_SCALE))])

        # Arpeggio filter over the section
        c0, c1 = (c * ARP_BRIGHT for c in opt.get('arp', (600, 600)))
        n = (b1 - b0) * 4
        for k in range(n + 1):
            seq.at(pos + k * beat_s, demos.cutoff_ev(PARTS[11][1], c0 * (c1 / c0) ** (k / n)))
        pos += (b1 - b0) * bar_s

    # Let the ending ring, then everything off
    stop = pos + 3.0
    if open_hat:
        seq.ev.append((pos, (0x80 | DRUM_CH['open_hat'], drumkit.KIT['open_hat'][1], 0)))
    for ch in list(range(7)) + list(DRUM_CH.values()):
        seq.at(stop, [(0xB0 | ch, 123, 0), (0xE0 | ch, 0, 64)])
    return seq, stop


def main():
    # --plain OUT: the source file as it is (its own tempo and order, the arpeggio's
    # filter fixed), for comparing the patches with a rendering of the source
    if len(sys.argv) > 2 and sys.argv[1] == '--plain':
        seq, length = build([(0, 39, dict(arp=(PARTS[11][2]['cutoff'] / ARP_BRIGHT,) * 2))], SOURCE_BPM)
        out = sys.argv[2]
    else:
        seq, length = build()
        out = os.path.join(HERE, '..', 'midi', 'magnetic-fields-2.mid')
    make_midis.TEMPO_US = round(60e6 / BPM)
    make_midis.TICKS_PER_S = make_midis.PPQ * 1e6 / make_midis.TEMPO_US
    with open(out, 'wb') as f:
        f.write(make_midis.smf(seq, 'magnetic-fields-2'))
    notes = sum(1 for _, m in seq.ev if m[0] & 0xF0 == 0x90)
    print(f'{os.path.relpath(out)}: {notes} notes, {length:.1f} s')


if __name__ == '__main__':
    main()
