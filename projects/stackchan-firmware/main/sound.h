// The speaker: an AW88298 amplifier on the existing I2C bus, fed by I2S.
//
// ⛔ The words are the wire's (`command_frame.h`'s `Sound`). The tones below are
//    this repository's choice, the same way the twelve LEDs' colours are:
//    **no tone here is a measurement**, and the one that was kept is the one the
//    author's ear accepted.
//
// ⚠️ The vendor's numbers, read on 2026-10-18 (hal/board/config.h,
//    cores3_audio_codec.cc, and esp_codec_dev's aw88298 driver): 24,000 Hz,
//    16-bit stereo, MCLK 256 x fs, and the register table in sound.cpp.
#pragma once

#include "command_frame.h"

namespace sound {

// Pulses the amplifier's reset line through the AW9523 (the display owns the
// expander), writes the amplifier's register table, sets the volume and starts
// I2S. False when any of that failed — ⚠️ a silent board must not stop the neck.
bool begin();

// Plays one word. `Sound::kNone` is silence and returns at once.
// ⚠️ Blocking: a whole word is at most a few hundred milliseconds, and the
//    caller is the console task, which nothing else waits on.
void play(Sound word);

// 0..100, mapped the way the vendor's driver maps it (a linear -96..0 dB
// sweep). ⛔ A register value is not a loudness; this is the bench's knob.
bool set_volume_percent(int percent);

}  // namespace sound
