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

}  // namespace wifi_probe
