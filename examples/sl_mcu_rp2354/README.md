# cmsynth on the RP2354

Pico SDK project running cmsynth on the RP2354 (sl_mcu_rp2354 Streamline
board) with the Arm Cortex-M33 cores, audio out through the PCM5102 audio DAC
Streamline blade. The main loop works like the STM32F407 example's, but the
rendering is split over both cores and the chip is overclocked to 320 MHz,
which gives 32 voices.

- USB MIDI device (TinyUSB from the Pico SDK), shows up as "CurrentMakers cmsynth"
- I2S from a PIO state machine fed by two chained DMA channels: 48 kHz, 16 bit
  stereo, 64 frame halves (1.33 ms)
- 320 MHz system clock with the core voltage raised to 1.30 V (`SYS_CLOCK_KHZ`
  in `CMakeLists.txt`, the RP2350 is rated for 150 MHz at 1.10 V)
- 32 voices (`MAX_VOICES` in `CMakeLists.txt`). Core 0 renders the even
  voices and core 1 the odd ones, each into its own mix, then core 0 adds the
  two mixes. Core 1 only works while core 0 waits for it inside
  `render_block()`, and MIDI is handled by core 0 between blocks, so no voice
  is changed while it is being rendered.
- The whole program runs from SRAM (`copy_to_ram`), no flash cache misses
- Arm mode only: CMSIS-DSP did not help on the RP2350 in earlier tests, and the
  synth uses the M33's single precision FPU directly

| Pin | Function |
|-----|----------|
| GPIO 3 | I2S BCK |
| GPIO 24 | I2S LRCK |
| GPIO 21 | I2S SD |
| GPIO 0, 1 | UART0 TX, RX (debug output, 921600 baud) |
| GPIO 37 | LED |

## Performance

Held notes with the worst case patch (three narrow pulses, pink noise, drive,
high emphasis, oscillator and filter modulation on the mod wheel), 320 MHz,
both cores. The load is the time from the start to the end of a block on core 0,
including the wait for core 1:

| Voices | CPU load | Core 1 |
|---|---|---|
| 0 | 1.4% | 0.1% |
| 8 | 19.3% | 16.9% |
| 16 | 36.5% | 33.8% |
| 24 | 53.4% | 50.7% |
| 32 | 70.5% | 67.6% |

Each pair of voices adds about 4.3% at 320 MHz, so 32 leaves room for USB
and the rest.

### Compared with the STM32F407

Before the overclock and the second core, at 150 MHz on one core and with
eight held notes:

| | RP2354, 150 MHz | STM32F407, 168 MHz |
|---|---|---|
| Default patch, 8 voices | 48% (96k cycles per block) | 53% (119k cycles per block) |
| Three oscillators, noise, drive, 8 voices | 69% | |
| Idle (no voices) | 2.1% | |

Per clock cycle the Cortex-M33 does about 20% more work than the F407's
Cortex-M4, so even at its lower clock the RP2354 renders a block about 10%
faster. To measure this again, set `SYS_CLOCK_KHZ` to 150000, `MAX_VOICES`
to 8 and render all voices on core 0.

## Building

The synth source is used straight from [`../../src`](../../src).

**VS Code**: install the Raspberry Pi Pico extension (the recommended
extensions are listed in `.vscode/extensions.json`), open this folder and use
Compile Project. The extension installs Pico SDK 2.3.0 and the toolchain under
`~/.pico-sdk`. The Flash task programs the board through a CMSIS-DAP probe
(the hybridlink) with OpenOCD.

**Command line**, with the SDK and tools from `~/.pico-sdk`:

    export PICO_SDK_PATH=~/.pico-sdk/sdk/2.3.0
    export PATH=~/.pico-sdk/toolchain/15_2_Rel1/bin:~/.pico-sdk/cmake/v3.31.5/bin:~/.pico-sdk/ninja/v1.12.1:$PATH
    cmake -S . -B build -G Ninja
    ninja -C build

The result is `build/cmsynth.elf` (and `.uf2` for the BOOTSEL drive).

## Debug output

UART0 prints every MIDI message and once a second a status line with the
active voices, CPU load per audio block (average and maximum, measured with
the DWT cycle counter), core 1's average load and audio buffer overruns, the same format as the
STM32F407 example. Printing goes through a ring buffer emptied by the UART TX
interrupt, so it never holds up the audio.
