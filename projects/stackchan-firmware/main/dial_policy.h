// Which commands may arrive over the network, and which must be typed at the board.
//
// ⛔ Why this file exists at all. Since 0.19.60 the same line dispatcher is fed
//    from two wires: the USB console and a TCP link the board dials outward.
//    They are not the same channel. The console is a person holding the object;
//    the link is a socket, and a socket can be anything on the segment.
//    ⇒ A command that changes how this board is reached is the console's.
//
// ⚠️ The rule is written as one sentence and checked as one function, because a
//    rule that lives only in a comment is this repository's own definition of a
//    defect. `dial_policy.cpp` compiles on the host under
//    `tests/test_stackchan_link_policy.py` and takes no IDF header.
#pragma once

namespace dial_policy {

//: True when this line must be typed at the console and must not be obeyed
//: from a socket.
//:
//: ⛔ `bench wifi …` carries the SSID and the PSK, writes them to NVS, or puts a
//:    new address on the station — and `bench dial …` repoints the link itself.
//:    A PSK sent down a plain TCP socket is a PSK written on the wire, which is
//:    the same thing the console echo rule already forbids on this side.
//: ⇒ The whole of both verbs is the console's, not just the sub-verb that
//:   looks dangerous: a rule that has to judge which spelling is safe will one
//:   day judge wrong, and the wrong judgement is silent.
bool console_only(const char* line);

}  // namespace dial_policy
