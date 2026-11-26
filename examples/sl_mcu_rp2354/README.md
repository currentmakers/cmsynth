# cmsynth on the RP2354

Pico SDK project running cmsynth on the RP2354 (sl_mcu_rp2354 Streamline
board) with the Arm Cortex-M33 cores, audio out through the PCM5102 audio DAC
Streamline blade. It is set up like the STM32F407 example so the two can be
compared directly: one core renders the audio, runs USB MIDI and prints the
status line, the other core is not used yet.

- USB MIDI device (TinyUSB from the Pico SDK), shows up as "CurrentMakers cmsynth"
- I2S from a PIO state machine fed by two chained DMA channels: 48 kHz, 16 bit
  stereo, 64 frame halves (1.33 ms)
- 150 MHz system clock (`SYS_CLOCK_KHZ` in `CMakeLists.txt`)
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
the DWT cycle counter) and audio buffer overruns, the same format as the
STM32F407 example. Printing goes through a ring buffer emptied by the UART TX
interrupt, so it never holds up the audio.
