#include "light_colour.h"

namespace {

using Rgb = light_colour::Rgb;

// ⚠️ **A choice, not a measurement: the brightest channel of every screen
//    colour.** The LEDs' own values top out at 160 (`alert`) — at that level a
//    face is a smudge on a 2.8-inch panel in a lit room, because the panel is
//    not a lamp and its area is what carries the light. 232 is high enough to be
//    clearly lit and low enough that the anti-aliased edges keep their places in
//    RGB565 (the top five bits are the channel, so 232 and 255 differ by one
//    step — the coverage is what draws the shape, not the ceiling).
constexpr int kScreenPeak = 232;

// ⛔ **The face in the room's dark.** `light: off` reaches the screen from
//    `resting` every night; the author watched it stay lit on 2026-10-24. A
//    neutral grey rather than a scale of zero — and not the panel's white either,
//    because a face at full brightness on an otherwise dark desk is a lamp.
constexpr Rgb kAsleep = {150, 150, 150};

// Scales a colour so that its largest channel is `kScreenPeak`. ⚠️ The hue is
// preserved exactly — every channel is multiplied by the same factor — because
// the whole point of this table is that the face and the twelve agree on colour.
// ⛔ The largest channel is computed rather than assumed: `error` has no green and
// `alert` has no blue, and scaling on `r` alone would darken one and brighten the
// other by accident.
Rgb Scale(Rgb colour) {
  int peak = colour.r;
  if (colour.g > peak) {
    peak = colour.g;
  }
  if (colour.b > peak) {
    peak = colour.b;
  }
  if (peak == 0) {
    return {0, 0, 0};
  }
  return {static_cast<uint8_t>(colour.r * kScreenPeak / peak),
          static_cast<uint8_t>(colour.g * kScreenPeak / peak),
          static_cast<uint8_t>(colour.b * kScreenPeak / peak)};
}

}  // namespace

bool light_colour::operator==(const Rgb& a, const Rgb& b) {
  return a.r == b.r && a.g == b.g && a.b == b.b;
}

// ⚠️ These are the values `leds.cpp` carried until 2026-10-24, unchanged,
//    including the note that matters: they were multiplied by four on 2026-10-18
//    after the first frame a host sent produced 「無点灯」 in a lit room.
light_colour::Rgb light_colour::LedColour(Light light) {
  switch (light) {
    case Light::kOff:
      return {0, 0, 0};
    // ⚠️ What the unit shows is (24, 24, 40): `SetLedColor` keeps the top five
    //    bits of each channel for RGB565, and 28 & 0xF8 == 24 & 0xF8 == 24,
    //    44 & 0xF8 == 40. ⛔ The three values are written one band higher than
    //    they look, so that the swell in `leds.cpp` crosses a band edge halfway
    //    through its cycle — at 24 the light would sit on the bottom edge of its
    //    band, and the first percent of every dip would drop a whole step at once.
    case Light::kDim:
      return {28, 28, 44};
    // ⚠️ Added on 2026-10-20 with the two words. Both are choices, not
    //    measurements, and neither had been looked at on the unit when it was
    //    written: the question they answer is whether an eye can tell them apart
    //    on a desk, and only an eye answers it.
    case Light::kWriting:
      return {104, 40, 76};
    case Light::kBusy:
      return {24, 104, 88};
    case Light::kBreathe:
      return {40, 48, 72};
    case Light::kWarm:
      return {112, 64, 24};
    case Light::kAlert:
      return {160, 104, 0};
    case Light::kError:
      return {144, 0, 0};
  }
  return {0, 0, 0};
}

light_colour::Rgb light_colour::ScreenColour(Light light) {
  if (light == Light::kOff) {
    return kAsleep;
  }
  return Scale(LedColour(light));
}
