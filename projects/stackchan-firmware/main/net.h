#pragma once

// The board's first listening port.
//
// ⛔ It carries nothing. A connection is accepted, the peer is printed, each
//    line received is answered with its own length and nothing else, and the
//    line is not dispatched. That is on purpose: the console task already owns
//    the body, and a socket task that dispatched would be a second writer on
//    one half-duplex bus — the mistake 0.19.27 measured on the console.
// ⚠️ What this port is for on 2026-10-21 is a measurement, not a protocol:
//    whether a unicast packet from the Mac reaches this board at all.
namespace net_probe {

// Starts the listener. Does nothing when the radio never came up, and says so.
void begin();

// Answers whether the listener is up and how many connections it has served.
void report();

// Sends one UDP datagram to `ip:port` and waits two seconds for anything to
// come back. `spec` is "<ip> <port> <text...>".
//
// ⛔ This is a probe of the path, not a feature of the body: it exists because
//    on 2026-10-21 the Mac could not reach a board that answered ARP, and the
//    question left was whether a packet the board sends first gets an answer —
//    a reply to a flow the board opened is not the same thing, to an access
//    point, as a cold unicast frame aimed at a station that has been quiet.
void send(const char* spec);

// Announces this board's own address by gratuitous ARP.
//
// ⚠️ On 2026-10-21 the Mac held this board's MAC in its ARP table and still
//    could not send to it: every `sendto`, `connect` and unbounded `ping` came
//    back "No route to host", while the entry never once showed `(incomplete)`.
//    ⛔ A gratuitous ARP is the one frame that does not need the Mac to ask.
//    If announcing fixes it, the fault is that the Mac's requests are not
//    arriving — which is a network fault, not this board's.
void announce();

// Opens a TCP connection outward, says one line, and waits for an answer.
// `spec` is "<ip> <port> <text...>".
//
// ⚠️ This is the direction that has been measured to work. Every attempt from
//    the Mac inward was refused by the Mac's own kernel in 0.1 ms; every frame
//    this board sent outward arrived and was answered. If a connection this
//    board opens can also carry the Mac's bytes back, then the body can dial
//    home and no inbound route to the board is ever needed.
void call(const char* spec);

}  // namespace net_probe
