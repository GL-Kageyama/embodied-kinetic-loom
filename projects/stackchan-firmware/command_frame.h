// Stack-chan — the device end of the wire (0.19.0).
//
// ✅ Built and flashed on 2026-10-18: the app was written at 0x510000, and the
//    board printed the frames a host wrote to its console.
//
// ⛔ NO NUMBER FOR MACHINE 2 IS IN THIS FILE. A gesture is a name here. The table
//    that turns one into a servo angle was measured on the unit in hand on
//    2026-10-18 and lives in main/main.cpp, beside the record that says where
//    each number came from (records/2026-10-18-the-gestures.md).
//
// ⚠️ The wire carries a command only at a phase transition. It is not a stream.
#pragma once

#include <stdint.h>

enum class Face : uint8_t {
  kNone,
  // ⚠️ The first five are the Pet's, and their drawings are the vendor's skin.
  kCurious,
  kGreeting,
  kHappy,
  kAngry,
  kSleepy,
  // ⚠️ Three words added on 2026-10-24, so that the face can follow the light:
  //    `focused` while a write is in flight, `watching` while a command runs,
  //    and `startled` for the two-second failure flash. ⛔ Their shapes are
  //    choices, not measurements — `face_bitmap.cpp` says where each number
  //    came from, and only an eye says whether the shape reads as the word.
  kFocused,
  kWatching,
  kStartled,
};

enum class Light : uint8_t {
  kOff,
  kDim,
  // ⚠️ Two words added on 2026-10-20, so that `working` can say what it is
  //    working on. ⛔ Their colours are choices, not measurements — the same
  //    standing as the other six.
  kWriting,
  kBusy,
  kBreathe,
  kWarm,
  kAlert,
  kError,
};

enum class Gesture : uint8_t {
  kNone,
  kLookUp,
  kNod,
  kLookSide,
  kRest,
  kRecoil,
};

// ⚠️ A sound is a word, not a frequency — the same rule as a gesture. The
//    word-to-tone table lives in main/sound.cpp, beside the place it was placed
//    by ear. ⛔ `kNone` means this frame is silent; unlike `Light` there is no
//    "keep the last one", because a sound is an event.
enum class Sound : uint8_t {
  kNone,
  kHello,
  kPip,
  kChime,
  kFall,
};

struct Command {
  Face face;
  Light light;
  Gesture gesture;
  Sound sound;
};

enum class ParseResult : uint8_t {
  kOk,
  kTooLong,
  kMalformed,
  kNotAnObject,
  kUnknownKey,
  kMissingKey,
  kBadType,
  kUnknownValue,
};

// Parses exactly one command line. The line may end with a newline; two lines
// are refused, because one frame is one line.
//
// ⛔ An unknown key is refused, not ignored: a field that is merely ignored can
//    ride along, and a prompt is not allowed to ride along.
ParseResult parse_command(const char* line, int length, Command* out);

// ⛔ This function does not move the neck. There is no gesture -> angle table,
//    because every number in such a table would be invented.
void apply_command(const Command& command);
