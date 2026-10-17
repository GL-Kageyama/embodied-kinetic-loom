// Stack-chan — the device end of the wire (0.19.0).
//
// ⛔ SOURCE ONLY. Never built, never flashed.
//
// ⚠️ The parser is deliberately strict and deliberately small. It accepts the
//    shape `{"face": <string|null>, "light": <string>, "gesture": <string|null>}`
//    and nothing else. It does not allocate, and it does not depend on key order.
//
// ⛔ `apply_command` refuses every gesture. That is not a placeholder for a
//    missing line — it is the line, until this unit has been measured.
#include "command_frame.h"

#include <cstring>

namespace {

// The contract's words. `tests/test_stackchan_wire.py` reads these literals and
// refuses the day they disagree with schemas/stackchan-command.schema.json.
const char* const kFaceCurious = "curious";
const char* const kFaceGreeting = "greeting";
const char* const kFaceHappy = "happy";
const char* const kFaceAngry = "angry";
const char* const kFaceSleepy = "sleepy";

const char* const kLightOff = "off";
const char* const kLightDim = "dim";
const char* const kLightBreathe = "breathe";
const char* const kLightWarm = "warm";
const char* const kLightAlert = "alert";
const char* const kLightError = "error";

const char* const kGesturePerk = "perk";
const char* const kGestureNod = "nod";
const char* const kGestureTurn = "turn";
const char* const kGestureSettle = "settle";
const char* const kGestureFlinch = "flinch";

const char* const kKeyFace = "face";
const char* const kKeyLight = "light";
const char* const kKeyGesture = "gesture";

// The longest value is "breathe" (7 bytes); the bound is the host's, with room
// to spare. ⚠️ This is a protocol bound, not a measurement of anything.
const int kMaxLine = 256;

bool Equals(const char* text, int length, const char* word) {
  const int word_length = static_cast<int>(std::strlen(word));
  return length == word_length && std::memcmp(text, word, length) == 0;
}

void SkipSpace(const char* line, int length, int* at) {
  while (*at < length) {
    const char c = line[*at];
    if (c != ' ' && c != '\t' && c != '\r' && c != '\n') {
      return;
    }
    ++*at;
  }
}

bool ReadString(const char* line, int length, int* at, const char** text, int* size) {
  if (*at >= length || line[*at] != '"') {
    return false;
  }
  ++*at;
  const int start = *at;
  while (*at < length && line[*at] != '"') {
    const char c = line[*at];
    if (c == '\\' || c == '\n' || c == '\r') {
      return false;  // no escapes, and no second line
    }
    ++*at;
  }
  if (*at >= length) {
    return false;
  }
  *text = line + start;
  *size = *at - start;
  ++*at;
  return true;
}

bool ReadValue(const char* line, int length, int* at, const char** text, int* size,
               bool* is_null) {
  SkipSpace(line, length, at);
  if (*at + 4 <= length && std::memcmp(line + *at, "null", 4) == 0) {
    *at += 4;
    *is_null = true;
    *text = nullptr;
    *size = 0;
    return true;
  }
  *is_null = false;
  return ReadString(line, length, at, text, size);
}

ParseResult DecideFace(const char* text, int size, Face* out) {
  if (Equals(text, size, kFaceCurious)) { *out = Face::kCurious; return ParseResult::kOk; }
  if (Equals(text, size, kFaceGreeting)) { *out = Face::kGreeting; return ParseResult::kOk; }
  if (Equals(text, size, kFaceHappy)) { *out = Face::kHappy; return ParseResult::kOk; }
  if (Equals(text, size, kFaceAngry)) { *out = Face::kAngry; return ParseResult::kOk; }
  if (Equals(text, size, kFaceSleepy)) { *out = Face::kSleepy; return ParseResult::kOk; }
  return ParseResult::kUnknownValue;
}

ParseResult DecideLight(const char* text, int size, Light* out) {
  if (Equals(text, size, kLightOff)) { *out = Light::kOff; return ParseResult::kOk; }
  if (Equals(text, size, kLightDim)) { *out = Light::kDim; return ParseResult::kOk; }
  if (Equals(text, size, kLightBreathe)) { *out = Light::kBreathe; return ParseResult::kOk; }
  if (Equals(text, size, kLightWarm)) { *out = Light::kWarm; return ParseResult::kOk; }
  if (Equals(text, size, kLightAlert)) { *out = Light::kAlert; return ParseResult::kOk; }
  if (Equals(text, size, kLightError)) { *out = Light::kError; return ParseResult::kOk; }
  return ParseResult::kUnknownValue;
}

ParseResult DecideGesture(const char* text, int size, Gesture* out) {
  if (Equals(text, size, kGesturePerk)) { *out = Gesture::kPerk; return ParseResult::kOk; }
  if (Equals(text, size, kGestureNod)) { *out = Gesture::kNod; return ParseResult::kOk; }
  if (Equals(text, size, kGestureTurn)) { *out = Gesture::kTurn; return ParseResult::kOk; }
  if (Equals(text, size, kGestureSettle)) { *out = Gesture::kSettle; return ParseResult::kOk; }
  if (Equals(text, size, kGestureFlinch)) { *out = Gesture::kFlinch; return ParseResult::kOk; }
  return ParseResult::kUnknownValue;
}

}  // namespace

