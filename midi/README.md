# Demo MIDI files

Standard MIDI Files for cmsynth. Each file starts by sending
the complete panel settings (as CCs) for every channel it uses, so it sets up
its own sound no matter what the synth was doing before.

| File | Channels | What it plays |
|------|----------|---------------|
| `bass.mid` | 1 | 16th note bass riff, the filter opens up in the last bar |
| `pad.mid` | 1 | Five note chords with high emphasis and a filter sweep |
| `lead.mid` | 1 | Lead with glide, vibrato from oscillator 3 on the mod wheel |
| `multi.mid` | 1, 2, 3 | Bass, pad (left) and resonant pluck arpeggio (right) at once |
| `popcorn2.mid` | 1-8, 10-14 | Popcorn, converted from an LMMS project with `tools/lmms2mid.py` (2:34) |
| `canon.mid` | 1-6 | Pachelbel's Canon in D: three violins in canon (left, right, centre) over the cello, with a spinet and a theorbo as continuo, converted from LMMS (5:39) |
| `bach-air.mid` | 1-14 | Bach's Air (BWV 1068), a grand orchestral arrangement made with `tools/make_air.py` (3:49) |
| `drum-solo.mid` | 1-14 | A drum solo on the drum kit below, made with `tools/make_drum_solo.py` (1:47) |
| `magnetic-fields-2.mid` | 1-14 | Jean-Michel Jarre's Magnetic Fields, pt. 2, rearranged with `tools/make_magnetic.py` (1:30) |
| `drumkit-test.mid` | 1-14 | Every drum of the kit on its own, three strengths each (1:05) |

### Drum kit

A complete drum kit made only with patch CCs and the mod wheel, no firmware
changes (`tools/drumkit.py`). A cmsynth patch belongs to a channel, so each drum gets
its own channel:

| Channel | Drum | Note | Made from |
|---------|------|------|-----------|
| 1 | Kick | 36 | Triangle at 65 Hz and noise for the beater through a filter that starts high and closes below 65 Hz within about 60 ms: only the first few cycles get through, a thump with a falling pitch instead of a note |
| 2 | Snare | 55 | Two triangles (body) and noise through a falling filter |
| 3 | Rim click | 72 | Narrow pulse and a short, resonant ping |
| 4 | Hi-hat | 84 | Noise high up, very short |
| 5 | Open hi-hat | 84 | The same, longer, choked by the next closed or pedal hi-hat |
| 6 | Crash | 82 | Noise high up, long decay |
| 7 | Splash | 88 | Brighter and shorter |
| 8 | Ride | 86 | A little more of the metal, a ping at the start |
| 9 | Ride bell | 79 | Triangle and metal through a resonant peak, the one cymbal that is meant to ring |
| 10-13 | Toms, high to floor | 55, 50, 45, 40 | Triangle plus a drumhead overtone a fifth up, filter following the note (keyboard tracking) and opening briefly on the hit, noise for the stick |
| 14 | Pedal hi-hat | 84 | The foot closing the hi-hat: darker and shorter |

The hi-hats and cymbals are noise plus two high square waves that the noise
frequency-modulates (noise as the modulation source, mod wheel CC 1 up). On
their own two squares sound like a cowbell; with the noise FM they spread into
a metallic shimmer. The filter is low-pass only; emphasis lowers a ladder
filter's passband, so cutoff and emphasis together shape where the energy sits.

The drums were tuned against recordings of real drums (the samples on
Wikipedia's bass drum, tom, hi-hat, crash and ride cymbal articles) by
comparing octave band spectra: the cymbals put their energy around 2-8 kHz
like the real ones, and the kick and toms have the overtones and stick/beater
content of a drumhead instead of a pure tone.

A note played again on the same channel retriggers that channel's voice, so
every drum uses one voice, like a real drum: the whole kit never needs more
than 14. The open hi-hat has its decay switch off, so a note off chokes
it in 5 ms; the scripts send one whenever the closed or pedal hi-hat plays.
Pan is from the drummer's seat (hi-hat and high tom left, ride and floor tom
right).

`drum-solo.mid` is 51 bars at 120 bpm: a hi-hat intro, a rock groove with
ghost notes, a ride groove, a funk groove with open hi-hat barks, a tom
feature over four on the floor, flams and a snare roll, a double kick build,
a breakdown and a finale. Velocity carries the dynamics and timing and
velocity are slightly humanised. It peaks at 8 voices and 15% CPU on the
RP2354. On the F407's 8 voices it plays too, but a few
cymbal tails get cut short when everything hits at once.

Drums have sharp peaks, so normalising the recording to its peak leaves it
quiet. The drum mp3s are brought up with a limiter on the peaks:
`samples/drum-solo.mp3` to -11 LUFS, `samples/drumkit-test.mp3` to -16 LUFS
(gentler, so the single hits keep their attack).

