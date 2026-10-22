#include "dial_scan.h"

#include <cstdio>
#include <cstring>

namespace {

//: ⚠️ `sscanf` with a trailing `%c` so that `192.168.0.103x` is refused: a
//:    rule that read the first four numbers and stopped would dial an address
//:    the console never typed.
bool Parse(const char* text, uint32_t* out) {
  if (text == nullptr) {
    return false;
  }
  unsigned a = 0;
  unsigned b = 0;
  unsigned c = 0;
  unsigned d = 0;
  char tail = 0;
  if (std::sscanf(text, "%u.%u.%u.%u%c", &a, &b, &c, &d, &tail) != 4) {
    return false;
  }
  if (a > 255u || b > 255u || c > 255u || d > 255u) {
    return false;
  }
  *out = (a << 24) | (b << 16) | (c << 8) | d;
  return true;
}

}  // namespace

int dial_scan::candidates(const char* known, uint32_t* out, int max) {
  uint32_t base = 0;
  if (out == nullptr || max <= 0 || !Parse(known, &base)) {
    return 0;
  }
  const uint32_t net = base & 0xFFFFFF00u;
  const int last = static_cast<int>(base & 0xFFu);
  int count = 0;
  out[count++] = base;
  for (int step = 1; step < 256 && count < max; ++step) {
    const int up = last + step;
    const int down = last - step;
    // ⛔ `.0` is the network and `.255` is the broadcast: neither is a host.
    if (up < 255) {
      out[count++] = net | static_cast<uint32_t>(up);
      if (count >= max) {
        break;
      }
    }
    if (down > 0) {
      out[count++] = net | static_cast<uint32_t>(down);
    }
  }
  return count;
}

bool dial_scan::is_loom(const char* line, int length) {
  if (line == nullptr || length < 4) {
    return false;
  }
  if (std::strncmp(line, "loom", 4) != 0) {
    return false;
  }
  return length == 4 || line[4] == ' ' || line[4] == '\t' || line[4] == '\r';
}

int dial_scan::format(uint32_t address, char* out, int size) {
  if (out == nullptr || size <= 0) {
    return 0;
  }
  // ⚠️ **Each field is cast to `unsigned` first.** On the target `uint32_t` is
  //    `unsigned long`, and the firmware builds with `-Werror=format=`: the
  //    same expression that passes on the host fails the build on the board.
  const int need = std::snprintf(
      out, static_cast<size_t>(size), "%u.%u.%u.%u",
      static_cast<unsigned>((address >> 24) & 0xFFu),
      static_cast<unsigned>((address >> 16) & 0xFFu),
      static_cast<unsigned>((address >> 8) & 0xFFu),
      static_cast<unsigned>(address & 0xFFu));
  // ⚠️ `snprintf` returns the length it *would* have written; a value that did
  //    not fit leaves a cut address behind, and a cut address is refused here.
  return (need > 0 && need < size) ? need : 0;
}

dial_scan::Sweep dial_scan::sweep_when(bool routed, int64_t now_us,
                                       int64_t last_us, int64_t every_us) {
  if (!routed) {
    return Sweep::kNoRoute;
  }
  // ⚠️ Never is always due: a body that has just been pointed somewhere has not
  //    wasted a sweep on it yet.
  if (last_us == 0 || now_us - last_us >= every_us) {
    return Sweep::kNow;
  }
  return Sweep::kTooSoon;
}
