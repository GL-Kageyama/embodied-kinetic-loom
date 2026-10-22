// The addresses the dialer tries when the one it was given answers nothing.
//
// ⛔ Why this file exists. Until 0.19.75 the dialer knew one address, and that
//    address was a fact about one router's DHCP lease. On 2026-10-23 a reboot
//    moved the Mac from `192.168.0.103` to `192.168.0.106`; the board went on
//    dialling `.103`, the daemon's log filled with `"err": "nobody"`, and
//    nothing on the board said why. ⇒ **The dialer looks for its host instead
//    of assuming where it is.**
//
// ⚠️ The sweep is not a search for services. A candidate is accepted only when
//    it greets: the host writes `loom` as the first line on every connection
//    (`projects/stackchan/daemon/__main__.py`), and an address that says
//    anything else — or nothing at all — is closed and left alone. ⛔ Without a
//    greeting the sweep would drive the body from whatever answers port 3333.
//
// ⚠️ Pure and host-compiled, like `dial_policy.cpp`: no IDF header, no socket.
//    `tests/test_stackchan_dial_scan.py` compiles this file and asks it.
#pragma once

#include <cstdint>

namespace dial_scan {

//: The most addresses one sweep may try: every host of a /24 but `.0` and `.255`.
constexpr int kMaxCandidates = 254;

//: **The order the sweep tries.** Writes up to `max` addresses into `out` and
//: returns how many were written.
//:
//: `known` is `"a.b.c.d"` — the address the console named. It is first, and the
//: rest of its /24 follows nearest-first (`.+1`, `.-1`, `.+2`, `.-2`, …), so a
//: host that moved two doors down is found in three tries and one that moved
//: across the subnet in at most 254.
//:
//: ⛔ Returns 0 when `known` is not an address: a board that swept without
//:    having been pointed anywhere would be a board that walks out of the room.
int candidates(const char* known, uint32_t* out, int max);

//: True when `line` is the host's greeting — `loom`, or `loom` plus a space.
//: ⛔ Matched as a word, never as a prefix: `loomish` is not this host.
bool is_loom(const char* line, int length);

//: Writes `address` as `"a.b.c.d"` into `out`. Returns the length, or 0 when it
//: does not fit — ⛔ **a cut address is an address to somewhere else.**
int format(uint32_t address, char* out, int size);

//: **Whether a sweep may run at this moment, and if not, why.**
enum class Sweep {
  kNow,      //: the named address is silent, there is a route, and the last sweep is old
  kNoRoute,  //: this body has no address of its own to sweep from
  kTooSoon,  //: a sweep ran less than `every_us` ago
};

//: **The rule, without a socket under it.**
//:
//: ⛔ **`kNoRoute` comes first.** On 2026-10-23 the boot dial ran before the
//: station had an address and `connect` returned `ENETUNREACH` in 0 ms; the
//: sweep then "tried" 254 addresses in three seconds and found nothing,
//: because **a missing route and a missing host are one failure to a socket**.
//: ⇒ A body that cannot route has no reason to doubt an address.
//:
//: ⚠️ `last_us == 0` means never, and never is always due.
Sweep sweep_when(bool routed, int64_t now_us, int64_t last_us, int64_t every_us);

}  // namespace dial_scan
