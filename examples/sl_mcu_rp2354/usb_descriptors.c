/**
 ******************************************************************************
 * @file           : usb_descriptors.c
 * @brief          : TinyUSB USB descriptors, USB MIDI device
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

#include <string.h>

#include "pico/unique_id.h"
#include "tusb.h"

//--------------------------------------------------------------------+
// Device descriptor
//--------------------------------------------------------------------+

static tusb_desc_device_t const desc_device = {
    .bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = 0x00, // Class defined at interface level
    .bDeviceSubClass = 0x00,
    .bDeviceProtocol = 0x00,
    .bMaxPacketSize0 = CFG_TUD_ENDPOINT0_SIZE,
    .idVendor = 0xCAFE,
    .idProduct = 0x4000,
    .bcdDevice = 0x0100,
    .iManufacturer = 0x01,
    .iProduct = 0x02,
    .iSerialNumber = 0x03,
    .bNumConfigurations = 0x01
};

uint8_t const *tud_descriptor_device_cb(void) {
    return (uint8_t const *)&desc_device;
}

//--------------------------------------------------------------------+
// Configuration descriptor
//--------------------------------------------------------------------+

enum {
    ITF_NUM_MIDI = 0,
    ITF_NUM_MIDI_STREAMING,
    ITF_NUM_TOTAL
};

#define CONFIG_TOTAL_LEN (TUD_CONFIG_DESC_LEN + TUD_MIDI_DESC_LEN)

#define EPNUM_MIDI_OUT 0x01
#define EPNUM_MIDI_IN 0x81

static uint8_t const desc_configuration[] = {
    TUD_CONFIG_DESCRIPTOR(1, ITF_NUM_TOTAL, 0, CONFIG_TOTAL_LEN, 0x00, 100),
    TUD_MIDI_DESCRIPTOR(ITF_NUM_MIDI, 0, EPNUM_MIDI_OUT, EPNUM_MIDI_IN, 64)
};

uint8_t const *tud_descriptor_configuration_cb(uint8_t index) {
    (void)index;
    return desc_configuration;
}

//--------------------------------------------------------------------+
// String descriptors
//--------------------------------------------------------------------+

static char const *string_desc_arr[] = {
    (const char[]){ 0x09, 0x04 }, // 0: English (US)
    "CurrentMakers",              // 1: Manufacturer
    "CurrentMakers cmsynth (RP2354)",      // 2: Product (the MIDI port name)
    NULL,                         // 3: Serial number, the chip's unique id
};

static uint16_t desc_str[48];  // Room for the product name with the MCU

uint16_t const *tud_descriptor_string_cb(uint8_t index, uint16_t langid) {
    (void)langid;
    uint8_t chr_count;
    char serial[2 * PICO_UNIQUE_BOARD_ID_SIZE_BYTES + 1];

    if (index == 0) {
        memcpy(&desc_str[1], string_desc_arr[0], 2);
        chr_count = 1;
    } else {
        if (index >= sizeof(string_desc_arr) / sizeof(string_desc_arr[0]))
            return NULL;

        const char *str = string_desc_arr[index];
        if (index == 3) {
            pico_get_unique_board_id_string(serial, sizeof(serial));
            str = serial;
        }

        chr_count = (uint8_t)strlen(str);
        if (chr_count > 47)
            chr_count = 47;
        for (uint8_t i = 0; i < chr_count; i++)
            desc_str[1 + i] = str[i];
    }

    desc_str[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * chr_count + 2));
    return desc_str;
}
