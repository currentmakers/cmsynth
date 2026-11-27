#!/usr/bin/env python3
"""A drum solo for the cmsynth drum kit (tools/drumkit.py).

Usage: tools/make_drum_solo.py          (writes midi/drum-solo.mid)

Written as a score: every bar is a set of lanes (one drum each) and/or a
sticking line.  The length of a lane or line sets its subdivision: 16 is
sixteenths, 12 eighth triplets, 24 sixteenth triplets, 32 thirty-seconds.

Lane characters:   X accent   x normal   o soft   g ghost   - rest
Line characters:   S snare accent  s snare  g ghost snare  F flam
                   1 2 3 4 toms (high to floor), Q W E R the same accented
                   K kick  k soft kick  U kick + floor tom  X crash + kick
                   Z splash + kick  h hi-hat  o open hi-hat  p pedal hi-hat
                   b ride bell  r rim  . rest

Velocity is the dynamics (ghost notes are quiet, accents hard), with a little
humanisation in timing and velocity so it doesn't sound like a drum machine.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demos                # noqa: E402
import drumkit              # noqa: E402
import make_midis           # noqa: E402

BPM = 120
BAR = 4 * 60 / BPM
VEL = {'X': 120, 'x': 95, 'o': 70, 'g': 32}
LANES = dict(kick='kick', snare='snare', hat='hat', open='open_hat', pedal='pedal', ride='ride', bell='bell',
             crash='crash', splash='splash', rim='rim', t1='tom1', t2='tom2', t3='tom3', t4='floor')
LINE = {'S': [('snare', 120)], 's': [('snare', 92)], 'g': [('snare', 32)], 'F': [('flam', 115)],
        '1': [('tom1', 95)], '2': [('tom2', 95)], '3': [('tom3', 95)], '4': [('floor', 95)],
        'Q': [('tom1', 122)], 'W': [('tom2', 122)], 'E': [('tom3', 122)], 'R': [('floor', 122)],
        'K': [('kick', 118)], 'k': [('kick', 80)], 'U': [('kick', 120), ('floor', 120)],
        'X': [('crash', 120), ('kick', 120)], 'Z': [('splash', 115), ('kick', 110)],
        'h': [('hat', 90)], 'o': [('open_hat', 100)], 'p': [('pedal', 80)], 'b': [('bell', 100)],
        'r': [('rim', 100)]}

# Grooves
ROCK = dict(kick='X-----x-x-------', snare='----X--g-g--X--g', hat='x-x-x-x-x-x-x-x-')
ROCK2 = dict(kick='X-----x-x-x-----', snare='----X--g-g--X-g-', hat='x-x-x-x-x-x-x---', open='--------------x-')
RIDE = dict(kick='X--x--x---x--x--', snare='----X--g-g--X-g-', ride='X-x-X-x-X-x-X-x-', bell='------x-------x-',
            pedal='----o-------o---')
FUNK = dict(kick='X--X--X---X--X--', snare='----X--g-gX-g--g', hat='XgxgXgx-XgxgXgxg', open='-------x--------')
FUNK2 = dict(kick='X--X---X-XX--X--', snare='----X--g-g-gX--g', hat='XgxgXgxgXgx-Xgxg', open='-----------x----')
FLOOR4 = dict(kick='o---o---o---o---')
DOUBLE = dict(kick='oooooooooooooooo')
BIG = dict(kick='X-xX--x-X-xX--x-', snare='----X-------X---', ride='X-x-X-x-X-x-X-x-', crash='X---------------')


def bar(*parts, cresc=None, **lanes):
    """One bar: dicts of lanes and lane keywords, line strings as positional strings."""
    b = {'lanes': {}, 'lines': [], 'cresc': cresc}
    for p in parts:
        if isinstance(p, dict):
            b['lanes'].update(p)
        else:
            b['lines'].append(p)
    b['lanes'].update(lanes)
    return b


SCORE = [
    # Intro: hi-hat alone, then the kick, the backbeat and a first little fill
    bar(hat='X-x-X-x-X-x-X-x-'),
    bar(hat='X-x-X-x-X-x-X-x-', kick='X-------X-------'),
    bar(hat='X-x-X-x-X-x-X-x-', kick='X-----x-X-------', snare='----X-------X---'),
    bar(hat='X-x-X-x-X-x-----', kick='X-----x-X-------', snare='----X-------XxXx'),
    # Groove A: rock with ghost notes
    bar(ROCK, crash='X---------------', hat='--x-x-x-x-x-x-x-'),
    bar(ROCK), bar(ROCK2), bar(ROCK),
    bar(ROCK), bar(ROCK2), bar(ROCK),
    bar(kick='X-----x-X-------', hat='x-x-x-x---------', snare='----X-----------', line='........SsSs1122'),
    # Groove B: on the ride with the bell, hi-hat foot on 2 and 4
    bar(RIDE, crash='X---------------', ride='--x-X-x-X-x-X-x-'),
    bar(RIDE), bar(RIDE),
    bar(dict(RIDE, ride='X-x-X-x---------', snare='----X-----------', kick='X--x--x---------', bell='------x---------',
             pedal='----o-----------'), '........Q.1.W.2.'),
    bar(RIDE, crash='X---------------', ride='--x-X-x-X-x-X-x-'),
    bar(RIDE), bar(RIDE),
    bar(kick='X---------------', ride='X-x-------------', line='......sss111222333444RRR'),
    # Funk: sixteenth hi-hats with open barks
    bar(FUNK, crash='X---------------', hat='--xgXgx-XgxgXgxg'),
    bar(FUNK2), bar(FUNK),
    bar(kick='X--X--X---------', hat='XgxgXgx---------', snare='----X--g--------', line='........KsKs1K2K'),
    bar(FUNK, crash='X---------------', hat='--xgXgx-XgxgXgxg'),
    bar(FUNK2), bar(FUNK),
    bar(kick='X--X------------', hat='XgxgX-----------', snare='----X-----------', line='........S1S2S3S4',
        splash='--------------X-'),
    # Tom feature over four on the floor
    bar(FLOOR4, 'X.11W.22E.33R.44'),
    bar(FLOOR4, '1212323434341212'),
    bar(FLOOR4, 'Q12W23E34R4K'),
    bar('1s2s3s4s1s2s3s4sK4K4K4K4'),
    bar('U.U.4.U.U.4.U.UU'),
    bar('U.U.4.U.U.4.RRRR'),
    bar(FLOOR4, 'F..F..F.F..F..F.'),
    bar('s' * 32, cresc=(0.25, 1.3)),
    # Build: double kick under snare and tom accents, crashes every second bar
    bar(DOUBLE, 'X..S..S.S..S..S.'),
    bar(DOUBLE, 'S..S..S.S1.2.3.4'),
    bar(DOUBLE, 'X..S..Q.S..W..E.'),
    bar(DOUBLE, 'S1S2S3S4S1S2S3S4'),
    bar(DOUBLE, 'X.ss1.ss2.ss3.ss'),
    bar(DOUBLE, 'Q12W23E34R41Q12W23E34R4K'),
    bar(DOUBLE, 'X.S.Q.W.E.R.S.Q.'),
    bar('1234123412341234', cresc=(0.75, 1.15)),
    # Breakdown: the pedal hi-hat alone, then a snare roll that grows into the finale
    bar('Z...p...p...p..r'),
    bar('s' * 32, cresc=(0.2, 1.35)),
    # Finale: the big groove with crashes, a last trip around the kit and the ending
    bar(BIG), bar(BIG),
    bar(BIG, line='..............SS'),
    bar('S1234S1234S1234UUUUSSSSS', cresc=(0.85, 1.1)),
    bar('X...............', splash='X---------------', t4='X---------------', snare='X---------------'),
]


def build():
    seq = demos.Seq()
    t0 = drumkit.setup(seq) + 0.5
    d = drumkit.Drummer(seq)
    rnd = random.Random(1068)

    def hit(t, drum, vel):
        # Humanise: a few ms and a few velocity steps, less on kick and snare
        tight = drum in ('kick', 'snare', 'flam')
        t += rnd.gauss(0, 0.002 if tight else 0.004)
        vel *= 1 + rnd.gauss(0, 0.03 if tight else 0.05)
        if drum == 'flam':
            d.hit(t - 0.02, 'snare', vel * 0.45)
            d.hit(t, 'snare', vel)
        elif drum == 'pedal':
            d.pedal(t, vel)
        else:
            d.hit(t, drum, vel, length=0.05)

    for i, b in enumerate(SCORE):
        start = t0 + i * BAR

        def at(step, steps, vel):
            x = step / steps
            if b['cresc']:
                c0, c1 = b['cresc']
                vel *= c0 + (c1 - c0) * x
            return start + x * BAR, vel

        for lane, pattern in b['lanes'].items():
            if lane == 'line':
                continue
            for step, c in enumerate(pattern):
                if c in VEL:
                    t, vel = at(step, len(pattern), VEL[c])
                    hit(t, LANES[lane], vel)
        lines = b['lines'] + ([b['lanes']['line']] if 'line' in b['lanes'] else [])
        for line in lines:
            for step, c in enumerate(line):
                for drum, v in LINE.get(c, []):
                    t, vel = at(step, len(line), v)
                    hit(t, drum, vel)
    end = t0 + len(SCORE) * BAR
    d.choke(end + 3.0)
    return seq, end + 3.5


def main():
    seq, length = build()
    make_midis.TEMPO_US = round(60e6 / BPM)
    make_midis.TICKS_PER_S = make_midis.PPQ * 1e6 / make_midis.TEMPO_US
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'midi', 'drum-solo.mid')
    with open(out, 'wb') as f:
        f.write(make_midis.smf(seq, 'drum-solo'))
    hits = sum(1 for _, m in seq.ev if m[0] & 0xF0 == 0x90)
    print(f'{os.path.relpath(out)}: {len(SCORE)} bars, {hits} hits, {length:.1f} s')


if __name__ == '__main__':
    main()
