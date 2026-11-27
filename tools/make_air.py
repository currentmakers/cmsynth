#!/usr/bin/env python3
"""Bach's Air (BWV 1068) arranged for cmsynth, a grand orchestral version.

Usage: tools/make_air.py            (writes midi/bach-air.mid)

The notes are the four parts of the Bach-Gesellschaft edition as typeset by the
Mutopia Project (tools/bach-air-notes.ly, Creative Commons Attribution-ShareAlike
3.0, typeset by Jeff Covey), read with a small parser for the bit of LilyPond
that file uses.  The arrangement plays both repeats and builds up each time:

  1. A section:        strings only (violins, viola, cello)
  2. A section again:  double bass, harpsichord continuo, high violins an
                       octave up, timpani at the cadence
  3. B section:        organ, choir, celesta on the long melody notes
  4. B section again:  tutti with horns, string ensemble, organ pedal and
                       timpani, broader tempo and a final fermata roll

The patches go out first, one channel at a time, so the file sets up its own
sound.  14 channels, up to about 30 voices at once: made for the RP2354.
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demos                # noqa: E402
import make_midis           # noqa: E402  (sets demos.LEVEL for files)
import lmms2mid             # noqa: E402  (the violin patch)

HERE = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(HERE, 'bach-air-notes.ly')

# ---------------------------------------------------------------------------
# LilyPond subset: \relative blocks, notes with is/es, octave marks, durations
# with dots, ties, rests, bar checks, \acciaccatura {..}, ^\trill, \fermata.

STEP = dict(c=0, d=1, e=2, f=3, g=4, a=5, b=6)
SEMI = [0, 2, 4, 5, 7, 9, 11]
TOKEN = re.compile(r"\\acciaccatura|\\fermata|\^\\trill|[{}~|]"
                   r"|r(\d*)(\.*)"
                   r"|([a-g])((?:is|es)*)!?([',]*)!?(\d*)(\.*)!?")


class Note:
    def __init__(self, start, dur, pitch):
        self.start, self.dur, self.pitch = start, dur, pitch
        self.tie = self.trill = self.fermata = False

    @property
    def end(self): return self.start + self.dur


def parse_part(body, ref):
    """Notes of one \\relative block, times in quarter notes."""
    body = re.sub(r'%.*', '', body)
    prev = 21 + STEP[ref[0]] + 7 * (ref.count("'") - ref.count(','))   # c = C3
    pos, dur = 0.0, 1.0
    notes, graces = [], []
    grace_mode = False
    bar = 1
    for m in TOKEN.finditer(body):
        tok = m.group(0)
        if tok == '\\acciaccatura':
            grace_mode = True
        elif tok == '{':
            pass
        elif tok == '}':
            grace_mode = False
        elif tok == '~':
            notes[-1].tie = True
        elif tok == '|':
            if abs(pos - 4 * bar) > 1e-9:
                sys.exit(f'bar {bar}: {pos / 4:.3f} bars of notes')
            bar += 1
        elif tok == '^\\trill':
            notes[-1].trill = True
        elif tok == '\\fermata':
            notes[-1].fermata = True
        elif tok.startswith('r'):
            if m.group(1):
                dur = 4 / int(m.group(1)) * (1.5 if m.group(2) else 1)
            pos += dur
        else:
            letter, acc, marks, length, dots = m.group(3, 4, 5, 6, 7)
            # Nearest note with this letter, then the octave marks
            s = next(s for s in range(prev - 3, prev + 4) if s % 7 == STEP[letter])
            s += 7 * (marks.count("'") - marks.count(','))
            prev = s
            pitch = 12 * (s // 7 + 1) + SEMI[s % 7] + acc.count('is') - acc.count('es')
            d = 4 / int(length) * (1.5 if dots else 1) if length else None
            if grace_mode:
                graces.append(pitch)
                continue
            if d is not None:
                dur = d
            if notes and notes[-1].tie and notes[-1].pitch == pitch and abs(notes[-1].end - pos) < 1e-9:
                notes[-1].dur += dur
                notes[-1].tie = False
            else:
                n = Note(pos, dur, pitch)
                # Acciaccatura: a short grace note on the beat, taken from the main note
                for g in graces:
                    gd = min(0.125, dur / 3)
                    notes.append(Note(n.start, gd, g))
                    n.start += gd
                    n.dur -= gd
                graces = []
                notes.append(n)
            pos += dur
    return notes, pos


def read_score():
    text = open(NOTES).read()
    parts = {}
    for name, ref, body in re.findall(r"(\w+)\s*=\s*\\relative\s+([a-g][',]*)\s*\{(.*?)\n\}", text, re.S):
        notes, length = parse_part(body, ref)
        if abs(length - 76) > 1e-9:
            sys.exit(f'{name}: {length / 4} bars, expected 19')
        parts[name] = notes
    return parts


# ---------------------------------------------------------------------------
# Form: ||: bars 1-5 :|| with first ending bar 6 and second ending bar 7, then
# ||: bars 8-19 :||.  Played bars (0 based) and which time through each is.

ORDER = list(range(5)) + [5] + list(range(5)) + [6] + list(range(7, 19)) * 2
PASS_START = [0, 6, 12, 24]


def pass_of_bar(k):
    return sum(k >= s for s in PASS_START) - 1


def unfold(notes):
    """[(beat, note, pass)] for the whole performance."""
    out = []
    for k, bar in enumerate(ORDER):
        for n in notes:
            if bar * 4 - 1e-9 <= n.start < bar * 4 + 4 - 1e-9:
                c = Note(n.start - bar * 4 + k * 4, n.dur, n.pitch)
                c.trill, c.fermata = n.trill, n.fermata
                out.append((c, pass_of_bar(k)))
    return out


# Tempo: a broad 40 beats per minute, the tutti a little broader still, with a
# ritardando at the end of every section and a long one at the very end
BPM = 40.0
RIT = {5: 0.88, 11: 0.78, 23: 0.84, 35: 0.5}
FERMATA_S = 3.5
LEAD_IN = 1.0
TOTAL_BEATS = len(ORDER) * 4


def bpm_at(beat):
    k = int(beat // 4)
    f = 0.95 if k >= PASS_START[3] else 1.0
    if k in RIT:
        x = (beat - 4 * k) / 4
        if x > 0.4:
            f *= 1 - (1 - RIT[k]) * (x - 0.4) / 0.6
    return BPM * f


STEPS_PER_BEAT = 96
_times = [0.0]
for i in range(TOTAL_BEATS * STEPS_PER_BEAT + 4 * STEPS_PER_BEAT):
    b = i / STEPS_PER_BEAT
    _times.append(_times[-1] + 60.0 / bpm_at(b) / STEPS_PER_BEAT)


def sec(beat):
    i = beat * STEPS_PER_BEAT
    lo = int(i)
    return LEAD_IN + _times[lo] + (_times[lo + 1] - _times[lo]) * (i - lo)


# ---------------------------------------------------------------------------
# Patches, in the units demos.patch() takes

SONG_LEVEL = 0.4
# Oscillator 3 as a vibrato LFO: LO range, keyboard off, about 5.5 Hz
VIBRATO = dict(osc3_range='LO', osc3_wave='tri', osc3_kbd=0, osc3_detune=1.0, osc3_on=0, osc_mod=1, mod_mix=0.0)

CH = dict(vln1=0, vln1_8va=1, vln2=2, viola=3, cello=4, bass=5, harpsichord=6, organ=7, horns=8, choir=9,
          timpani=10, pedal=11, ensemble=12, celesta=13)

PATCHES = {
    # Violins tuned against a recording of a real violin (see lmms2mid.py's
    # 'violin'): saw and narrow pulse for the body's uneven harmonics, a fixed
    # resonant peak for the bridge hill, vibrato that also moves the filter.
    'vln1': dict(lmms2mid.PATCHES['violin'], volume=0.8, pan=-0.2, mod=0),
    'vln1_8va': dict(osc1_range="8'", osc1_wave='tri', osc2_range="8'", osc2_wave='narrow', osc2_detune=0.05,
                     osc1_level=0.8, osc2_level=0.3, cutoff=2600, emphasis=0.1, contour=0.2, kbd=2,
                     f_attack=0.1, f_decay=0.6, f_sustain=0.7, l_attack=0.1, l_decay=0.4, l_sustain=0.85,
                     decay_sw=1, volume=0.4, pan=0.3, **dict(VIBRATO, osc3_detune=1.15)),
    'vln2': dict(lmms2mid.PATCHES['violin'], cutoff=2200, osc3_detune=0.92, volume=0.55, pan=-0.6, mod=17),
    # Viola: a bigger body, so a lower peak and a fuller pulse
    'viola': dict(lmms2mid.PATCHES['violin'], osc2_wave='wide', cutoff=1800, l_attack=0.1, osc3_detune=1.08,
                  volume=0.55, pan=0.45, mod=15),
    'cello': dict(lmms2mid.PATCHES['cello'], volume=0.7, pan=0.3),
    'bass': dict(osc1_range="16'", osc1_wave='saw', osc2_range="16'", osc2_wave='tri', osc2_level=0.5,
                 osc1_level=0.75, cutoff=330, emphasis=0.1, contour=0.35, kbd=1, f_attack=0.03, f_decay=0.4,
                 f_sustain=0.4, l_attack=0.03, l_decay=0.3, l_sustain=0.85, decay_sw=1, volume=0.7, pan=0.1),
    'harpsichord': dict(osc1_range="8'", osc1_wave='narrow', osc2_range="4'", osc2_wave='saw', osc2_level=0.35,
                        osc1_level=0.8, cutoff=900, emphasis=0.35, contour=0.75, kbd=3, f_attack=0.001,
                        f_decay=0.25, f_sustain=0.0, l_attack=0.001, l_decay=0.9, l_sustain=0.0, decay_sw=1,
                        volume=0.45, pan=0.6),
    'organ': dict(osc1_range="8'", osc1_wave='square', osc2_range="4'", osc2_wave='tri', osc2_level=0.4,
                  osc1_level=0.5, osc3_range="16'", osc3_wave='tri', osc3_level=0.45, osc3_on=1,
                  cutoff=2200, emphasis=0.0, contour=0.0, kbd=2, l_attack=0.06, l_decay=0.25, l_sustain=1.0,
                  decay_sw=1, volume=0.4, pan=0.0),
    'horns': dict(osc1_range="8'", osc1_wave='saw', osc2_range="8'", osc2_wave='saw', osc2_detune=0.08,
                  osc1_level=0.7, osc2_level=0.6, cutoff=420, emphasis=0.2, contour=0.55, kbd=2,
                  f_attack=0.15, f_decay=0.6, f_sustain=0.55, l_attack=0.06, l_decay=0.35, l_sustain=0.9,
                  decay_sw=1, volume=0.55, pan=-0.1),
    'choir': dict(osc1_range="8'", osc1_wave='trisaw', osc2_range="8'", osc2_wave='saw', osc2_detune=0.14,
                  osc1_level=0.6, osc2_level=0.45, osc3_range="4'", osc3_wave='tri', osc3_detune=-0.08,
                  osc3_level=0.2, osc3_on=1, cutoff=1300, emphasis=0.3, contour=0.15, kbd=2,
                  f_attack=0.5, f_decay=1.0, f_sustain=0.8, l_attack=0.45, l_decay=1.0, l_sustain=0.9,
                  decay_sw=1, volume=0.5, pan=0.0),
    # Timpani: the self-oscillating filter tuned to the note, struck by a short contour
    'timpani': dict(osc1_range="8'", osc1_wave='tri', osc1_level=0.7, osc2_on=0, noise_on=1, noise_level=0.15,
                    cutoff=90, emphasis=0.85, contour=0.55, kbd=3, f_attack=0.001, f_decay=0.12, f_sustain=0.0,
                    l_attack=0.001, l_decay=0.9, l_sustain=0.0, decay_sw=1, drive=0.3, volume=0.8, pan=0.0),
    'pedal': dict(osc1_range="16'", osc1_wave='tri', osc2_range="32'", osc2_wave='square', osc2_level=0.3,
                  osc1_level=0.8, cutoff=400, emphasis=0.0, contour=0.0, kbd=1, l_attack=0.08, l_decay=0.3,
                  l_sustain=1.0, decay_sw=1, volume=0.5, pan=0.0),
    'ensemble': dict(osc1_range="8'", osc1_wave='saw', osc2_range="8'", osc2_wave='saw', osc2_detune=-0.15,
                     osc1_level=0.6, osc2_level=0.6, cutoff=1600, emphasis=0.1, contour=0.2, kbd=2,
                     f_attack=0.3, f_decay=1.0, f_sustain=0.8, l_attack=0.25, l_decay=0.6, l_sustain=0.9,
                     decay_sw=1, volume=0.42, pan=0.55),
    'celesta': dict(osc1_range="4'", osc1_wave='tri', osc2_range="2'", osc2_wave='narrow', osc2_level=0.2,
                    osc1_level=0.8, cutoff=3000, emphasis=0.1, contour=0.3, kbd=3, f_attack=0.001,
                    f_decay=0.6, f_sustain=0.0, l_attack=0.001, l_decay=1.3, l_sustain=0.0, decay_sw=1,
                    volume=0.4, pan=0.65),
}

# Velocity per time through (None = not playing)
VEL = {
    'vln1': (82, 92, 100, 112), 'vln1_8va': (None, 62, None, 82), 'vln2': (70, 80, 88, 100),
    'viola': (70, 80, 88, 100), 'cello': (78, 88, 96, 108), 'bass': (None, 80, 90, 105),
    'harpsichord': (None, 72, 64, None), 'organ': (None, None, 52, 78), 'horns': (None, None, None, 88),
    'choir': (None, None, 62, 78), 'pedal': (None, None, None, 92), 'ensemble': (None, None, None, 72),
    'celesta': (None, None, 72, None),
}
# Brighter each time through: cutoff multiplier
BRIGHT = (1.0, 1.15, 1.3, 1.5)
VIBRATO_DEPTH = 21          # CC 1, about +/- 20 cents, as measured on a real violin
D_MAJOR = [1, 2, 4, 6, 7, 9, 11]   # pitch classes


def upper_neighbour(p):
    return next(q for q in range(p + 1, p + 3) if q % 12 in D_MAJOR)


def build():
    parts = read_score()
    played = {name: unfold(notes) for name, notes in parts.items()}
    seq = demos.Seq()
    pending = []      # (start s, channel, pitch, length s, velocity)

    def add(t0, ch, pitch, dur, vel):
        pending.append([t0, ch, pitch, dur, vel])
    t = 0.0
    for name, ch in CH.items():
        p = dict(PATCHES[name])
        p['volume'] *= SONG_LEVEL
        mod = p.pop('mod', 0)          # Mod wheel: the inner strings' constant vibrato
        p.pop('bowed', None)
        seq.at(t, demos.patch(ch, **p) + [(0xB0 | ch, 1, mod)])
        t += 0.05
    end_beat = TOTAL_BEATS

    def note(ch, b0, b1, pitch, vel, final=False):
        t0, t1 = sec(b0), sec(b1)
        if final:
            t1 += FERMATA_S
        add(t0, ch, pitch, max(0.03, t1 - t0), max(1, min(127, round(vel))))

    def phrase(b):
        """Gentle swell over every two bars."""
        return 0.92 + 0.08 * math.sin(math.pi * ((b % 8) / 8))

    # Cutoff a little brighter each time through
    for i, b in enumerate(PASS_START):
        for name, ch in CH.items():
            if name in ('timpani', 'organ', 'pedal'):
                continue
            seq.at(sec(b) - 0.02, demos.cutoff_ev(ch, PATCHES[name]['cutoff'] * BRIGHT[i]))

    def is_final(n):
        return abs(n.end - end_beat) < 1e-6

    # Melody: first violins, with vibrato coming in on long notes and real trills
    def melody(name, transpose=0, min_len=0.0):
        ch = CH[name]
        for n, ps in played['violinone']:
            v = VEL[name][ps]
            if v is None or n.dur < min_len:
                continue
            fin = is_final(n)
            vel = v * phrase(n.start)
            if n.trill:
                # Start on the upper note, alternate, end on the main note
                t0, t1 = n.start, n.end
                k = max(2, int((sec(t1) - sec(t0)) / 0.075))
                for i in range(k):
                    pitch = n.pitch if i == k - 1 or i % 2 else upper_neighbour(n.pitch)
                    b0 = t0 + (t1 - t0) * i / k
                    b1 = t0 + (t1 - t0) * (i + 1) / k
                    note(ch, b0, b1, pitch + transpose, vel)
                continue
            note(ch, n.start, n.end, n.pitch + transpose, vel, fin)
            if PATCHES[name].get('osc_mod'):
                t0, t1 = sec(n.start), sec(n.end) + (FERMATA_S if fin else 0)
                seq.at(t0, [(0xB0 | ch, 1, 0)])
                if t1 - t0 > 0.6:
                    for i in range(12):
                        seq.at(t0 + 0.25 + i * 0.035, [(0xB0 | ch, 1, round(VIBRATO_DEPTH * (i + 1) / 12))])

    melody('vln1')
    melody('vln1_8va', transpose=12)
    melody('horns', transpose=-12, min_len=0.5)

    # Inner parts and strings that double them
    for part, names in (('violintwo', ('vln2', 'organ', 'ensemble')), ('viola', ('viola', 'organ'))):
        for n, ps in played[part]:
            for name in names:
                v = VEL[name][ps]
                if v is not None:
                    note(CH[name], n.start, n.end, n.pitch, v * phrase(n.start), is_final(n))

    # The ensemble also doubles the first violins, the choir sings the long melody notes
    for n, ps in played['violinone']:
        if VEL['ensemble'][ps] is not None and n.dur >= 0.5:
            note(CH['ensemble'], n.start, n.end, n.pitch, VEL['ensemble'][ps], is_final(n))
        if VEL['choir'][ps] is not None and n.dur >= 1.0:
            note(CH['choir'], n.start, n.end, n.pitch, VEL['choir'][ps], is_final(n))
        if VEL['celesta'][ps] is not None and n.dur >= 1.0:
            note(CH['celesta'], n.start, n.start + 1, n.pitch, VEL['celesta'][ps])

    # Continuo: cello and double bass slightly detached, harpsichord, organ pedal in quarters
    for n, ps in played['continuo']:
        fin = is_final(n)
        for name, length in (('cello', 0.8), ('bass', 0.75)):
            v = VEL[name][ps]
            if v is not None:
                note(CH[name], n.start, n.start + (n.dur if fin else n.dur * length), n.pitch, v * phrase(n.start), fin)
        v = VEL['harpsichord'][ps]
        if v is not None:
            note(CH['harpsichord'], n.start, n.start + n.dur * 0.5, n.pitch, v)
    for beat in range(TOTAL_BEATS):
        ps = pass_of_bar(beat // 4)
        if VEL['pedal'][ps] is None:
            continue
        here = [n for n, _ in played['continuo'] if beat - 1e-9 <= n.start < beat + 1 - 1e-9]
        if here:
            low = min(n.pitch for n in here) - 12
            while low < 28:
                low += 12
            fin = any(is_final(n) for n in here)
            note(CH['pedal'], beat, max(n.end for n in here) if fin else beat + 1, low, VEL['pedal'][ps], fin)

    # Harpsichord right hand: on every beat, the chord of the inner parts, lightly spread
    for beat in range(TOTAL_BEATS):
        v = VEL['harpsichord'][pass_of_bar(beat // 4)]
        if v is None:
            continue
        chord = sorted({n.pitch for part in ('violintwo', 'viola') for n, _ in played[part]
                        if n.start - 1e-9 <= beat < n.end - 1e-9})
        for i, pitch in enumerate(chord):
            t0 = sec(beat) + 0.015 * (i + 1)
            add(t0, CH['harpsichord'], pitch, sec(beat + 0.6) - t0, round(v * 0.8))

    # Timpani: D and A at the big moments, a roll under the final fermata
    tch = CH['timpani']
    D2, A1 = 38, 33
    hits = [(6 * 4, D2, 70), (11 * 4 + 2, A1, 78),                    # A section again, its cadence
            (24 * 4, A1, 96), (24 * 4 + 2, A1, 70), (29 * 4 + 2, A1, 80),   # tutti
            (35 * 4, A1, 92), (35 * 4 + 1.5, A1, 84)]
    for b, pitch, vel in hits:
        add(sec(b), tch, pitch, 0.5, vel)
    # Roll into the tutti
    t0, t1 = sec(23 * 4 + 3), sec(24 * 4)
    k = int((t1 - t0) / 0.07)
    for i in range(k):
        add(t0 + i * (t1 - t0) / k, tch, A1, 0.06, round(40 + 50 * i / k))
    # Final roll on D, swelling and dying away under the fermata
    t0 = sec(35 * 4 + 2)
    t1 = sec(end_beat) + FERMATA_S
    k = int((t1 - t0) / 0.065)
    for i in range(k):
        x = i / k
        add(t0 + x * (t1 - t0), tch, D2, 0.06, round(60 + 50 * math.sin(math.pi * min(1, x * 1.4)) * (1 - x * 0.5)))

    # Two parts on one channel playing the same note: end the first just before the
    # second starts, so a note off never cuts a note that is still meant to sound
    pending.sort()
    last = {}
    for n in pending:
        key = (n[1], n[2])
        if key in last and last[key][0] + last[key][3] > n[0] - 0.005:
            if abs(last[key][0] - n[0]) < 0.005:      # Same start: keep the longer one
                last[key][3] = max(last[key][3], n[3])
                n[3] = 0
                continue
            last[key][3] = max(0.02, n[0] - last[key][0] - 0.005)
        last[key] = n
    # Bowing on the cello: volume, brightness and vibrato move within every note
    cello = [(t0, dur) for t0, ch, pitch, dur, vel in pending if ch == CH['cello'] and dur > 0]
    for i, b in enumerate(PASS_START):
        t_start = sec(b)
        t_end = sec(PASS_START[i + 1]) if i + 1 < len(PASS_START) else 1e9
        lmms2mid.bow(seq, CH['cello'], [n for n in cello if t_start - 0.01 <= n[0] < t_end - 0.01],
                     PATCHES['cello']['volume'] * SONG_LEVEL, PATCHES['cello']['cutoff'] * BRIGHT[i])
    for t0, ch, pitch, dur, vel in pending:
        if dur > 0:
            seq.note(t0, ch, pitch, dur, vel)

    # Everything off and vibrato back to zero at the end
    stop = sec(end_beat) + FERMATA_S + 2.5
    for ch in CH.values():
        seq.at(stop, [(0xB0 | ch, 1, 0), (0xB0 | ch, 123, 0)])
    return seq, stop


def peak_notes(seq):
    """Most notes held at once (without release tails)."""
    ev = sorted(((t, 1 if m[0] & 0xF0 == 0x90 else -1) for t, m in seq.ev if m[0] & 0xE0 == 0x80),
                key=lambda e: (e[0], e[1]))
    n = peak = 0
    for _, d in ev:
        n += d
        peak = max(peak, n)
    return peak


def main():
    seq, length = build()
    make_midis.TEMPO_US = round(60e6 / BPM)
    make_midis.TICKS_PER_S = make_midis.PPQ * 1e6 / make_midis.TEMPO_US
    out = os.path.join(HERE, '..', 'midi', 'bach-air.mid')
    with open(out, 'wb') as f:
        f.write(make_midis.smf(seq, 'bach-air'))
    notes = sum(1 for _, m in seq.ev if m[0] & 0xF0 == 0x90)
    print(f'{os.path.relpath(out)}: {notes} notes on {len(CH)} channels, {length:.1f} s, '
          f'up to {peak_notes(seq)} notes held at once')


if __name__ == '__main__':
    main()
