// The five faces as pixels — pure, no IDF, so a host can draw and check them.
//
// ⛔ The drawing is the vendor's default skin: a black screen, two white eye
//    discs with a black lid over each, and a white mouth bar. The numbers are
//    lifted from `skins/default/eyes.cpp` and `mouth.cpp` (M5Stack, MIT) and
//    named in `face_bitmap.cpp`; this file is the same shapes without LVGL.
// ⚠️ The vendor draws through LVGL, which anti-aliases its circles; a one-bit
//    renderer reproduced the shapes and not the smoothness. So the buffer is
//    8-bit grey: the coverage of each pixel, 0..255, and the panel sends it as
//    RGB565. ⛔ The middle values are not decoration — they are what stops a
//    20-pixel circle from being a staircase.
#pragma once

#include <stdint.h>

#include "command_frame.h"

namespace face_bitmap {

constexpr int kWidth = 320;
constexpr int kHeight = 240;
constexpr int kBytes = kWidth * kHeight;  // one byte of grey per pixel: 76,800

//: Fills `grey` (kBytes, one byte per pixel) with the face. `Face::kNone` fills
//: it with zeroes: the screen goes blank, because "no expression" is not one of
//: the five.
void render(Face face, uint8_t* grey);

//: Draws the same face with both lids closed — one frame of a blink. ⚠️ Same
//: mouth, same places; the lid is the only thing that moves, because a blink is
//: an eye and not a sixth expression.
void render_blink(Face face, uint8_t* grey);

//: Whether a blink is drawn for this face. ⛔ False for `sleepy`, whose lids are
//: already nearly shut, and for `kNone`, which is not a face. ⚠️ The rule lives
//: here rather than in `display.cpp` so that it can be asked on a host.
bool can_blink(Face face);

}  // namespace face_bitmap
