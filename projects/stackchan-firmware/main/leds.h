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

// ⚠️ A diagnostic for the bench, not a feature of the wire. It prints pin 0 —
//    the servo rail's enable line — register by register, and reads the input
//    register back. ⛔ A bit that says "high" is an enable line that is high;
//    it is not a rail that is powered. The two are one question apart, and
//    only a meter closes the second.
void servo_power_probe();

// ⛔ Written on 2026-10-19, because `servo_power_probe()` could not tell two
//    things apart: an input bit of 0 while the output bit is 1 is either a line
//    held low or a register that does not look at an output. Pin 0 is made an
//    input with a pull-up first (the rail goes off, which is the safe direction),
//    the pad is read, and then the output is restored high so that a diagnostic
//    never leaves the rail switched off. ⚠️ Neither reading is the rail's
//    voltage; only a meter closes that.
void servo_power_level_probe();

// ⚠️ A diagnostic for the bench, not a feature of the wire. It reads back what
//    the expander says it holds, then writes full red to all twelve and reads it
//    again — so that "the registers took the values" and "the pixels lit" become
//    two questions with two answers instead of one word that covers both.
void probe();

}  // namespace leds
