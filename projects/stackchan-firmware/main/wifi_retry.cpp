#include "wifi_retry.h"

namespace wifi_retry {

uint32_t next(uint32_t waited_ms) {
  // ⚠️ The curve starts at `kMinMs`: anything shorter is lifted, not doubled.
  //    A wait of 500 ms that doubled would be 1,000, and the first retry after
  //    a drop is meant to be the first wait — a hole under the curve is a rule
  //    with an exception nobody wrote down.
  if (waited_ms < kMinMs) return kMinMs;
  // ⚠️ The clamp comes before the doubling: `waited_ms * 2` on a value near
  //    `UINT32_MAX` wraps to a small number, and a wrap here would be a retry
  //    every two seconds forever — the busy loop this file exists to avoid.
  if (waited_ms >= kMaxMs) return kMaxMs;
  return waited_ms > kMaxMs / 2 ? kMaxMs : waited_ms * 2;
}

bool worth_printing(uint32_t attempt) {
  // ⚠️ `attempt` is one-based: the first retry is 1. Zero is not an attempt,
  //    and saying so keeps `0 % 10 == 0` from earning a line for a retry that
  //    did not happen.
  if (attempt == 0) return false;
  return attempt <= 3 || attempt % 10 == 0;
}

}  // namespace wifi_retry
