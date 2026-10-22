// The radio, brought up as a probe — no line changes hands over it.
//
// ⛔ Why this file exists. On 2026-10-21 the host disabled this board's USB
//    port twice — `AppleUSBHostPort::terminateDevice ... hardware port
//    disabled` at 03:24:03, and again at 03:48:01, **70 seconds after the cable
//    was put back**. The board carries its own battery (the PMIC reads it), so
//    a cable replug does not power-cycle the chip: the chip kept running while
//    its USB was gone, and the face on the glass was the last frame it got.
//    ⇒ The console is one wire, and one wire can be taken away by the host
//    without the body dying. This is the first step toward a second path.
//
// ⚠️ What this does NOT do: it carries no frame and no pose, and it changes no
//    existing behaviour. Nothing is routed over it until the numbers are
//    measured — the same rule the whole repository is built on.
//
// ⚠️ The credentials, if any, are the vendor's: `esp_wifi_get_config` reads
//    what the setup wizard stored in NVS. ⛔ Nothing here prints a PSK.
#pragma once

namespace wifi_probe {

//: Netif, event loop, driver, STA mode — then one line either way. Never
//: blocks for longer than the driver's own start.
void begin();

//: What the radio can see: SSID, channel, RSSI, auth mode. ⚠️ Blocks for
//: seconds, like every other `bench` command that asks the machine something.
void scan();

//: Stores an SSID and PSK in NVS and connects. ⛔ The PSK is not printed, and
//: an empty PSK means an open network rather than an empty password.
void join(const char* ssid, const char* psk);

//: One line: whether NVS holds a configuration, whether the station is
//: associated, and the address if it has one.
void report();

//: **Whether this station has an address right now.**
//
// ⛔ **2026-10-23、掃き出しはこれを訊かずに走った。** 起動直後、`dial::begin()`
//    は電波が繋がる前に走り、`connect` は **0 ms で `ENETUNREACH`** を返す——
//    経路が無いのであり、**相手が居ないのではない**。その失敗が掃き出しを
//    起こし、254 の住所が**経路の無いまま**「試された」。⇒ **住所を疑う前に、
//    この体に経路があるかを訊く。**
bool routed();

//: Stops the DHCP client and puts a fixed address on the station, for this boot
//: only. `spec` is "<ip> <mask> <gateway>". Nothing is written to NVS.
//
// ⚠️ This exists to answer one question, and it is the last one left. On
//    2026-10-21 the Mac could not send a single packet to this board: every
//    bound `connect` and `sendto` was refused in 0.1 ms with "No route to
//    host", while `route get` showed a live entry with `expire 1161` and
//    `arp -an` showed this board's own MAC. A refusal that fast is the host
//    synthesising it, not a frame going unanswered — and the gateway, the one
//    host on this link with a *static* /32 route, answered fine on the same
//    bound sockets.
//    ⇒ A different address gets a different entry. If the Mac reaches that
//      one, the fault was one wedged entry and the network is innocent. If it
//      does not, no wireless client is reachable from this Mac, and the answer
//      is the router's or the direction of the connection — not this board's.
void set_address(const char* spec);

}  // namespace wifi_probe
