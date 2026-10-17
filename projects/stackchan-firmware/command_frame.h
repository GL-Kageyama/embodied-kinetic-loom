// Stack-chan — the device end of the wire (0.19.0).
//
// ⛔ SOURCE ONLY. This file has never been built, and has never been flashed.
//    Nothing in this repository has ever written a byte to a machine.
//
// ⛔ NO NUMBER FOR MACHINE 2 IS IN THIS FILE, and none will be added until the
//    unit in hand has been measured (docs/first-contact-stackchan.md). A gesture
//    is a name. The table that would turn it into a servo angle is in no record,
//    so `apply_command` refuses instead of guessing.
//
// ⚠️ The wire carries a command only at a phase transition. It is not a stream.
#pragma once

#include <stdint.h>

enum class Face : uint8_t {
  kNone,
  kCurious,
  kGreeting,
  kHappy,
  kAngry,
  kSleepy,
};

enum class Light : uint8_t {
  kOff,
  kDim,
  kBreathe,
  kWarm,
  kAlert,
  kError,
};

enum class Gesture : uint8_t {
  kNone,
  kPerk,
  kNod,
  kTurn,
  kSettle,
  kFlinch,
};

struct Command {
  Face face;
  Light light;
  Gesture gesture;
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
