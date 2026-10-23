// The screen: a 320 x 240 ILI9342C, and the eight faces drawn on it.
//
// ⛔ Not every number here is a measurement. The pins, the panel, the two I2C
//    devices and the face's shapes are the vendor's record (m5stack/StackChan,
//    MIT); the rasterizer is this repository's (face_bitmap.cpp). No register
//    value below was discovered by this repository.
#pragma once

#include "command_frame.h"

namespace display {

// Creates the SPI bus and the panel IO, resets the panel through the AW9523,
// turns the backlight on through the AXP2101, sends the ILI9342C init sequence
// and clears the screen. False when any of that failed — ⚠️ the neck and the
// LEDs must keep working either way, so the caller does not abort on false.
bool begin();

// Draws one of the eight faces. `Face::kNone` clears the screen; it does not
// draw a ninth face.
void show(Face face);

// **The face takes the light's colour.** Reads the light word through
// `light_colour::ScreenColour` — one table, two media (`main/light_colour.cpp`)
// — and repaints what is already drawn, because a frame that moves only the
// twelve carries `face: null` and no second frame follows it.
//
// ⛔ Called with every frame, from `apply_command`, so the drawing can never
//    wear a light that has gone. ⚠️ `off` is not black: `resting` sends it every
//    night and the sleeping face stayed lit on the unit (2026-10-24).
void tint(Light light);

// **The backlight's own switch, and nothing else.**
//
// The backlight is DLDO1 on the AXP2101, and its enable is **bit 7 of register
// `0x90`** (`XPowersLib`: `enableDLDO1` sets that bit). ⚠️ The vendor's boot
// sequence writes `0xBF` there — bit 7 high, the other six rails as they were —
// so this clears and sets one bit and leaves every other rail alone.
//
// ⛔ The voltage register `0x99` is not touched. Dimming it to the vendor's 0 %
// (value 20, 2.5 V) leaves the panel glowing, which is not what a dark room
// asks for; the author's word for the asleep screen is 「真っ暗」.
//
// ⚠️ The panel keeps what was drawn: this is a lamp, not a blank. Returning
// `true` means the PMIC took the write — ⛔ not that the eye saw dark.
bool backlight(bool on);

// Call often from the main loop, one context only. Closes and reopens the lids
// by itself — ⚠️ two frames, about 60 ms, every 3.2–6.8 s, and never on `sleepy`
// (whose lids are already nearly shut). The mouth does not move: a blink is an
// eye, not an expression. ⛔ Nothing is sent over the wire for it, so no log
// grows and no host is involved.
void tick();

// ⚠️ The AW88298's reset line is P0.2 on the AW9523 — the expander this module
//    already owns. The speaker asks for that pulse here rather than opening the
//    expander twice: one bus, one owner. False if this module never came up.
bool pulse_amplifier_reset();

// ⚠️ A diagnostic for the bench, not a feature of the wire. It reads the
//    AXP2101's two status registers and the battery voltage — whether a battery
//    is present, which way the current flows, and what the battery reads.
//    ⛔ It does not measure the servo rail: a battery at 4.0 V and a rail at
//    0 V are consistent with a switch that is not conducting, and only a meter
//    separates them.
void pmu_probe();

}  // namespace display
