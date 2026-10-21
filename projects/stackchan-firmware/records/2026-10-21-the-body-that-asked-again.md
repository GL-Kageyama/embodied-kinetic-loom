<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-body-that-asked-again.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-body-that-asked-again.md) | [日本語](2026-10-21-the-body-that-asked-again-ja.md) | [中文](2026-10-21-the-body-that-asked-again-zh.md)

# The body that asked again — 2026-10-21

⛔ **This page is a record of one drop, five questions, and a body that kept running with no network under it.** **The author carried the unit about 50 m away and brought it back.** ⚠️ **The console never lost a line**, so the window below is whole. **What the author did is the spine, and the program's numbers are quoted inside it as evidence.**

**What was counted.** One unit, one console (`/dev/cu.usbmodem101`, read by a capture that stamps every line), one access point (`BFW6K-G-48420_EXT`, channel 6), and one walk. **What was not counted:** the access point's own log; any packet capture; the last beacon's timestamp — the driver waits **25,000 ms** of missed beacons before it calls the drop, and that wait is a setting, not a measurement of this walk — and ⛔ **whether anything on the screen moved while the body was away: nobody looked and said so.**

## What the author did

**Carried it about 50 m away from the access point** — the author's own estimate — and brought it back. ⚠️ **The USB cable went with it**, and the capture held the port from 17:55 to the end of the run; **not one line is missing.**

## What the board said

```
17:59:31.360 wifi: not connected — reason 200 (beacon timeout)
17:59:31.361 dial: the host let go
17:59:33.360 wifi: asking again — attempt 1, waited 2000 ms
17:59:35.770 wifi: not connected — reason 201 (no ap found)
17:59:37.361 wifi: asking again — attempt 2, waited 4000 ms
17:59:39.771 wifi: not connected — reason 201 (no ap found)
17:59:45.362 wifi: asking again — attempt 3, waited 8000 ms
17:59:47.772 wifi: not connected — reason 201 (no ap found)
18:00:03.771 wifi: not connected — reason 201 (no ap found)
18:00:31.369 wifi:state: init -> auth (0xb0)
18:00:31.745 wifi:connected with BFW6K-G-48420_EXT, aid = 9, channel 6, 40U, bssid = dc:62:79:d0:ad:2e
18:00:31.746 wifi:security: WPA2-PSK, phy: bgn, rssi: -72, cipher(pairwise:0x3, group:0x3), pmf:0
18:00:31.751 wifi: associated — waiting for an address
18:00:32.843 esp_netif_handlers: sta ip: 192.168.0.100, mask: 255.255.255.0, gw: 192.168.0.254
18:00:32.844 wifi: connected ip=192.168.0.100
18:00:32.860 wifi: associated after 5 attempt(s)
18:00:39.102 dial: connected to 192.168.0.103:3333
```

- ⛔ **The first reason is 200 and every attempt after it is 201.** 200 is an association that lost its beacons; 201 is a connect that found no access point. **Both are the driver's words**, and the access point's side was not read.
- **`dial: the host let go` arrives 1 ms after the drop** — the link dies with the radio, because it is a socket on that radio.
- ⛔ **`alive` kept printing every 3 s from 17:59:33.965 to 18:00:30.963** — **twenty lines with no network under the body at all.** The body did not stop when its network did.
- **The address that came back is the same one**: `192.168.0.100`, one DHCP lease, so a reconnection does not need a new address to be found.

## The attempts that printed nothing

⛔ **The console showed three `asking again` lines and the board counted five.** `wifi_retry::worth_printing` prints the first three attempts and then every tenth, so **attempts 4 and 5 left no line at all.**

| attempt | waited | when the connect was issued | was it printed |
|---|---|---|---|
| 1 | 2,000 ms | 17:59:33.360 | ✅ |
| 2 | 4,000 ms | 17:59:37.361 | ✅ |
| 3 | 8,000 ms | 17:59:45.362 | ✅ |
| 4 | 16,000 ms | 18:00:01.362 | ⛔ **no line** |
| 5 | **30,000 ms** — the ceiling | 18:00:31.362 | ⛔ **no line** |

⚠️ **The two unprinted times are arithmetic from the waits that were printed, not lines the board emitted.** The failures behind them are lines: `reason 201` at 18:00:03.771 belongs to attempt 4.

⇒ **A reader who counts `asking again` lines undercounts the attempts.** The board's own count is the number that holds: `wifi: associated after 5 attempt(s)` on the console, and `5 retries since boot, last drop reason 201 (no ap found)` from `bench wifi` at 18:01:43.

## What came back

| what | value | where it came from |
|---|---|---|
| the association | `init -> auth` at 18:00:31.369, `assoc -> run` at 18:00:31.540 | the driver's own lines |
| the signal | **rssi −72** (it was −56 before the walk) | `wifi:connected` |
| the address | `192.168.0.100`, **1.48 s after the association** | `esp_netif_handlers` |
| the board's count | `wifi: associated after 5 attempt(s)`, **16 ms after the address** | the retry task |
| the link | `dial: connected to 192.168.0.103:3333`, **6.24 s after the address** | `dial.cpp` |
| after it | `associated, 192.168.0.100`, **rssi −61**, `5 retries since boot`, `sys_evt stack 1604 bytes never used` | `bench wifi` |

⛔ **The stack margin did not move**: 1,604 bytes never used at 17:55:06 (boot) and 1,604 at 18:01:43, **after the event task had run six disconnect events.** The 4,096 tick that fixed the 0.19.59 boot loop still holds under the load this page measured.

## What this does not establish

- ⛔ **Whether a network that comes back is noticed before the wait ends.** The fifth connect was issued at 18:00:31.362 and the association landed 7 ms later — **the two coincided, so this run cannot say how long a body waits after its access point returns.** ⇒ **By design it is up to 30,000 ms**: the wait ends on an association, and an access point returning is not an event this task listens for. ⚠️ **This run does not measure that window.**
- ⛔ **Why the first reason was 200** — the access point's side was not read, and the last beacon was not timestamped.
- ⛔ **The distance.** 50 m is the author's estimate; the walls between are not counted.
- ⛔ **The screen.** Nothing was said about what it showed while the body was away.
- ⚠️ **The ceiling was reached once, on the fifth attempt.** A longer outage would print attempts 10 and 20 and nothing between them — **that is the rule, and this run does not show it.**
- ⚠️ **One walk is not a curve.** The rule's two numbers (2,000 ms and 30,000 ms) were chosen, and this page measures the shape of one drop, not the fit of the curve.
