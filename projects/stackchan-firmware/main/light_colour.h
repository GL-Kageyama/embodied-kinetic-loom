// One table, two media: what a light word means as twelve pixels, and as a face.
//
// ⛔ No colour in this file is a measurement. The eight LED colours are this
//    repository's choices — `leds.cpp` said so first, and said why they are dim
//    (twelve pixels at full brightness in a dark room is a lamp, not a face).
//
// ⚠️ **Why the table moved here on 2026-10-24.** It lived in an anonymous
//    namespace inside `leds.cpp`, so nothing else could ask what colour a light
//    word was. The author's word for this change was
//    「光の色に合わせて、今の白抜きの表情を、その光の色と同じにしよう」 — one hue for
//    the room and the face — and **a second copy of the table is the one thing
//    that would let the two drift apart**. One table, two readings.
#pragma once

#include <stdint.h>

#include "command_frame.h"

namespace light_colour {

struct Rgb {
  uint8_t r;
  uint8_t g;
  uint8_t b;
};

bool operator==(const Rgb& a, const Rgb& b);

//: The twelve LEDs' colour. ⛔ `off` is black here, and that is right: an LED
//: that is not lit is not lit.
Rgb LedColour(Light light);

//: The face's colour — **the same hue, brighter**, because a 320x240 panel
//: showing a 20-pixel disc at an LED's dim value is a smudge, not a face.
//:
//: ⛔ **`off` is not black here, and the exception is the point.** `resting`
//: sends `light: "off"` every night, and on 2026-10-24 an eye watched that
//: state: the sleeping face stayed lit for about five minutes on a Mac that had
//: been shut down (records/2026-10-24-the-body-that-slept-itself.md). **A screen
//: that followed `off` to black would have deleted the drawing the author saw.**
//: So `off` returns a neutral grey — ⚠️ a chosen value, not a measurement, and
//: the one row whose job is to stay visible.
//:
//: ⚠️ The screen does not breathe and does not swell: `breathe` takes its own
//: colour and stands still. The twelve move; the drawing is the thing that is
//: looked at, and a face that pulsed would be a second animation on one event.
Rgb ScreenColour(Light light);

}  // namespace light_colour
