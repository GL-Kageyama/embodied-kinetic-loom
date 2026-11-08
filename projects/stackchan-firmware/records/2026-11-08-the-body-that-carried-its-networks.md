<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-11-08-the-body-that-carried-its-networks.md | translated: 2026-11-08 -->

**Language:** [English](2026-11-08-the-body-that-carried-its-networks.md) | [日本語](2026-11-08-the-body-that-carried-its-networks-ja.md) | [中文](2026-11-08-the-body-that-carried-its-networks-zh.md)

# The body that carried its networks — 2026-11-08

✅ **The author carried this body to another place and asked whether it could hold more than one network.** ⛔ **It could not** — one SSID, one PSK, the vendor's single station config, and `bench wifi join` overwrote it. **So the day built a table of four, and the body joined a network it had never seen while the one it was seeded from was out of reach.** ⛔ **And then the link did not cross**: on the same day, the body and the Mac could not reach each other in either direction, while the body reached the gateway in **19 ms**.

**What was counted.** One unit, one Mac, one serial console, and one hard reset. The numbers below come from the board's own lines (`bench wifi`, `bench dial`) and from the Mac's (`arp`, `ping`, `nc`, `ifconfig`, `ioreg`), and each number says which. **What was not counted:** how many networks exist at this place — a scan saw **14**, and a quiet one is invisible; **which SSID the Mac was associated with** — `system_profiler` redacted it, `networksetup` answered *not associated*, and `sudo wdutil info` needs a password it did not have; whether any other wireless client was reachable — there was no second one to ask; and whether the separator is the access point or something behind it — **no packet capture was taken, because it needs root.**

## What the body held before this day

⛔ **Exactly one network.** The station came up from whatever the vendor's wizard had left in NVS, and the console's `bench wifi join` wrote over it: there was no second row, and no way to return to the old one without the password. ⇒ **a body carried to a place whose network it had never seen could be taught that network, and could not be taught to keep both.**

## What was built

✅ **A table of four, in one blob.** `main/wifi_profiles.h` / `.cpp` is a pure module — no ESP-IDF header, compiled on the host by `tests/test_stackchan_wifi_profiles.py` like `wifi_retry.cpp` and `dial_scan.cpp` before it — and it holds:

| what | value | how it was chosen |
|---|---|---|
| rows | **4** | chosen, not measured |
| one row | **97 bytes** — 33 for the SSID, 64 for the PSK | the driver's own field widths, NUL included |
| the blob | at most **390 bytes**, version **1** | 2 + 4 × 97 |
| one row's turn | **2 attempts** | chosen: the second network is reached 6 s after the first attempt, and the 2 / 4 / 8 s ladder is kept |

- ⚠️ **A PSK of 64 characters used to be truncated in silence** — the driver's field is 64 bytes *including* the NUL — so the table refuses a PSK longer than 63 and prints *the psk is longer than 63 characters* rather than shortening it.
- ✅ **`add` updates a row in place and `remove` keeps the order of the others**; the row the radio is on is printed with `*`.
- ✅ **The wait keeps its ladder and only the row moves** — an earlier draft reset the wait with the row, which would have retried every two seconds off-network forever, the busy loop `wifi_retry` exists to avoid.
- ⛔ **The console can override the episode**: `bench wifi join` raises `g_epoch`, and the retry task breaks when the epoch has moved, so **the network a person just chose is not rotated away while they watch**.
- ✅ **Three console verbs**: `bench wifi add <ssid> [psk]` stores without switching, `forget` removes one, `join` stores and connects. ⛔ **Over the link they are refused** — `bench wifi …` is the console's, because a PSK on a plaintext socket is a PSK written on the wire.

## What the unit did

✅ **The first flashed version panicked.** After `wifi: added "Cokoga-5F" (2 of 4)` the board printed **`***ERROR*** A stack overflow in task wifi_retry has been detected`** — `ApplyProfile` copied the whole 390-byte table onto a **3,072-byte** task stack. ⇒ **`RowAt` copies one 97-byte row instead, and the stack is 4,096** (⚠️ **margin, not measured** — 3,072 is the only number the machine gave).

✅ **Measured after the fix, without a reboot**: `wifi: added "Cokoga-5F" (2 of 4)`, `wifi: connected ip=10.5.0.136`, and `wifi: list 2 of 4` names both rows with `*` on the venue's.

✅ **And then a hard reset, which is the measurement the feature exists for** — the body tried the home network first and could not hear it (reason **201, no ap found**):