ParseResult parse_command(const char* line, int length, Command* out) {
  if (line == nullptr || out == nullptr) {
    return ParseResult::kMalformed;
  }
  if (length > kMaxLine) {
    return ParseResult::kTooLong;
  }
  int at = 0;
  SkipSpace(line, length, &at);
  if (at >= length || line[at] != '{') {
    return ParseResult::kNotAnObject;
  }
  ++at;

  bool has_face = false;
  bool has_light = false;
  bool has_gesture = false;
  out->face = Face::kNone;
  out->light = Light::kOff;
  out->gesture = Gesture::kNone;

  SkipSpace(line, length, &at);
  if (at < length && line[at] == '}') {
    return ParseResult::kMissingKey;
  }

  while (at < length) {
    const char* key = nullptr;
    int key_size = 0;
    if (!ReadString(line, length, &at, &key, &key_size)) {
      return ParseResult::kMalformed;
    }
    SkipSpace(line, length, &at);
    if (at >= length || line[at] != ':') {
      return ParseResult::kMalformed;
    }
    ++at;

    const char* value = nullptr;
    int value_size = 0;
    bool is_null = false;
    if (!ReadValue(line, length, &at, &value, &value_size, &is_null)) {
      return ParseResult::kMalformed;
    }

    if (Equals(key, key_size, kKeyFace)) {
      if (has_face) { return ParseResult::kMalformed; }
      has_face = true;
      if (!is_null) {
        const ParseResult r = DecideFace(value, value_size, &out->face);
        if (r != ParseResult::kOk) { return r; }
      }
    } else if (Equals(key, key_size, kKeyLight)) {
      if (has_light) { return ParseResult::kMalformed; }
      has_light = true;
      if (is_null) { return ParseResult::kMissingKey; }
      const ParseResult r = DecideLight(value, value_size, &out->light);
      if (r != ParseResult::kOk) { return r; }
    } else if (Equals(key, key_size, kKeyGesture)) {
      if (has_gesture) { return ParseResult::kMalformed; }
      has_gesture = true;
      if (!is_null) {
        const ParseResult r = DecideGesture(value, value_size, &out->gesture);
        if (r != ParseResult::kOk) { return r; }
      }
    } else {
      return ParseResult::kUnknownKey;
    }

    SkipSpace(line, length, &at);
    if (at < length && line[at] == ',') {
      ++at;
      continue;
    }
    if (at < length && line[at] == '}') {
      break;
    }
    return ParseResult::kMalformed;
  }

  if (!has_face || !has_light || !has_gesture) {
    return ParseResult::kMissingKey;
  }
  SkipSpace(line, length, &at);
  while (at < length && (line[at] == '\n' || line[at] == '\r')) {
    ++at;
  }
  if (at != length) {
    return ParseResult::kMalformed;  // a second line, or trailing bytes
  }
  return ParseResult::kOk;
}

void apply_command(const Command& command) {
  // ⛔ There is no gesture -> angle table here, and there will not be one until
  //    the unit in hand has been measured. Every angle written today would be an
  //    invention. So a gesture that arrives is refused, not guessed.
  //
  // ⚠️ The face and the light are meanings; nothing here turns them into pixels
  //    or into twelve RGB values. The LED order and the colour order of this
  //    unit are in no record either.
  (void)command;
}
