#include "dial_policy.h"

#include <cstring>

namespace {

//: ⚠️ Matched as `<verb>` or `<verb> `, never as a prefix, so that a future
//:    `bench wifiish` is not swept in by a rule that only meant the verb.
bool IsVerb(const char* line, const char* verb) {
  const size_t length = std::strlen(verb);
  if (std::strncmp(line, verb, length) != 0) {
    return false;
  }
  return line[length] == '\0' || line[length] == ' ';
}

}  // namespace

bool dial_policy::console_only(const char* line) {
  if (line == nullptr) {
    return false;
  }
  // ⚠️ The console's own spelling is `bench <verb> …`; `HandleBench` is handed
  //    the text after `bench`, and this rule is handed the whole line.
  if (std::strncmp(line, "bench ", 6) != 0) {
    return false;
  }
  // ⛔ **`HandleBench` skips leading spaces** (`main.cpp`, its second line), so
  //    `bench  wifi` is a command the board really runs. A rule that did not
  //    skip the same ones would let exactly that spelling through — and the
  //    hole would be invisible, because every other spelling still had it.
  //    ⚠️ Found by `tests/test_stackchan_dial_policy.py` on 2026-10-21, before
  //    it ever reached a unit.
  const char* verb = line + 6;
  while (*verb == ' ') {
    ++verb;
  }
  return IsVerb(verb, "wifi") || IsVerb(verb, "dial");
}
