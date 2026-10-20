// The body's second wire: a connection this board opens outward.
//
// ⛔ Why outward. On 2026-10-21 the Mac could not speak first to this board —
//    33 `connect`s, every one `EHOSTUNREACH` in 0.1 ms, with the board's own
//    MAC in the Mac's ARP table the whole time — while every attempt the board
//    made outward arrived and was answered, and one TCP connection the board
//    opened carried both directions (`records/2026-10-21-two-directions.md`).
//    ⇒ If the body is to be driven with the USB cable out, the board must dial.
//
// ⚠️ What this replaces, and what it does not. The console still owns the body:
//    a line from either wire goes through `RunLine`, one at a time, because the
//    servo bus is half-duplex and two tasks inside `Dispatch` at once take each
//    other's replies — 0.19.35's failure, one layer out.
//
// ⛔ What does NOT travel up this link. The console prints about two hundred
//    different lines; only the handful the host parses are mirrored, and they
//    are the ones written through `Say` in `main.cpp`. Everything else stays on
//    the console. ⚠️ A link that carried the whole log would be a log on a wire
//    slower and dearer than the one it already has.
#pragma once

namespace dial {

//: Reads the stored `<ip> <port>` from NVS and starts the dialer. Does nothing
//: but say so when nothing is stored — ⛔ a board that dials an address nobody
//: named is a board that walks out of the room on its own.
void begin();

//: One line: where it is pointed, whether it is up, and what has crossed it.
void report();

//: Stores `<ip> <port>` in NVS and dials it now. `spec` is "<ip> <port>".
//:
//: ⚠️ This is stored because with the USB cable out there is no console to
//:    type it into again. ⛔ The address is a fact about one router's DHCP
//:    lease, not about this machine — if the Mac's address changes, this board
//:    dials a host that no longer answers, and nothing here discovers the new
//:    one. That gap is named, not hidden.
void set(const char* spec);

//: True while a connection is up. ⚠️ Read without the send lock: a false "up"
//: costs one line, and a true "up" on a link that just died costs one drop.
bool up();

//: One line up the link, if one is up. `text` may end in a newline or not.
//: ⛔ Bounded, and it never blocks the caller for longer than `kSendWaitMs`:
//:    the caller is the task that owns the body, and a stalled socket must not
//:    stop a pose stream.
void say(const char* text);

}  // namespace dial
