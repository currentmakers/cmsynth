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
| `canon.mid` | 1-4 | Pachelbel's Canon in D: three violins in canon (left, right, centre) over the cello, converted from LMMS (11:43) |

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
