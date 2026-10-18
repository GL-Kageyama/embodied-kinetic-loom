// The screen: a 320 x 240 ILI9342C, and the five faces drawn on it.
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

// Draws one of the five faces. `Face::kNone` clears the screen; it does not
// draw a sixth face.
void show(Face face);

}  // namespace display
