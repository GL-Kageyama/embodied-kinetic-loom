// When the body goes dark, and when it comes back.
//
// ⛔ Why this exists. The host is a Mac that is shut down at night, and the
//    board is powered from a wall outlet and carries a battery: on 2026-10-20
//    the unit ran **9.5 h unplugged**, screen included. ⇒ Cutting the Mac's
//    power does not cut the board's, and the only thing that can switch this
//    body off is the body. Until now the author did it by hand.
//
// ⚠️ The signal is the link, not activity. A Mac that is on and idle holds the
//    dial connection open, so a quiet afternoon does not darken the room; a Mac
//    that is off cannot hold it. ⛔ Activity would put the body to sleep on a
//    quiet day with the host wide awake.
//
// ⛔ Pure and host-compiled, like `dial_scan.cpp`: no IDF header, no clock.
//    `tests/test_stackchan_sleep_rule.py` compiles this file and asks it.
#pragma once

#include <cstdint>

namespace sleep_rule {

//: The two states the body can be in.
enum class State {
  kAwake,
  kAsleep,
};

//: **The next state, from this one.**
//:
//: `absent_us` is how long it has been since a host was last there — a
//: connection, or a line on either wire. `after_us` is how long an absence must
//: last before the body goes dark.
//:
//: ⛔ **Presence wakes at once; absence sleeps only after `after_us`.** The
//:    asymmetry is the rule: a dropped association or a restarted daemon passes
//:    through that window in seconds — 0.19.74 measured 0.3–4 s to re-dial —
//:    and neither may darken the room.
//:
//: ⚠️ `after_us` is an argument, not a constant here, so the number is named
//:    where it is chosen (`main.cpp`) and the rule stays a rule.
State next(State now, bool present, int64_t absent_us, int64_t after_us);

}  // namespace sleep_rule
