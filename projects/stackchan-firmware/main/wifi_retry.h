// How long to wait before asking for the access point again.
//
// ⛔ Why this file exists. Until 2026-10-21 the board connected once — at
//    `WIFI_EVENT_STA_START` — and the `WIFI_EVENT_STA_DISCONNECTED` branch
//    printed its reason and returned. Measured on that day: the body was
//    powered and answering (`bench pos` gave yaw 492, pitch 773, and the
//    console printed `alive`), and it sat off the network with
//    `not associated, no ip` while the dial task hammered a socket it had no
//    address to open — 18 dials, 0 connects.
//    ⇒ **A drop is not a state this body may stay in.**
//
// ⚠️ The retry waits rather than spinning: `esp_wifi_connect()` returns at once
//    when no access point is in range, so an immediate retry is a busy loop
//    inside the event task.
// ⚠️ And it does not print every attempt. The note left in 0.19.58 says the
//    first reason is the one worth reading, so the line is rationed and the
//    reason printed by the event handler stays the first one on the console.
//
// ⚠️ The rule lives here, as one function, because a rule that lives only in a
//    comment is this repository's own definition of a defect. `wifi_retry.cpp`
//    takes no IDF header and is compiled on the host by
//    `tests/test_stackchan_wifi_retry.py`.
#pragma once

#include <cstdint>

namespace wifi_retry {

//: The first wait, and the longest. 2 s so that an access point coming back
//: from a reboot is noticed while a person is still standing there; 30 s so a
//: body carried back into range is not away for minutes. ⚠️ **Both are chosen,
//: not measured** — the 2026-10-21 fault was a day, not a curve.
constexpr uint32_t kMinMs = 2000;
constexpr uint32_t kMaxMs = 30000;

//: The next wait: double, never past `kMaxMs`, never below `kMinMs`, and never
//: past what `uint32_t` holds.
uint32_t next(uint32_t waited_ms);

//: Whether this attempt earns a line on the console. The first three do — they
//: say the retry exists and what it is waiting for — and after that every
//: tenth, so a night off the network is tens of lines and not thousands.
bool worth_printing(uint32_t attempt);

}  // namespace wifi_retry
