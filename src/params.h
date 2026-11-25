/*----------------------------------------------------------------------------
 | @file           : params.h
 | @brief          : Synth parameter table (MIDI CC to patch mapping)
 |----------------------------------------------------------------------------
 | @attention
 |
 | Copyright (c) 2026 CurrentMakers
 |
 | Released under the MIT License, see the LICENSE file in the root of
 | the cmsynth repository.
 |
 |----------------------------------------------------------------------------*/

#ifndef PARAMS_H_
#define PARAMS_H_

#include <stdint.h>
#include <stddef.h>

typedef enum {
    PARAM_LINEAR = 0,   // min + x * (max - min)
    PARAM_EXP,          // min * (max / min) ^ x - for times and frequencies
    PARAM_BIPOLAR,      // CC 64 = centre, mapped to [min, max]
    PARAM_ENUM          // CC 0-127 split evenly into (max + 1) steps, stored as uint8_t
} param_curve_t;

// Parameters with fine set accept a 14-bit value: MSB on cc (< 32), LSB on cc + 32

typedef struct {
    const char *name;
    uint8_t cc;
    param_curve_t curve;
    float min;
    float max;
    size_t offset;      // offsetof() the field in synth_patch_t
    uint8_t fine;       // 14-bit capable (MSB on cc, LSB on cc + 32)
} param_def_t;

// Look up the parameter mapped to a CC number, NULL if none
const param_def_t* param_find_cc(uint8_t cc);

// Apply a CC value to a channel's patch. Handles 14-bit LSBs (CC 32-63) for
// fine parameters. Returns the parameter or NULL if the CC is not mapped.
const param_def_t* param_set_cc(uint8_t channel, uint8_t cc, uint8_t value);

// Read a channel's parameter back as a 7-bit CC value
uint8_t param_get_cc(uint8_t channel, const param_def_t *param);

extern const param_def_t param_table[];
extern const size_t param_count;

#endif /* PARAMS_H_ */
