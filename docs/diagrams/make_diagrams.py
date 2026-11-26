#!/usr/bin/env python3
"""Generate the cmsynth block diagrams as SVG (and PNG with Inkscape if present).

Copyright (c) 2026 CurrentMakers
Released under the MIT License, see the LICENSE file in the root of the cmsynth repository.
"""

import math
import os
import shutil
import subprocess

OUT = os.path.dirname(os.path.abspath(__file__))
FONT = "DejaVu Sans, Arial, Helvetica, sans-serif"
MONO = "DejaVu Sans Mono, Consolas, monospace"

STYLE = {
    'audio': ('#e3effb', '#2b6cb0'),
    'ctrl': ('#fdf0dc', '#c27a12'),
    'hw': ('#e3f4e6', '#2f855a'),
    'ext': ('#eeeeee', '#555555'),
    'note': ('#ffffff', '#888888'),
}
INK = '#1a202c'
SUB = '#4a5568'
ARROW = {'audio': '#2b6cb0', 'ctrl': '#c27a12', 'hw': '#2f855a', 'ext': '#555555'}


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h = w, h
        self.parts = []
        self.title = title

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=14, weight='normal', anchor='middle', fill=INK, family=FONT, style=''):
        s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        self.add(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}" fill="{fill}" {style}>{s}</text>')

    def box(self, x, y, w, h, title, sub=(), kind='audio', rx=8, size=15, dash=False):
        fill, stroke = STYLE[kind]
        d = ' stroke-dasharray="6 4"' if dash else ''
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2"{d}/>')
        n = 1 + len(sub)
        line = 18
        y0 = y + h / 2 - (n - 1) * line / 2 + 5
        if title:
            self.text(x + w / 2, y0, title, size=size, weight='bold')
        for i, s in enumerate(sub):
            self.text(x + w / 2, y0 + (i + 1) * line, s, size=12.5, fill=SUB)

    def line(self, pts, kind='audio', arrow=True, dash=False, width=2):
        c = ARROW[kind]
        d = ' stroke-dasharray="6 4"' if dash else ''
        m = f' marker-end="url(#a_{kind})"' if arrow else ''
        p = ' '.join(f'{x},{y}' for x, y in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{c}" stroke-width="{width}"{d}{m}/>')

    def circle(self, x, y, r, label, kind='ctrl'):
        fill, stroke = STYLE[kind]
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.text(x, y + 6, label, size=17, weight='bold')

    def legend(self, x, y, items):
        for kind, label in items:
            fill, stroke = STYLE[kind]
            self.add(f'<rect x="{x}" y="{y - 11}" width="22" height="14" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
            self.text(x + 30, y + 1, label, size=12.5, anchor='start', fill=SUB)
            x += 40 + 7.2 * len(label)

    def save(self, name):
        defs = ''.join(
            f'<marker id="a_{k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
            for k, c in ARROW.items())
        svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
               f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">\n'
               f'<title>{self.title}</title>\n<defs>{defs}</defs>\n'
               f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>\n' + '\n'.join(self.parts) + '\n</svg>\n')
        path = os.path.join(OUT, name + '.svg')
        with open(path, 'w') as f:
            f.write(svg)
        if shutil.which('inkscape'):
            subprocess.run(['inkscape', path, '--export-type=png', '--export-dpi=192',
                            f'--export-filename={os.path.join(OUT, name + ".png")}'],
                           check=True, stderr=subprocess.DEVNULL)
        print('wrote', name)


def system():
    s = Svg(1000, 520, 'cmsynth system overview')
    s.text(500, 28, 'cmsynth: from USB MIDI to audio out', size=19, weight='bold')
    W, H = 165, 92
    xs = [20, 235, 450, 665]
    r1, r2, r3 = 60, 210, 360

    s.box(xs[0], r1, W, H, 'Host', ['DAW, aplaymidi,', 'web panel (Web MIDI)'], 'ext')
    s.box(xs[1], r1, W, H, 'TinyUSB', ['USB MIDI device', '"CurrentMakers cmsynth"'], 'hw')
    s.box(xs[2], r1, W, H, 'midi.c', ['note on/off, CC, bend,', 'mod wheel, pedal'], 'ctrl')
    s.box(xs[3], r1, W, H, 'params.c', ['CC → patch field,', 'range, curve, 14-bit'], 'ctrl')
    s.box(850, r1, 130, H, 'patches[16]', ['one per MIDI', 'channel'], 'ctrl')
    s.line([(xs[0] + W, r1 + H / 2), (xs[1], r1 + H / 2)], 'ext')
    s.text((xs[0] + W + xs[1]) / 2, r1 + H / 2 - 8, 'USB', size=12, fill=SUB)
    s.line([(xs[1] + W, r1 + H / 2), (xs[2], r1 + H / 2)], 'hw')
    s.line([(xs[2] + W, r1 + H / 2), (xs[3], r1 + H / 2)], 'ctrl')
    s.text((xs[2] + W + xs[3]) / 2, r1 + H / 2 - 8, 'CC', size=12, fill=SUB)
    s.line([(xs[3] + W, r1 + H / 2), (850, r1 + H / 2)], 'ctrl')

    s.box(xs[2], r2, W, H, 'Voice allocation', ['free voice, else oldest', 'released, else oldest'], 'ctrl', size=14)
    s.line([(xs[2] + W / 2, r1 + H), (xs[2] + W / 2, r2)], 'ctrl')
    s.text(xs[2] + W / 2 + 8, (r1 + H + r2) / 2 + 5, 'note on/off', size=12, anchor='start', fill=SUB)

    # Stacked voices
    for i in (2, 1):
        f, st = STYLE['audio']
        s.add(f'<rect x="{xs[3] + 6 * i}" y="{r2 - 6 * i}" width="{W}" height="{H}" rx="8" fill="{f}" stroke="{st}" stroke-width="2"/>')
    s.box(xs[3], r2, W, H, 'voices[8]', ['pitch, phases, filter,', 'both contours'], 'audio')
    s.line([(xs[2] + W, r2 + H / 2), (xs[3], r2 + H / 2)], 'ctrl')
    s.line([(915, r1 + H), (915, r2 + H / 2), (xs[3] + W + 12, r2 + H / 2)], 'ctrl', dash=True)
    s.text(925, r2 + H / 2 + 26, 'each voice reads', size=12, anchor='middle', fill=SUB)
    s.text(925, r2 + H / 2 + 42, 'its channel\'s patch', size=12, anchor='middle', fill=SUB)

    s.box(xs[3], r3, W, H, 'synth_process()', ['main loop renders', '64 frames (1.33 ms)'], 'audio', size=14)
    s.line([(xs[3] + W / 2, r2 + H), (xs[3] + W / 2, r3)], 'audio')

    # DMA buffer with two halves
    s.box(xs[2], r3, W, H, '', [], 'hw')
    s.text(xs[2] + W / 2, r3 + 22, 'DMA buffer', size=15, weight='bold')
    for i, lab in enumerate(('half A', 'half B')):
        bx = xs[2] + 12 + i * 72
        s.add(f'<rect x="{bx}" y="{r3 + 34}" width="69" height="28" fill="#ffffff" stroke="#2f855a" stroke-width="1.5"/>')
        s.text(bx + 34.5, r3 + 53, lab, size=12.5)
    s.text(xs[2] + W / 2, r3 + 80, 'circular, ping-pong', size=12.5, fill=SUB)
    s.line([(xs[3], r3 + H - 18), (xs[2] + W, r3 + H - 18)], 'audio')
    s.text((xs[2] + W + xs[3]) / 2, r3 + H + 17, 'int16 L/R', size=12, fill=SUB)
    s.line([(xs[2] + W, r3 + 18), (xs[3], r3 + 18)], 'hw', dash=True)
    s.text((xs[2] + W + xs[3]) / 2, r3 - 8, 'half done', size=12, fill=SUB)

    s.box(xs[1], r3, W, H, 'I2S', ['I2S2 + DMA (F407)', 'PIO + 2 DMA (RP2354)'], 'hw')
    s.line([(xs[2], r3 + H / 2), (xs[1] + W, r3 + H / 2)], 'hw')
    s.box(xs[0], r3, W, H, 'PCM5102', ['Audio DAC blade', '16-bit, 48 kHz'], 'hw')
    s.line([(xs[1], r3 + H / 2), (xs[0] + W, r3 + H / 2)], 'hw')
    s.line([(xs[0] + W / 2, r3 + H), (xs[0] + W / 2, r3 + H + 30)], 'hw')
    s.text(xs[0] + W / 2 + 10, r3 + H + 26, 'line out', size=12.5, anchor='start', fill=SUB)

    s.legend(235, 505, [('ctrl', 'MIDI and control'), ('audio', 'synth engine (src/)'), ('hw', 'MCU specific (examples/)'), ('ext', 'external')])
    s.save('cmsynth_system')


def voice():
    s = Svg(1000, 620, 'cmsynth voice signal chain')
    s.text(500, 28, 'One voice: Minimoog style signal chain', size=19, weight='bold')
    X, W, H = 40, 165, 62
    ys = [50, 125, 200, 275]
    srcs = [('NOISE', ['white or pink']),
            ('OSC 1', ["LO, 32' – 2', 6 waves"]),
            ('OSC 2', ['as OSC 1, ±7 semitones']),
            ('OSC 3', ['reverse saw, can be LFO'])]
    mx, mw = 255, 125
    for (t, sub), y in zip(srcs, ys):
        s.box(X, y, W, H, t, sub, 'audio')
        s.line([(X + W, y + H / 2), (mx, y + H / 2)], 'audio')
    s.box(mx, 50, mw, 287, 'MIXER', ['level and on', 'per source', '', '× DRIVE', '1 – 4'], 'audio')

    fx, fy, fw, fh = 430, 138, 175, 110
    s.box(fx, fy, fw, fh, 'LADDER FILTER', ['24 dB/octave', '4 × TPT one-pole', 'emphasis k 0 – 4.15'], 'audio')
    s.line([(mx + mw, fy + fh / 2), (fx, fy + fh / 2)], 'audio')
    vx, vw = 650, 115
    s.box(vx, fy + 15, vw, 80, 'VCA', ['× velocity'], 'audio')
    s.line([(fx + fw, fy + fh / 2), (vx, fy + fh / 2)], 'audio')
    px, pw = 810, 120
    s.box(px, fy + 15, pw, 80, 'PAN', ['and volume'], 'audio')
    s.line([(vx + vw, fy + fh / 2), (px, fy + fh / 2)], 'audio')
    s.line([(px + pw, fy + 38), (985, fy + 38)], 'audio')
    s.line([(px + pw, fy + 72), (985, fy + 72)], 'audio')
    s.text(958, fy + 31, 'L', size=13, weight='bold')
    s.text(958, fy + 65, 'R', size=13, weight='bold')
    s.text(870, fy + 122, 'to the stereo mix', size=12.5, fill=SUB)
    s.text(870, fy + 138, 'of all voices', size=12.5, fill=SUB)

    # Control rate section
    cy, ch = 430, 100
    s.add(f'<rect x="12" y="{cy - 20}" width="976" height="{ch + 55}" rx="10" fill="none" stroke="#c27a12" stroke-width="1.2" stroke-dasharray="4 4"/>')
    s.text(24, cy + ch + 25, 'Control rate: every 16 samples (3 kHz), interpolated per sample', size=13, anchor='start', fill='#c27a12', weight='bold')

    pxx, pww = 40, 165
    s.box(pxx, cy, pww, ch, 'PITCH', ['note, glide, bend', 'detune, range', '(OSC 3 kbd off: free)'], 'ctrl')
    # Pitch to the three oscillators along the left edge
    s.line([(pxx, cy + ch / 2), (22, cy + ch / 2), (22, ys[1] + H / 2)], 'ctrl', arrow=False)
    for y in ys[1:]:
        s.line([(22, y + H / 2), (X, y + H / 2)], 'ctrl')

    mdx, mdw = 245, 175
    s.box(mdx, cy, mdw, ch, 'MODULATION', ['OSC 3 / noise mix', '× mod wheel²', 'to pitch and/or filter'], 'ctrl')
    s.line([(185, ys[3] + H), (185, 375), (300, 375), (300, cy)], 'ctrl', dash=True)
    s.text(192, 368, 'OSC 3', size=12, anchor='start', fill=SUB)
    s.line([(mdx, cy + 70), (pxx + pww, cy + 70)], 'ctrl')
    s.text((mdx + pxx + pww) / 2, cy + 63, 'osc', size=12, fill=SUB)

    sx, sy = fx + fw / 2, 330
    s.circle(sx, sy, 17, 'Σ')
    s.line([(sx, sy - 17), (sx, fy + fh)], 'ctrl')
    s.text(sx + 8, fy + fh + 30, 'cutoff', size=12, anchor='start', fill=SUB)
    s.line([(390, cy), (390, sy), (sx - 17, sy)], 'ctrl')
    s.text(395, sy + 18, 'filter', size=12, anchor='start', fill=SUB)
    s.line([(690, sy), (sx + 17, sy)], 'ctrl')
    s.text(623, sy - 26, 'cutoff knob,', size=12.5, fill=SUB)
    s.text(623, sy - 10, 'keyboard ⅓ ⅔ full', size=12.5, fill=SUB)

    fcx, fcw = sx - 85, 170
    s.box(fcx, cy, fcw, ch, 'FILTER CONTOUR', ['attack, decay, sustain', 'amount: up to 5 octaves'], 'ctrl', size=14)
    s.line([(sx, cy), (sx, sy + 17)], 'ctrl')

    lcx, lcw = 650, 170
    s.box(lcx, cy, lcw, ch, 'LOUDNESS CONTOUR', ['attack, decay, sustain', 'linear per sample'], 'ctrl', size=14)
    s.line([(vx + vw / 2, cy), (vx + vw / 2, fy + 95)], 'ctrl')
    s.box(855, cy, 120, ch, 'GATE', ['note on/off,', 'sustain pedal,', 'decay switch'], 'note', size=14)
    s.line([(855, cy + ch / 2), (lcx + lcw, cy + ch / 2)], 'ctrl')

    s.legend(330, 605, [('audio', 'audio rate, 48 kHz'), ('ctrl', 'control rate, 3 kHz')])
    s.save('cmsynth_voice')


def ladder():
    s = Svg(1000, 470, 'cmsynth ladder filter')
    s.text(500, 28, 'Ladder filter: zero delay feedback, four one-pole stages', size=19, weight='bold')
    y = 120
    s.text(40, y + 5, 'mixer', size=13, fill=SUB)
    s.circle(105, y, 17, '+')
    s.line([(65, y), (88, y)], 'audio')
    s.text(118, y + 38, '−', size=18, weight='bold')
    b1x = 150
    s.box(b1x, y - 32, 125, 64, '× 1/(1+kG⁴)', ['solves the loop'], 'audio', size=14)
    s.line([(122, y), (b1x, y)], 'audio')
    b2x = 310
    s.box(b2x, y - 32, 115, 64, 'soft clip', ['x − 4x³/27'], 'audio', size=14)
    s.line([(b1x + 125, y), (b2x, y)], 'audio')
    st = [460, 580, 700, 820]
    prev = b2x + 115
    for i, x in enumerate(st):
        s.box(x, y - 32, 95, 64, f'stage {i + 1}', ['1-pole, G'], 'audio', size=14)
        s.line([(prev, y), (x, y)], 'audio')
        prev = x + 95
    s.line([(prev, y), (985, y)], 'audio')
    s.text(950, y - 10, 'to VCA', size=12.5, fill=SUB)

    # Feedback
    fy = 225
    s.line([(960, y), (960, fy), (585, fy)], 'audio', arrow=False)
    s.box(505, fy - 22, 80, 44, '× k', [], 'audio', size=15)
    s.line([(505, fy), (105, fy), (105, y + 17)], 'audio')
    s.text(300, fy + 45, 'feedback k = emphasis × 4.15 (self-oscillates at 4)', size=12.5, fill=SUB)
    s.text(740, fy + 45, 'S: the output\'s part that depends only on the stage states', size=12.5, fill=SUB)

    # One-pole inset
    iy = 290
    s.box(40, iy, 440, 150, '', [], 'note')
    s.text(260, iy + 26, 'One stage (trapezoidal one-pole)', size=15, weight='bold')
    for i, l in enumerate(['v = (x − s) · G', 'y = v + s', 's = y + v        (new state)']):
        s.text(80, iy + 60 + i * 24, l, size=14, anchor='start', family=MONO)
    s.text(80, iy + 134, 'each stage: y = G·x + (1−G)·s', size=12.5, anchor='start', fill=SUB)

    s.box(520, iy, 440, 150, '', [], 'note')
    s.text(740, iy + 26, 'Coefficient, at control rate', size=15, weight='bold')
    for i, l in enumerate(['g = tan(π · fc / fs)', 'G = g / (1 + g)', 'G interpolated per sample']):
        s.text(560, iy + 60 + i * 24, l, size=14, anchor='start', family=MONO)
    s.text(560, iy + 134, 'tan() is a Padé approximation, no libm', size=12.5, anchor='start', fill=SUB)
    s.save('cmsynth_ladder')


def contour():
    rate = 3000.0

    def coef(sec, ratio):
        return 1.0 - math.exp(-1.0 / ((max(sec, 0.0005) / ratio) * rate))

    A, D, S, OFF, END = 0.15, 0.35, 0.5, 0.9, 1.5

    def run(release_s):
        a, d, r = coef(A, 1.466), coef(D, 3.0), coef(release_s, 3.0)
        lvl, stage, pts = 0.0, 'A', []
        for n in range(int(END * rate)):
            t = n / rate
            if t >= OFF and stage != 'R':
                stage = 'R'
            if stage == 'A':
                lvl += (1.3 - lvl) * a
                if lvl >= 1.0:
                    lvl, stage = 1.0, 'D'
            elif stage == 'D':
                lvl += (S - lvl) * d
            else:
                lvl -= lvl * r
            pts.append((t, lvl))
        return pts

    s = Svg(1000, 440, 'cmsynth contour')
    s.text(500, 28, 'Contour (filter and loudness): attack, decay, sustain', size=19, weight='bold')
    x0, y0, pw, ph = 90, 340, 860, 260

    def X(t):
        return x0 + t / END * pw

    def Y(v):
        return y0 - v / 1.3 * ph

    # Axes and grid
    s.add(f'<line x1="{x0}" y1="{y0}" x2="{x0 + pw}" y2="{y0}" stroke="{SUB}" stroke-width="1.5"/>')
    s.add(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 - ph}" stroke="{SUB}" stroke-width="1.5"/>')
    for v, lab in ((1.0, '1.0'), (S, 'sustain'), (1.3, '1.3')):
        s.add(f'<line x1="{x0}" y1="{Y(v)}" x2="{x0 + pw}" y2="{Y(v)}" stroke="#cccccc" stroke-dasharray="4 4"/>')
        s.text(x0 - 8, Y(v) + 4, lab, size=12, anchor='end', fill=SUB)
    for t in (0.0, 0.5, 1.0, 1.5):
        s.text(X(t), y0 + 18, f'{t:.1f} s', size=12, fill=SUB)

    # Gate
    gy = y0 + 62
    s.add(f'<polyline points="{X(0)},{gy} {X(0)},{gy - 14} {X(OFF)},{gy - 14} {X(OFF)},{gy} {X(END)},{gy}" fill="none" stroke="#2f855a" stroke-width="2"/>')
    s.text(X(OFF / 2), gy - 20, 'gate (key held)', size=12, fill='#2f855a')

    # Attack target
    s.line([(X(0), Y(0)), (X(A * 1.25), Y(1.3))], 'ext', arrow=False, dash=True, width=1.2)
    s.text(X(A * 1.25) + 6, Y(1.3) + 16, 'attack aims at 1.3, stops at 1.0', size=12, anchor='start', fill=SUB)

    on = run(D)
    off = [p for p in run(0.005)]
    pts = ' '.join(f'{X(t):.1f},{Y(v):.1f}' for t, v in on[::3])
    s.add(f'<polyline points="{pts}" fill="none" stroke="#c27a12" stroke-width="3"/>')
    pts = ' '.join(f'{X(t):.1f},{Y(v):.1f}' for t, v in off if t >= OFF - 0.01)
    s.add(f'<polyline points="{pts}" fill="none" stroke="#2b6cb0" stroke-width="2.5" stroke-dasharray="7 4"/>')

    s.text(X(A) - 10, Y(1.06), 'attack', size=13, weight='bold', anchor='end')
    s.text(X(A + D / 2), Y(0.82), 'decay: 95% of the way', size=13, weight='bold', anchor='start')
    s.text(X(A + D / 2), Y(0.82) + 17, 'in the decay time', size=12.5, anchor='start', fill=SUB)
    s.text(X(0.62), Y(S) - 10, 'sustain', size=13, weight='bold')
    s.text(X(OFF) + 60, Y(0.42), 'decay switch on:', size=13, weight='bold', anchor='start', fill='#c27a12')
    s.text(X(OFF) + 60, Y(0.42) + 17, 'release uses the decay time', size=12.5, anchor='start', fill=SUB)
    s.text(X(OFF) - 12, Y(0.12), 'decay switch off: 5 ms release', size=12.5, anchor='end', fill='#2b6cb0')
    s.save('cmsynth_contour')


def timing():
    s = Svg(1000, 490, 'cmsynth render timing')
    s.text(500, 28, 'Rendering: double buffered blocks of 64 frames', size=19, weight='bold')
    x0, bw = 150, 200
    lanes = (('DMA → I2S plays', 75), ('CPU renders', 125))
    for lab, y in lanes:
        s.text(x0 - 12, y + 22, lab, size=13, anchor='end', weight='bold')
    halves = ['A', 'B', 'A', 'B']
    for i, h in enumerate(halves):
        x = x0 + i * bw
        s.box(x, 75, bw, 34, f'half {h}', [], 'hw', rx=3, size=13)
        nxt = 'B' if h == 'A' else 'A'
        f, st = STYLE['audio']
        busy = bw * 0.53
        s.add(f'<rect x="{x}" y="125" width="{busy}" height="34" rx="3" fill="{f}" stroke="{st}" stroke-width="2"/>')
        s.text(x + busy / 2, 147, f'fill {nxt}', size=13, weight='bold')
        s.text(x + busy + (bw - busy) / 2, 147, 'idle', size=12, fill=SUB)
        s.add(f'<line x1="{x}" y1="62" x2="{x}" y2="175" stroke="#2f855a" stroke-width="1.5" stroke-dasharray="3 3"/>')
    s.text(x0 + 2 * bw, 55, 'DMA half / full done interrupt: refill the half that just finished', size=12.5, fill='#2f855a')
    s.add(f'<line x1="{x0}" y1="190" x2="{x0 + bw}" y2="190" stroke="{SUB}" stroke-width="1.2" marker-start="url(#a_ext)" marker-end="url(#a_ext)"/>')
    s.text(x0 + bw / 2, 206, '64 frames = 1.33 ms', size=12.5, fill=SUB)
    s.text(x0 + bw + 20, 195, 'rendering 8 voices takes about half of each block (53% on the F407, 48% on the RP2354)', size=12.5, anchor='start', fill=SUB)

    # One block zoomed
    zy = 255
    s.text(500, zy, 'Inside synth_process(), one block', size=15, weight='bold')
    y = zy + 25
    segs = [('noise', 60, 'audio'), ('voice 1', 0, None), ('voice 2', 0, None), ('…', 50, 'note'), ('voice 8', 0, None), ('out', 70, 'audio')]
    vw = (920 - 60 - 50 - 70) / 3
    x = 40
    for lab, w, kind in segs:
        if kind is None:
            # four control steps
            sw = vw / 4
            for c in range(4):
                cx = x + c * sw
                f, st = STYLE['ctrl']
                s.add(f'<rect x="{cx}" y="{y}" width="{sw * 0.2}" height="44" fill="{f}" stroke="{st}" stroke-width="1.5"/>')
                f, st = STYLE['audio']
                s.add(f'<rect x="{cx + sw * 0.2}" y="{y}" width="{sw * 0.8}" height="44" fill="{f}" stroke="{st}" stroke-width="1.5"/>')
            s.text(x + vw / 2, y + 64, lab, size=13, weight='bold')
            x += vw
        else:
            s.box(x, y, w, 44, lab, [], kind, rx=3, size=12.5)
            x += w
    # Key for one control step
    ky = y + 95
    s.text(500, ky, 'One control step = 16 samples (repeated 4 times per voice):', size=13, weight='bold')
    items = [('ctrl', 'voice_control()', 'glide, pitch, modulation, contours, cutoff → G, 1/(1+kG⁴)'),
             ('audio', 'osc_render() × 3', 'one loop per waveform, mixed with the noise into m[16]'),
             ('audio', 'filter + VCA', 'ladder, loudness, pan; added to the L/R mix')]
    for i, (k, a, b) in enumerate(items):
        f, st = STYLE[k]
        yy = ky + 25 + i * 22
        s.add(f'<rect x="170" y="{yy - 12}" width="22" height="14" rx="3" fill="{f}" stroke="{st}" stroke-width="2"/>')
        s.text(202, yy, a, size=13, anchor='start', weight='bold', family=MONO)
        s.text(360, yy, b, size=12.5, anchor='start', fill=SUB)
    s.text(500, ky + 100, 'out: soft clip the mix and convert to int16 into the DMA half', size=12.5, fill=SUB)
    s.save('cmsynth_timing')


if __name__ == '__main__':
    system()
    voice()
    ladder()
    contour()
    timing()