### Magnetic Fields, pt. 2

`magnetic-fields-2.mid` is made by `tools/make_magnetic.py` from a General
MIDI file of Jean-Michel Jarre's Magnetic Fields, pt. 2
(`tools/magnetic-fields-2-source.mid`, 51 s, "(C)1994 Heavenly Music"). The
script reads the file itself (no MIDI libraries), sets it to the original
record's tempo (a bar in 1.25 s) and rearranges it into a longer piece from
its own sections: an intro with drums and the panning pulse, a groove where
the sequencer's filter opens, the theme and interlude, the second part, the
theme again and the ending.
The patches are inspired by the original record: a bright lead with glide
(the file's pitch bends and mod wheel pass through), a string machine of three
detuned saws, the resonant sequencer pluck, a punchy bass, a resonant "plop"
for the pulse that the file pans back and forth, and drums from the drum kit.

The composition is Jean-Michel Jarre's and still under copyright, as is the
source MIDI file: they are here for playing on the synth, not for videos or
other publication.

### Bach's Air

`bach-air.mid` is made by `tools/make_air.py` from the four parts of the
Bach-Gesellschaft edition as typeset by the [Mutopia Project](https://www.mutopiaproject.org/)
(`tools/bach-air-notes.ly`, by Jeff Covey), under
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/), so the MIDI
file and recordings of it are CC BY-SA 3.0 too. It plays both repeats and
builds up each time through:

1. A section: strings only (two violin parts, viola, cello)
2. A again: double bass, harpsichord continuo (the bass line plus the inner
   parts' chord on every beat), the melody an octave up, timpani at the cadence
3. B section: organ, choir on the long melody notes, celesta
4. B again: tutti with horns, a string ensemble, organ pedal and timpani, a
   broader tempo and a timpani roll under the final fermata

The first violins have vibrato from oscillator 3 that comes in on long notes
(mod wheel ramps) and the trills are played out. 14 channels and up to 27
voices at once, 50% CPU on the RP2354; it needs the RP2354's 32 voices.

### Violins

The violin patch (`violin` in `tools/lmms2mid.py`, used by the Canon and the
Air) was tuned against a recording of a real violin (the open strings in
"Violin sounds and techniques" on Wikipedia's violin article, and the vibrato
in a Telemann sonata for two violins from the same article):

- A saw and a narrow pulse at the same pitch: a plain saw has evenly falling
  harmonics, a violin's jump up and down by around 10 dB from one to the next
  because of the body's resonances. The mix gets about 7 dB, the plain saw had
  3.5.
- A resonant peak around 2.6 kHz that does not follow the note, like a body
  resonance (the "bridge hill"). The old patch's filter at 1.3-1.5 kHz cut
  that region away. Measured over the four open strings the patch now follows
  the real violin within a few dB from 1 to 12 kHz.
- The brightness grows over the first 0.1 s as the bow bites, and a little
  noise is the bow.
- Vibrato at 5.6 Hz and +/- 20 cents, the median measured on the real
  violinist, from oscillator 3. It moves the filter slightly too, so the tone
  flickers with the pitch as a real violin's harmonics move through its body
  resonances. In the Canon every violin has a slightly different vibrato rate.

The cello is made the same way and was tuned against two solo cello
recordings from Wikipedia's cello article (Bach's first suite and a
sarabande): the same saw and pulse mix with the peak lower down (1.6 kHz) for
the bigger body, and a slower vibrato. The old cello patch was very dark (44
dB down at 2 kHz, where a real cello is only about 9 dB down) and had too much
sub bass; the new one follows the real cello within a few dB from 125 Hz to 4
kHz.

A static note sounds like a keyboard however good its spectrum is, so the
cello is also bowed (`bow()` in `tools/lmms2mid.py`, used by the Canon and the
Air): it plays one note at a time, so every note gets its own automation on
the cello's channel. The volume (CC 7) starts at 70%, swells to its peak a
third into the stroke and eases off towards the end, the brightness (cutoff)
follows the same curve as bow pressure does, and the vibrato fades in after
the start of the note. The patch itself has a slower attack and a sustain
that fades a little.

### Continuo in the Canon

A baroque performance of the Canon has continuo players with the cello: an
instrument that plays the chords over the bass line. `tools/lmms2mid.py`
generates them from the cello's notes (`_continuo` in `SONGS`): the chord of
every bass note, from the key, voiced around G3-G4 with the smallest movement
from the previous chord (D, A, Bm, F#m, G, D, G, A).

- A spinet (a small harpsichord) plucks the chord, spread lightly from the
  bottom, and again softer halfway through the bass note.
- A theorbo (a large lute with long bass strings) plays the bass note an
  octave down and breaks the chord upwards, four notes to the bass note.

The strings in the Canon are a little darker than the violin patch on its own:
measured against an ensemble recording of the Canon (violins, cello and
continuo in a hall) the close-miked solo violin tuning was 6-12 dB too bright
between 2 and 4 kHz.

### Electronic demos from LMMS

Converted from demo projects that ship with LMMS
([data/projects/demos](https://github.com/LMMS/lmms/tree/master/data/projects/demos)),
under the licences their authors gave them. The arrangements for cmsynth are
modified versions: the original instruments, samples and effects are replaced
by cmsynth patches.

| File | Original | Author | Licence | Length |
|------|----------|--------|---------|--------|
| `farbro-tectonic.mid` | [Tectonic](https://lmms.io/lsp/index.php?action=show&file=1327) | Farbro | [CC BY](https://creativecommons.org/licenses/by/3.0/) | 3:52 |
| `skiessi-onion.mid` | [Onion](https://lmms.io/lsp/index.php?action=show&file=405) | Skiessi | [CC BY-SA](https://creativecommons.org/licenses/by-sa/3.0/) | 3:28 |
| `momo64-esp.mid` | [esp](https://lmms.io/lsp/index.php?action=show&file=1534) | Momo64 | [Artistic 2.0](https://opensource.org/licenses/Artistic-2.0) | 5:07 |
| `oglsdl-pptrip.mid` | [PpTrip](https://lmms.io/lsp/index.php?action=show&file=1156) | Oglsdl | [Artistic 2.0](https://opensource.org/licenses/Artistic-2.0) | 2:16 |
| `socceroos-progress.mid` | [Progress](https://lmms.io/lsp/index.php?action=show&file=1516) | Socceroos | [Artistic 2.0](https://opensource.org/licenses/Artistic-2.0) | 3:51 |
| `esoxlb-cpu.mid` | [CPU](https://lmms.io/lsp/index.php?action=show&file=723) | E.SoX (lowbudget) | [Artistic 2.0](https://opensource.org/licenses/Artistic-2.0) | 3:46 |

These files keep their original licences, not the MIT licence of the rest of
the repository. When you publish a recording, credit the author and the
licence; recordings of `skiessi-onion.mid` have to be shared under CC BY-SA
too. The licences are listed in LMMS's `LICENSES.TXT` files next to the
projects.

They use up to 16 channels and are dense, so on the STM32F407 (8 voices) a
lot of notes are stolen. They are meant for the RP2354 with 32 voices.
Recordings from the RP2354's line out are in [../samples](../samples) under
the same names (`samples/skiessi-onion.mp3` and so on), with the same
licences.

## Playing them

**Linux** (aplaymidi is in the alsa-utils package):

    aplaymidi -l                                         # find the synth's port
    aplaymidi -p "CurrentMakers cmsynth" midi/bass.mid

**Windows, macOS or Linux with a DAW**: import the file into a MIDI track
(Reaper, Cakewalk, Ableton Live, Logic, ...) and set the track's MIDI output to
"CurrentMakers cmsynth". Make sure the CCs at the start of the file are sent too,
some DAWs strip or chase controllers differently.

Recordings of the same demos are in [../samples](../samples).

## Regenerating

The files are made from the sequences in `tools/demos.py`:

    tools/make_midis.py

## Converting LMMS projects

`tools/lmms2mid.py` turns an LMMS project (`.mmpz` or `.mmp`) into a MIDI
file for the synth:

    tools/lmms2mid.py ~/lmms/projects/Popcorn2.mmpz      # writes midi/popcorn2.mid

- Every instrument track gets its own MIDI channel (1-9, 15, 16) and a
  cmsynth patch (bass, synth bass, acid, organ, pad, brass, reed, lead,
  pluck). Sound font tracks get one from their General MIDI program; LMMS's
  own synths (TripleOscillator, LB302, ZynAddSubFX...) from the track name,
  note range and note lengths; samples from their file name. Track volume and
  pan go into the patch, and the track's base note and oscillator tuning
  into the notes.
- Drums are split by drum into kick, snare, hats, cymbals and toms on
  channels 10-14, each with a drum patch made from the noise source and the
  self-oscillating filter. Both sound font drum kits (bank 128) and drum
  samples (recognised by their file name) are converted.
- Beat/Bassline patterns are expanded wherever they are placed in the song.
  Muted tracks are left out.
- With more tracks than channels, tracks with the same patch share one.
  Effects samples are not converted.
- Volume automation becomes CC 7. The patches go out one channel at a time in
  the first second, then the song starts.
- Tracks that need a specific sound can be given one in `SONGS` in the
  script, by project name and track name.

The F407 has 8 voices, so dense songs steal voices. Popcorn2 peaks at 8
voices and 60% CPU there.
