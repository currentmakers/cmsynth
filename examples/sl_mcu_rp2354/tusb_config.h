/**
 ******************************************************************************
 * @file           : tusb_config.h
 * @brief          : TinyUSB configuration, USB MIDI device
 ******************************************************************************
 * @attention
 *
 * Copyright (c) 2026 CurrentMakers
 *
 * Released under the MIT License, see the LICENSE file in the root of
 * the cmsynth repository.
 *
 ******************************************************************************
 */

#ifndef _TUSB_CONFIG_H_
#define _TUSB_CONFIG_H_

#ifdef __cplusplus
extern "C" {
#endif

// The Pico SDK sets CFG_TUSB_MCU (OPT_MCU_RP2040, also used for the RP2350)
#ifndef CFG_TUSB_MCU
#error CFG_TUSB_MCU must be defined
#endif

#ifndef CFG_TUSB_OS
#define CFG_TUSB_OS                 OPT_OS_NONE
#endif
#define CFG_TUSB_DEBUG              0

#define CFG_TUD_ENABLED             1
#define BOARD_TUD_RHPORT            0
#define CFG_TUD_MAX_SPEED           OPT_MODE_FULL_SPEED
#define CFG_TUSB_RHPORT0_MODE       (OPT_MODE_DEVICE | OPT_MODE_FULL_SPEED)

#ifndef CFG_TUSB_MEM_SECTION
#define CFG_TUSB_MEM_SECTION
#endif

#ifndef CFG_TUSB_MEM_ALIGN
#define CFG_TUSB_MEM_ALIGN          __attribute__((aligned(4)))
#endif

#define CFG_TUD_ENDPOINT0_SIZE      64

// USB MIDI only
#define CFG_TUD_MIDI                1
#define CFG_TUD_CDC                 0
#define CFG_TUD_MSC                 0
#define CFG_TUD_HID                 0
#define CFG_TUD_VENDOR              0

#define CFG_TUD_MIDI_RX_BUFSIZE     64
#define CFG_TUD_MIDI_TX_BUFSIZE     64

#ifdef __cplusplus
}
#endif

#endif /* _TUSB_CONFIG_H_ */
