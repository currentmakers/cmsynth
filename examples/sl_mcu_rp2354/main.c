/**
 ******************************************************************************
 * @file           : main.c
 * @brief          : cmsynth on the RP2354 (sl_mcu_rp2354), Arm Cortex-M33
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 CurrentMakers
 *
 * Released under the MIT License, see the LICENSE file in the root of
 * the cmsynth repository.
 *
 ******************************************************************************
 *
 * Same structure as the STM32F407 example: the DMA interrupt says which half
 * of the I2S buffer to refill, the main loop renders it, runs TinyUSB (MIDI
 * goes straight into the synth) and prints a status line every second.
 *
 * Rendering is split over both cores: core 0 renders the even voices, core 1
 * the odd ones, each into its own mix, and core 0 adds them up. Core 1 only
 * runs while core 0 waits for it inside render_block(), so MIDI (handled by
 * core 0 between blocks) never changes a voice while it is being rendered.
 *
 * The system clock is 320 MHz with the core voltage at 1.30 V (overclocked,
 * the RP2350 is rated for 150 MHz at 1.10 V).
 */

#include <stdio.h>
#include <string.h>

#include "hardware/clocks.h"
#include "hardware/dma.h"
#include "hardware/gpio.h"
#include "hardware/irq.h"
#include "hardware/pio.h"
#include "hardware/structs/busctrl.h"
#include "hardware/structs/m33.h"
#include "hardware/sync.h"
#include "hardware/uart.h"
#include "hardware/vreg.h"
#include "pico/multicore.h"
#include "pico/stdio/driver.h"
#include "pico/stdlib.h"

#include "tusb.h"

#include "synth.h"

#include "i2s.pio.h"

// Print cycles per sample for each synth stage at startup
#define SYNTH_BENCHMARK 1

#define LED_DELAY 500   // ms
#define TICK_DELAY 1000 // ms

// PCM5102 audio blade
#define I2S_SD_PIN 21
#define I2S_BCK_PIN 3
#define I2S_LRCK_PIN 24

// Debug UART
#define DEBUG_UART uart0
#define DEBUG_UART_IRQ UART0_IRQ
#define DEBUG_UART_BAUD 921600

// One synth block per half buffer, one 32 bit word (left + right) per frame
#define I2S_DMA_BUFFER_FRAMES SYNTH_BLOCK_SIZE
static uint32_t i2s_dma_buffer[2 * I2S_DMA_BUFFER_FRAMES];

static int16_t *volatile dma_buffer_to_fill = NULL;
static volatile uint32_t dma_overruns = 0; // Half buffers the main loop did not fill in time

static PIO i2s_pio = pio0;
static uint i2s_sm = 0;
static int dma_chan_a = -1;
static int dma_chan_b = -1;

/*
 * Non-blocking printf: characters go into a ring buffer that the UART TX
 * interrupt empties, so debug output never stalls audio rendering. When the
 * buffer is full, characters are dropped rather than waiting.
 */

#define UART_TX_BUFFER_SIZE 2048
static volatile uint8_t uart_tx_buffer[UART_TX_BUFFER_SIZE];
static volatile uint16_t uart_tx_head = 0;
static volatile uint16_t uart_tx_tail = 0;

// Move characters from the ring buffer into the UART FIFO while there is room
static void uart_tx_fill(void) {
    while (uart_tx_tail != uart_tx_head && uart_is_writable(DEBUG_UART)) {
        uart_get_hw(DEBUG_UART)->dr = uart_tx_buffer[uart_tx_tail];
        uart_tx_tail = (uart_tx_tail + 1) % UART_TX_BUFFER_SIZE;
    }
    // The TX interrupt only fires when the FIFO drains below its level, so it
    // is only needed while there is more waiting than fits in the FIFO
    uart_set_irqs_enabled(DEBUG_UART, false, uart_tx_tail != uart_tx_head);
}

static void uart_tx_irq(void) {
    uart_tx_fill();
}

static void uart_ring_out_chars(const char *buf, int len) {
    uint32_t irq = save_and_disable_interrupts();
    for (int i = 0; i < len; i++) {
        uint16_t next = (uart_tx_head + 1) % UART_TX_BUFFER_SIZE;
        if (next == uart_tx_tail)
            break; // Full, drop the rest
        uart_tx_buffer[uart_tx_head] = buf[i];
        uart_tx_head = next;
    }
    uart_tx_fill();
    restore_interrupts(irq);
}

static stdio_driver_t uart_ring_driver = {
    .out_chars = uart_ring_out_chars,
#if PICO_STDIO_ENABLE_CRLF_SUPPORT
    .crlf_enabled = true,
#endif
};

