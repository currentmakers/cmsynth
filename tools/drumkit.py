#!/usr/bin/env python3
"""A drum kit for cmsynth, made only with patch CCs: one drum per MIDI channel.

Usage: tools/drumkit.py              (writes midi/drumkit-test.mid: every drum on its own)

cmsynth has one patch per channel, so the kit is spread over 13 channels.
Drums made from the ladder filter ring at their own pitch: the filter is close
to self-oscillation, keyboard tracking is full (so the note tunes the drum) and
a fast filter contour bends the pitch down after the hit.  Hi-hats and cymbals
are noise plus detuned square waves at odd intervals for the metallic part,
through a resonant peak high up.

The open hi-hat has its decay switch off, so a note off chokes it within 5 ms:
play_hat() sends that note off whenever the closed or pedal hi-hat is played,
the way a real hi-hat closes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demos                # noqa: E402
import make_midis           # noqa: E402  (sets demos.LEVEL for files)

# Shared by the hi-hats and cymbals: three detuned square waves
METAL = dict(osc1_range="4'", osc1_wave='square', osc2_range="4'", osc2_wave='square', osc2_detune=6.3,
             osc3_range="2'", osc3_wave='square', osc3_detune=-4.6, osc3_kbd=1, osc3_on=1)

# name: (channel, note, patch).  Pan as seen from the drummer's seat.
KIT = {
    'kick': (0, 33, dict(osc1_range="8'", osc1_wave='tri', osc1_level=1.0, osc2_on=0, noise_on=1, noise_level=0.15,
                         cutoff=55, emphasis=0.9, contour=0.65, kbd=0, f_attack=0.001, f_decay=0.04,
                         f_sustain=0.0, l_attack=0.001, l_decay=0.45, l_sustain=0.0, decay_sw=1, drive=0.7,
                         volume=1.0, pan=0.0)),
    'snare': (1, 55, dict(osc1_range="8'", osc1_wave='tri', osc1_level=0.7, osc2_range="8'", osc2_wave='tri',
                          osc2_detune=7.0, osc2_level=0.4, noise_on=1, noise_level=1.0, cutoff=4500, emphasis=0.25,
                          contour=0.5, kbd=0, f_attack=0.001, f_decay=0.12, f_sustain=0.1, l_attack=0.001,
                          l_decay=0.25, l_sustain=0.0, decay_sw=1, drive=0.3, volume=0.42, pan=0.0)),
    'rim': (2, 72, dict(osc1_range="4'", osc1_wave='narrow', osc1_level=0.6, osc2_on=0, noise_on=1, noise_level=0.3,
                        cutoff=2400, emphasis=0.75, contour=0.3, kbd=0, f_attack=0.001, f_decay=0.02, f_sustain=0.0,
                        l_attack=0.001, l_decay=0.07, l_sustain=0.0, decay_sw=1, volume=0.6, pan=0.05)),
    'hat': (3, 72, dict(METAL, osc1_level=0.35, osc2_level=0.3, osc3_level=0.25, noise_on=1, noise_level=1.0,
                        cutoff=9000, emphasis=0.55, contour=0.2, kbd=3, f_attack=0.001, f_decay=0.03,
                        f_sustain=0.0, l_attack=0.001, l_decay=0.06, l_sustain=0.0, decay_sw=1, volume=0.5,
                        pan=-0.45)),
    'open_hat': (4, 72, dict(METAL, osc1_level=0.35, osc2_level=0.3, osc3_level=0.25, noise_on=1, noise_level=1.0,
                             cutoff=8000, emphasis=0.5, contour=0.2, kbd=3, f_attack=0.001, f_decay=0.25,
                             f_sustain=0.2, l_attack=0.001, l_decay=0.7, l_sustain=0.0, decay_sw=0, volume=0.45,
                             pan=-0.45)),
    'crash': (5, 70, dict(METAL, osc1_level=0.3, osc2_level=0.3, osc3_level=0.3, noise_on=1, noise_level=1.0,
                          cutoff=7000, emphasis=0.3, contour=0.35, kbd=0, f_attack=0.001, f_decay=0.6,
                          f_sustain=0.3, l_attack=0.001, l_decay=2.2, l_sustain=0.0, decay_sw=1, volume=0.6,
                          pan=-0.55)),
    'splash': (6, 76, dict(METAL, osc1_level=0.3, osc2_level=0.3, osc3_level=0.3, noise_on=1, noise_level=1.0,
                           cutoff=9500, emphasis=0.35, contour=0.3, kbd=0, f_attack=0.001, f_decay=0.3,
                           f_sustain=0.2, l_attack=0.001, l_decay=1.0, l_sustain=0.0, decay_sw=1, volume=0.5,
                           pan=0.6)),
    'ride': (7, 74, dict(METAL, osc1_level=0.5, osc2_level=0.45, osc3_level=0.3, noise_on=1, noise_level=0.35,
                         cutoff=5500, emphasis=0.6, contour=0.4, kbd=0, f_attack=0.001, f_decay=0.06,
                         f_sustain=0.35, l_attack=0.001, l_decay=1.6, l_sustain=0.0, decay_sw=1, volume=0.5,
                         pan=0.45)),
    'bell': (8, 79, dict(METAL, osc1_wave='tri', osc1_level=0.7, osc2_level=0.45, osc3_level=0.35, noise_on=0,
                         cutoff=3200, emphasis=0.7, contour=0.3, kbd=0, f_attack=0.001, f_decay=0.1,
                         f_sustain=0.4, l_attack=0.001, l_decay=1.2, l_sustain=0.0, decay_sw=1, volume=0.4,
                         pan=0.45)),
}
# Toms: the note tunes both the triangle body and the ringing filter
TOM = dict(osc1_range="8'", osc1_wave='tri', osc1_level=0.8, osc2_on=0, noise_on=1, noise_level=0.2,
           cutoff=261.6, emphasis=0.92, contour=0.25, kbd=3, f_attack=0.001, f_decay=0.15, f_sustain=0.0,
           l_attack=0.001, l_sustain=0.0, decay_sw=1, drive=0.3, volume=0.9)
for name, ch, note, decay, pan in (('tom1', 9, 55, 0.45, -0.45), ('tom2', 10, 50, 0.55, -0.15),
                                   ('tom3', 11, 45, 0.65, 0.2), ('floor', 12, 40, 0.8, 0.5)):
    KIT[name] = (ch, note, dict(TOM, l_decay=decay, pan=pan))

LEVEL = 0.55       # Whole kit, on top of each drum's volume
PEDAL_NOTE = 60    # The pedal hi-hat is the closed hi-hat played lower (darker, via keyboard tracking)


def setup(seq, t=0.0, level=LEVEL):
    """Send the whole kit, one channel at a time. Returns the time after it."""
    for ch, _, p in KIT.values():
        p = dict(p)
        p['volume'] *= level
        seq.at(t, demos.patch(ch, **p))
        t += 0.05
    return t


class Drummer:
    """Hits on a demos.Seq, with the hi-hat choke."""

    def __init__(self, seq):
        self.seq = seq
        self.open_hat = None       # (note, end time) of a ringing open hi-hat

    def hit(self, t, drum, vel=100, note=None, length=None):
        ch, n, _ = KIT[drum]
        n = n if note is None else note
        vel = max(1, min(127, round(vel)))
        if drum in ('hat', 'pedal') or (drum == 'open_hat' and self.open_hat):
            self.choke(t)
        if drum == 'open_hat':
            self.seq.ev.append((t, (0x90 | ch, n, vel)))
            self.open_hat = (n, t)
            return
        self.seq.note(t, ch, n, length or 0.05, vel)

    def pedal(self, t, vel=70):
        self.choke(t)
        self.seq.note(t, KIT['hat'][0], PEDAL_NOTE, 0.05, max(1, min(127, round(vel))))

    def choke(self, t):
        if self.open_hat:
            n, t0 = self.open_hat
            self.seq.ev.append((max(t, t0 + 0.01), (0x80 | KIT['open_hat'][0], n, 0)))
            self.open_hat = None


def test():
    """Every drum on its own, three times at different strengths, 1.5 s apart."""
    seq = demos.Seq()
    t = setup(seq) + 0.5
    d = Drummer(seq)
    order = ['kick', 'snare', 'rim', 'hat', 'pedal', 'open_hat', 'crash', 'splash', 'ride', 'bell',
             'tom1', 'tom2', 'tom3', 'floor']
    for drum in order:
        for vel in (127, 90, 50):
            if drum == 'pedal':
                d.pedal(t, vel)
            else:
                d.hit(t, drum, vel, length=1.4)
            t += 1.5
        d.choke(t)
    return seq, t + 1.0, order


def main():
    seq, length, order = test()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'midi', 'drumkit-test.mid')
    with open(out, 'wb') as f:
        f.write(make_midis.smf(seq, 'drumkit-test'))
    print(f'{os.path.relpath(out)}: {len(order)} drums, {length:.1f} s')


if __name__ == '__main__':
    main()
