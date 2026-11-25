/*----------------------------------------------------------------------------
 | @file           : midi.h
 | @brief          : USB MIDI input handling
 |----------------------------------------------------------------------------
 | @attention
 |
 | Copyright (c) 2026 CurrentMakers
 |
 | Released under the MIT License, see the LICENSE file in the root of
 | the cmsynth repository.
 |
 |----------------------------------------------------------------------------*/

#ifndef MIDI_H_
#define MIDI_H_

#include <stdint.h>

// Handle one MIDI channel message (status byte includes the channel)
void midi_handle_message(uint8_t status, uint8_t data1, uint8_t data2);

#endif /* MIDI_H_ */