static void debug_uart_init(void) {
    uart_init(DEBUG_UART, DEBUG_UART_BAUD);
    gpio_set_function(PICO_DEFAULT_UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(PICO_DEFAULT_UART_RX_PIN, GPIO_FUNC_UART);
    irq_set_exclusive_handler(DEBUG_UART_IRQ, uart_tx_irq);
    irq_set_enabled(DEBUG_UART_IRQ, true);
    stdio_set_driver_enabled(&uart_ring_driver, true);
}

/*
 * Cycle counter (DWT) for CPU load measurement
 */

static void cycle_counter_init(void) {
    m33_hw->demcr |= M33_DEMCR_TRCENA_BITS;
    m33_hw->dwt_cyccnt = 0;
    m33_hw->dwt_ctrl |= M33_DWT_CTRL_CYCCNTENA_BITS;
}

static uint32_t cycle_counter(void) {
    return m33_hw->dwt_cyccnt;
}

/*
 * I2S output: PIO state machine fed by two DMA channels that chain to each
 * other (ping-pong), each playing one half of the buffer
 */

static void dma_irq_handler(void) {
    if (dma_hw->ints0 & (1u << dma_chan_a)) {
        dma_hw->ints0 = 1u << dma_chan_a;
        dma_channel_set_read_addr(dma_chan_a, &i2s_dma_buffer[0], false);
        if (dma_buffer_to_fill != NULL)
            ++dma_overruns;
        dma_buffer_to_fill = (int16_t *)&i2s_dma_buffer[0]; // A done, B playing: refill A's half
    }
    if (dma_hw->ints0 & (1u << dma_chan_b)) {
        dma_hw->ints0 = 1u << dma_chan_b;
        dma_channel_set_read_addr(dma_chan_b, &i2s_dma_buffer[I2S_DMA_BUFFER_FRAMES], false);
        if (dma_buffer_to_fill != NULL)
            ++dma_overruns;
        dma_buffer_to_fill = (int16_t *)&i2s_dma_buffer[I2S_DMA_BUFFER_FRAMES];
    }
}

static void i2s_dma_channel(int chan, int chain_to, uint32_t *buffer) {
    dma_channel_config c = dma_channel_get_default_config(chan);
    channel_config_set_transfer_data_size(&c, DMA_SIZE_32);
    channel_config_set_read_increment(&c, true);
    channel_config_set_write_increment(&c, false);
    channel_config_set_dreq(&c, pio_get_dreq(i2s_pio, i2s_sm, true));
    channel_config_set_chain_to(&c, chain_to);
    dma_channel_configure(chan, &c, &i2s_pio->txf[i2s_sm], buffer, I2S_DMA_BUFFER_FRAMES, false);
}

static void i2s_init(uint32_t sample_rate) {
    // DMA before the cores on the bus, so audio never waits behind the CPU
    busctrl_hw->priority = BUSCTRL_BUS_PRIORITY_DMA_W_BITS | BUSCTRL_BUS_PRIORITY_DMA_R_BITS;

    uint offset = pio_add_program(i2s_pio, &i2s_program);
    pio_sm_config c = i2s_program_get_default_config(offset);
    sm_config_set_out_pins(&c, I2S_SD_PIN, 1);
    sm_config_set_set_pins(&c, I2S_LRCK_PIN, 1);
    sm_config_set_sideset_pins(&c, I2S_BCK_PIN);
    sm_config_set_out_shift(&c, false, true, 32); // MSB first, autopull 32 bits
    sm_config_set_fifo_join(&c, PIO_FIFO_JOIN_TX);
    float bit_clock = (float)sample_rate * 32.0f;
    sm_config_set_clkdiv(&c, (float)clock_get_hz(clk_sys) / (bit_clock * I2S_PIO_CYCLES_PER_BIT));

    pio_gpio_init(i2s_pio, I2S_SD_PIN);
    pio_gpio_init(i2s_pio, I2S_BCK_PIN);
    pio_gpio_init(i2s_pio, I2S_LRCK_PIN);
    pio_sm_set_consecutive_pindirs(i2s_pio, i2s_sm, I2S_SD_PIN, 1, true);
    pio_sm_set_consecutive_pindirs(i2s_pio, i2s_sm, I2S_BCK_PIN, 1, true);
    pio_sm_set_consecutive_pindirs(i2s_pio, i2s_sm, I2S_LRCK_PIN, 1, true);

    pio_sm_init(i2s_pio, i2s_sm, offset + i2s_offset_entry_point, &c);
    pio_sm_exec(i2s_pio, i2s_sm, pio_encode_set(pio_pins, 0)); // LRCK low: left first

    // Silence in both halves to start with
    memset(i2s_dma_buffer, 0, sizeof(i2s_dma_buffer));

    dma_chan_a = dma_claim_unused_channel(true);
    dma_chan_b = dma_claim_unused_channel(true);
    i2s_dma_channel(dma_chan_a, dma_chan_b, &i2s_dma_buffer[0]);
    i2s_dma_channel(dma_chan_b, dma_chan_a, &i2s_dma_buffer[I2S_DMA_BUFFER_FRAMES]);

    dma_set_irq0_channel_mask_enabled((1u << dma_chan_a) | (1u << dma_chan_b), true);
    irq_set_exclusive_handler(DMA_IRQ_0, dma_irq_handler);
    irq_set_enabled(DMA_IRQ_0, true);

    pio_sm_set_enabled(i2s_pio, i2s_sm, true);
    dma_channel_start(dma_chan_a);
}

/*
 * Rendering on both cores
 */

#define SYNTH_CORES 2

static synth_mix_t mixes[SYNTH_CORES];

// Core 1: wait for a block, render its part of the voices, reply with the
// cycles it took
static void core1_main(void) {
    cycle_counter_init(); // Each core has its own DWT
    while (true) {
        multicore_fifo_pop_blocking();
        uint32_t start = cycle_counter();
        synth_render(&mixes[1], 1, SYNTH_CORES);
        multicore_fifo_push_blocking(cycle_counter() - start);
    }
}

// synth_block_end() writes left, right int16 pairs; the PIO sends the upper
// half word first, so swap the halves to put left there. Returns core 1's
// cycles.
static uint32_t render_block(int16_t *buf) {
    synth_block_begin();
    multicore_fifo_push_blocking(0); // Go, core 1
    synth_render(&mixes[0], 0, SYNTH_CORES);
    uint32_t core1_cycles = multicore_fifo_pop_blocking();
    synth_block_end(buf, mixes, SYNTH_CORES);

    uint32_t *frame = (uint32_t *)buf;
    for (int i = 0; i < I2S_DMA_BUFFER_FRAMES; i++)
        frame[i] = (frame[i] << 16) | (frame[i] >> 16);
    return core1_cycles;
}

int main(void) {
    // Raise the core voltage before the clock
    vreg_set_voltage(VREG_VOLTAGE_1_30);
    busy_wait_us(1000);
    set_sys_clock_khz(SYS_CLOCK_KHZ, true);

    debug_uart_init();

    gpio_init(PICO_DEFAULT_LED_PIN);
    gpio_set_dir(PICO_DEFAULT_LED_PIN, GPIO_OUT);

    printf("\n\n\ncmsynth on the RP2354, Arm Cortex-M33 at %lu MHz, %d voices on %d cores\n",
           clock_get_hz(clk_sys) / 1000000, MAX_VOICES, SYNTH_CORES);

    cycle_counter_init();

    // Cycles available per audio block
    const uint32_t block_budget = clock_get_hz(clk_sys) / SAMPLE_FREQ * SYNTH_BLOCK_SIZE;

    synth_init();
    synth_set_master_volume(0.5f);
#if SYNTH_BENCHMARK
    synth_benchmark(cycle_counter);
#endif
    synth_init();

    multicore_launch_core1(core1_main);

    i2s_init(SAMPLE_FREQ);

    tusb_init();

    uint32_t perf_cycles_sum = 0;
    uint32_t perf_cycles_max = 0;
    uint32_t perf_blocks = 0;
    uint32_t perf_core1_sum = 0;
    uint32_t loop_cnt = 0;
    uint32_t next_blink = LED_DELAY;
    uint32_t next_tick = TICK_DELAY;

    while (true) {
        // Render the next block as soon as the DMA asks for it
        if (dma_buffer_to_fill != NULL) {
            int16_t *buf = dma_buffer_to_fill;
            dma_buffer_to_fill = NULL;
            uint32_t start = cycle_counter();
            perf_core1_sum += render_block(buf);
            uint32_t cycles = cycle_counter() - start;
            perf_cycles_sum += cycles;
            if (cycles > perf_cycles_max)
                perf_cycles_max = cycles;
            ++perf_blocks;
        }

        // USB events, received MIDI goes to the synth (midi.c)
        tud_task();

        uint32_t now = to_ms_since_boot(get_absolute_time());

        if (now >= next_blink) {
            gpio_xor_mask64((uint64_t)1 << PICO_DEFAULT_LED_PIN);
            next_blink = now + LED_DELAY;
        }

        if (now >= next_tick) {
            // cpu: time from start to end of a block (core 0, including the
            // wait for core 1), core1: core 1's own rendering
            uint32_t avg = perf_blocks ? perf_cycles_sum / perf_blocks : 0;
            uint32_t avg1 = perf_blocks ? perf_core1_sum / perf_blocks : 0;
            printf("Tick %lu (loop=%lu) voices=%d cpu avg=%lu.%lu%% max=%lu.%lu%% (%lu/%lu cycles) core1=%lu.%lu%% overruns=%lu\n",
                   now / 1000, loop_cnt, synth_active_voices(),
                   avg * 100 / block_budget, (avg * 1000 / block_budget) % 10,
                   perf_cycles_max * 100 / block_budget, (perf_cycles_max * 1000 / block_budget) % 10,
                   perf_cycles_max, block_budget,
                   avg1 * 100 / block_budget, (avg1 * 1000 / block_budget) % 10, dma_overruns);
            perf_cycles_sum = perf_cycles_max = perf_blocks = perf_core1_sum = 0;
            loop_cnt = 0;
            next_tick = now + TICK_DELAY;
        }

        ++loop_cnt;
    }
}