```
wifi: asking again — attempt 2, waited 4000 ms, on "BFW6K-G-48420_EXT"
wifi: not connected — reason 201 (no ap found)
wifi: trying "Cokoga-5F" (2 of 2)
wifi: asking again — attempt 3, waited 8000 ms, on "Cokoga-5F"
wifi: connected ip=10.5.0.136
wifi: associated after 3 attempt(s)
```

⚠️ **The printed `waited` is the wait just slept**, so the three attempts are 2,000 / 4,000 / 8,000 ms and the association landed at **20.2 s** after boot (`sta ip` at `I (21289)`). ⚠️ **Attempt 1's line is missing from the capture** — the console was opened after it had gone by — so **the first wait is read from the ladder, not from a line**.

✅ **It survived a second boot**: `bench wifi` answered `wifi: list 2 of 4`, `"BFW6K-G-48420_EXT"` unmarked and `* "Cokoga-5F"`, channel 1, RSSI −55. ⇒ **the table is in NVS, not in RAM.**

⚠️ **The console's name moved with the port**: after the cable was moved to another USB port the device became **`/dev/cu.usbmodem101`** where it had been **`.2101`** — ⛔ **the number is the port's, not the board's**, and a script that remembers it will find nothing.

## What the network did

⛔ **Nothing crossed between the body and the Mac, in either direction.**

| direction | what was seen | from |
|---|---|---|
| body → Mac (`10.5.0.114:3333`) | `gave nothing in 3002 ms (errno -1)` | the board's console |
| the same, counted | **976 connect attempt(s) failed**, **0** connect(s), **934 address(es) swept**, **0 found** | `bench dial` |
| Mac → body (`10.5.0.136`) | `? (10.5.0.136) at (incomplete)`, `ping` → `No route to host`, `nc` → `No route to host` | `arp -an`, `ping`, `nc` |
| body → gateway (`10.5.0.1:3333`) | `gave nothing in 19 ms (errno 104)` | the board's console |

⇒ **The body's radio was working** — it reached the gateway's own port and was refused in 19 ms — **and the two wireless clients could not see each other**, while the Mac's firewall was **off** (`socketfilterfw --getglobalstate` → `State = 0`) and only its Wi-Fi interface was up.

⚠️ **The reading is client isolation** — a privacy separator at the access point, the shape a guest network is configured with. ⛔ **It is a reading and not a measurement**: no packet was captured, no second wireless client existed to compare, and **which SSID the Mac was on was not established.**

⚠️ **Three of the failed connections opened and said nothing**: the sweep includes the body's own address, the body's own probe server (`net.cpp`) printed **`net: open from 10.5.0.136`**, and that server answers `ok <n>` per line and never writes `loom`. ⇒ **`3 opened without a greeting` is most likely the body meeting itself** — ⛔ **the counter does not name the peer, so the identity of all three is inferred.**

## What the day tried, and could not

- ⛔ **Another network**: a scan saw 14 access points (`Cokoga-5F`, `monchan-only`, `smartut11`, `Cokoga-4F`, `Buffalo-G-7C98`, `AQyrkDo-7915`, `IODATA-513df8-2G`, `Buffalo-2G-D820`, and weaker copies of the same names), **and the Mac held a saved password for none of them** — the Keychain answered *not in Keychain* for all seven names. ⇒ **a different network needs a password the Mac does not have.**
- ⛔ **Wired**: no Ethernet adapter was ever enumerated — `ioreg -p IOUSB` showed **one device, the Espressif JTAG/serial unit**, and all three Thunderbolt ports answered `No device connected`, with `en4` / `en5` / `en6` `inactive` throughout two cable changes and two ports. ⇒ **there was no second interface to route the link over.**
- ✅ **The author's plan was three steps** — *try several networks, then look for a wire, then give up* — and the day stopped between the first and the second: ⛔ **the router is not the author's to touch** (「ルーターは触れない」), and no wire reached the Mac. **The next attempt is at home** (「家でwifi接続をやってみる」).

## What this record does not say

- ⛔ **That the access point isolates its clients.** The evidence is consistent with it and does not prove it.
- ⛔ **That the table rotates correctly at home.** The home network was seeded as row 1 and never reached from here; **what was measured is a rotation away from it, not a return to it.**
- ⛔ **That the body did anything this day.** No gesture was streamed, no frame was accepted, no face was judged, and **no eye reported the screen** — the daemon's rows read `sent: false, err: "nobody"` from the first minute.
- ⛔ **Whether the glass went dark.** Five minutes without a link is the rule and the link never opened; ⛔ **no one looked**, and a console line wakes the body, and the day typed several.
- ⛔ **That anything is fixed.** A table of four is a mechanism that ran on the unit; **what the author asked for is a body that works where it is carried, and that is not yet observed.**
