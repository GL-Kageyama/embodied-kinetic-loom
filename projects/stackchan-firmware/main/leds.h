// Twelve LEDs and the servo power switch, both behind the PY32 IO expander.
//
// ⚠️ The register map is the vendor's (m5stack/StackChan, MIT). The colours are
//    this repository's choice: ⛔ no colour for `light` is a measurement, and
//    none is written as if it were.
#pragma once

#include "command_frame.h"

namespace leds {

bool begin();

// `light` is the contract's word. It maps to a colour, or — for `breathe` — to
// a colour that `tick()` modulates.
void set_light(Light light);

// Call often from one context only. Animates `breathe`; does nothing otherwise.
void tick();

// ⛔ This is the only stop this machine has: the servo rail, switched off.
//    Powering it back on leaves the head limp until a goal is written.
bool servo_power(bool on);

// ⚠️ A diagnostic for the bench, not a feature of the wire. It reads back what
//    the expander says it holds, then writes full red to all twelve and reads it
//    again — so that "the registers took the values" and "the pixels lit" become
//    two questions with two answers instead of one word that covers both.
void probe();

}  // namespace leds
