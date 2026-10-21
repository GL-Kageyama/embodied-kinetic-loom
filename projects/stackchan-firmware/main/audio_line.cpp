#include "audio_line.h"

#include <cstring>

namespace audio_line {
namespace {

//: ⚠️ `audio ` — six characters, and the space is part of the spelling. `audio
//: 100` is not `audio: 100`: the other line types on this board are JSON and
//: this one is not, so the boundary is the exact word and one space.
constexpr const char* kWord = "audio ";

bool Digit(char c) { return c >= '0' && c <= '9'; }

}  // namespace

bool parse(const char* line, int length, int* bytes) {
  if (line == nullptr || bytes == nullptr) {
    return false;
  }
  const int word = static_cast<int>(std::strlen(kWord));
  if (length <= word) {
    return false;
  }
  if (std::strncmp(line, kWord, static_cast<size_t>(word)) != 0) {
    return false;
  }
  const int first = line[word];
  // ⛔ A leading zero is refused, and so is a sign: this number has one
  //    spelling, so that two hosts cannot disagree about what a block is.
  if (first < '1' || first > '9') {
    return false;
  }
  int value = 0;
  for (int i = word; i < length; ++i) {
    if (!Digit(line[i])) {
      return false;
    }
    value = value * 10 + (line[i] - '0');
    if (value > kMaxBytes) {
      return false;  // ⚠️ refused while reading, not after: no overflow to reach
    }
  }
  //: ⚠️ **Two bytes are one sample.** ⛔ This rule was removed for µ-law on
  //: 2026-10-21 (one byte was one sample) and **it comes back with the format**:
  //: an odd block is half a sample, and a player handed half a sample would
  //: read the last byte as the low half of a value whose high half never came.
  if (value <= 0 || value % 2 != 0) {
    return false;
  }
  *bytes = value;
  return true;
}

}  // namespace audio_line
