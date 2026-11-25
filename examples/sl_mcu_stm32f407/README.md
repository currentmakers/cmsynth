# cmsynth on the STM32F407

STM32CubeIDE project running cmsynth on an STM32F407VE at 168 MHz, with audio
out through the PCM5102 audio DAC Streamline blade.

- USB MIDI device on USB OTG FS (TinyUSB), shows up as "CurrentMakers cmsynth"
- I2S2 to the PCM5102: 48 kHz, 16 bit stereo, DMA with 64 frame halves
  (1.33 ms)
- 8 voices; with every voice playing the default patch the synth uses about
  53% of the CPU
- Voice state in the 64K core coupled RAM

| Pin | Function |
|-----|----------|
| PB10 | I2S2_CK |
| PB12 | I2S2_WS |
| PC3 | I2S2_SD |
| PA11, PA12 | USB OTG FS D-, D+ |
| PA9, PA10 | USART1 TX, RX (debug output) |

## Building

The synth source is not copied into the project: `cmsynth` is a link to
[`../../src`](../../src) and `tinyusb` a link to `../../lib/tinyusb/src`, so
clone with submodules first (see the [top README](../../README.md)).

In STM32CubeIDE: File > Import > Existing Projects into Workspace, select this
folder, then build. Or headless:

    stm32cubeide/headless-build.sh -data /tmp/ws -import examples/sl_mcu_stm32f407 \
        -build sl_mcu_stm32f407/Debug

Flash with STM32CubeProgrammer:

    STM32_Programmer_CLI -c port=SWD mode=UR -w Debug/sl_mcu_stm32f407.elf -v -rst

## Debug output

USART1 at 921600 baud prints every MIDI message and once a second a status
line with the active voices, CPU load per audio block (average and maximum)
and audio buffer overruns. Turn the CPU measurement off with
`SYNTH_BENCHMARK` in `Core/Src/main.c` and the MIDI log with `MIDI_LOG`.
`MAX_VOICES` sets the number of voices.

The user button cycles oscillator 1's waveform on channel 1.
