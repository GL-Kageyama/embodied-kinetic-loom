#include "sleep_rule.h"

namespace sleep_rule {

State next(State now, bool present, int64_t absent_us, int64_t after_us) {
  // ⚠️ A connection that is up is a host that is there, whatever the clock says.
  if (present) {
    return State::kAwake;
  }
  // ⚠️ `absent_us < 0` cannot mean "away for ever": it means the clock has not
  //    been read yet, and a body that slept on its first tick would be a body
  //    that never woke.
  if (absent_us >= after_us) {
    return State::kAsleep;
  }
  // ⛔ Inside the window, the state does not move. Asleep stays asleep until a
  //    host arrives; awake stays awake through a drop shorter than the window.
  return now;
}

}  // namespace sleep_rule
