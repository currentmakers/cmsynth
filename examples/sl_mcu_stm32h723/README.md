# cmsynth on the STM32H723

STM32CubeIDE project running cmsynth on an STM32H723VE (Arm Cortex-M7) at
550 MHz, with audio out through the PCM5102 audio DAC Streamline blade.

- USB MIDI device on USB OTG_HS in full speed mode with the internal PHY
  (TinyUSB, root port 1), shows up as "CurrentMakers cmsynth (STM32H723)"
- I2S2 to the PCM5102: 48 kHz, 16 bit stereo, DMA with 64 frame halves
  (1.33 ms)
- 32 voices; with every voice playing the most expensive patch the synth uses
  about 86% of the CPU per audio block, on one core
- Voice state in the 128K DTCM (`.dtcmram`, zero wait states, never touched
  by DMA). The data cache is on, so every rendered half of the DMA buffer
  (in the AXI SRAM) is cleaned to RAM before the DMA sends it.

| Pin | Function |
|-----|----------|
| PB10 | I2S2_CK |
| PB12 | I2S2_WS |
| PC3_C | I2S2_SD |
| PA11, PA12 | USB OTG_HS D-, D+ (internal full speed PHY) |
| PA9, PA10 | USART1 TX, RX (debug output) |

The hardware setup (`sl_mcu_stm32h723.ioc`) comes from the earlier
`sl_mcu_stm32h723_i2s_midi_polysynth` example: 16 MHz crystal, PLL1 with the
fractional divider to 550 MHz (VOS0). Everything cmsynth adds is in the
USER CODE sections, so the project can be regenerated in CubeMX.

## Building

The synth source is not copied into the project: `cmsynth` is a link to
[`../../src`](../../src) and `tinyusb` a link to `../../lib/tinyusb/src`, so
clone with submodules first (see the [top README](../../README.md)).
`MAX_VOICES=32` is set in the project's compiler defines.

In STM32CubeIDE: File > Import > Existing Projects into Workspace, select this
folder, then build. Or headless:

    stm32cubeide/headless-build.sh -data /tmp/ws -import examples/sl_mcu_stm32h723 \
        -build sl_mcu_stm32h723/Debug

Flash with STM32CubeProgrammer:

    STM32_Programmer_CLI -c port=SWD mode=UR -w Debug/sl_mcu_stm32h723.elf -v -rst

## Debug output

USART1 at 921600 baud prints the cycle benchmark at startup, every MIDI
message and once a second a status line with the active voices, CPU load per
audio block (average and maximum) and audio buffer overruns:

    cmsynth on the STM32H723 (550 MHz, 32 voices)
    bench voice_render      223 cycles/sample (whole voice)
    Tick 40 (loop=454870) voices=32 cpu avg=84.6% max=86.1% (631812/733312 cycles) overruns=0

The user button cycles oscillator 1's waveform on channel 1.
