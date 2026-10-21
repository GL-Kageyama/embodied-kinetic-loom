<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-body-that-lost-its-network.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-body-that-lost-its-network.md) | [日本語](2026-10-21-the-body-that-lost-its-network-ja.md) | [中文](2026-10-21-the-body-that-lost-its-network-zh.md)

# The body that could not find its network — 2026-10-21

⛔ **This page is a record of a body that was alive and could not be reached, and of what it took to reach it.** At the end of it, one sentence crossed the link and **the author heard it** — that is the only ear in this page, and it is theirs.

**What was counted.** One unit, one Mac, one console (`/dev/cu.usbmodem101`), one link (TCP to `192.168.0.103:3333`). **What was not counted:** any packet capture; the boot banner's disconnect reason (it had scrolled before the console was opened); the access point's own log; and ⛔ **whether the screen lit after the cable went in — nobody looked and said so.**

## What the author said first

**The screen was dark** — 「くらい」. ⛔ **And the body was alive at the same moment**: the console was printing `alive`, and `bench pos` answered `yaw raw 492, angle 10.0 deg` and `pitch raw 773, angle 47.8 deg`, with `servo strikes=0 rail=0`. ⇒ **A dark screen was not a dead body**, and the first explanation tried — a flat battery — was wrong.

## What the board said about itself

```
$ bench wifi
wifi: credentials "BFW6K-G-48420", not associated, no ip

$ bench dial
dial: 192.168.0.103:3333, down — 18 dial(s), 0 connect(s)

$ bench wifi scan
wifi: 1 access point(s)
wifi:   "BFW6K-G-48420_EXT" ch 6 rssi -58 auth 3
```

- ⛔ **The SSID the board remembered was not among the ones it could see.** One access point was in range and it was a different name.
- **18 dials, 0 connects** — the dial task was running and had nothing to dial over. ⚠️ **Its retry is 1–10 s and never stops** (`main/dial.cpp`), so **the absence of a dial is evidence about the network, not about the task.**

## What it took

**One line over the console** — `bench wifi join BFW6K-G-48420_EXT …` — and the board associated (WPA2-PSK, ch 6, rssi −57), took **`192.168.0.100`**, and printed its own verdict:

```
dial: connected to 192.168.0.103:3333
```

The daemon's log carries the other side of the same moment:

```json
{"link": "the board dialled in", "peer": "192.168.0.100:63142"}
```

⛔ **The key is not written on this page.** The SSID is; the passphrase is not, and the board's own `bench wifi` never prints it either.

## The first sentence

The mouth was asked for one sentence, 3.4 seconds of speech:

| what | value | where it came from |
|---|---|---|
| the tool's reply | `queued`, exit 0, **0.055 s** | `python3 -m projects.stackchan_next.mouth` |
| the daemon's row | `{"voice": "spoke", "blocks": 41, "bytes": 164294}` | `/tmp/ekl-stackchan-next.log` |
| the board's receipt | **41 blocks, 164,294 bytes, `not played` 0** | `bench dial`, on the board |
| how long the board played | **3,330 ms** | `bench dial` |
| what crossed | `link read 164,744` bytes, **41 heads** | `bench dial` |

**The extra 450 bytes are the heads** — 41 × 11 — which is the arithmetic the 0.19.69 measurement also produced (36 × 11 = 396). ⛔ **`not played: 0` is the board saying it played every block it received**; it is not the board saying the sound was good.

**And the author heard it** — 「聞こえた」. ⛔ **That closes one question and opens nothing**: it does not say the voice is clear, the right size, or right for the role. **The ear in this repository has never been asked a question it could answer with a number.**

## What the source says, and what it does not

- ⛔ **`main/wifi.cpp` does not rejoin a dropped access point.** The `WIFI_EVENT_STA_DISCONNECTED` branch prints the reason and returns; `esp_wifi_connect()` is called once, from `WIFI_EVENT_STA_START`. ⚠️ **That is a reading of the source, not a measurement of this fault** — but it is the shape that makes "powered, alive, unreachable" a state this body can sit in indefinitely.
- ⚠️ **The dial target came from NVS and did not change**: `192.168.0.103` before and after. **The board's own address did change**, from `192.168.0.19` to `192.168.0.100`, and the daemon followed it because the board dials out — **the direction that was proven on 2026-10-21 is the direction that saved it.**

## What is not established

- ⛔ **Whether `BFW6K-G-48420` stopped broadcasting, moved to another channel, or merely fell out of range.** The board saw one access point at its spot and the other was not there; **the access point's side was not read.**
- ⛔ **Why the boot's association failed** — the reason number was printed before the console was opened and was not captured.
- ⛔ **Whether the dark screen was the display or its backlight.** The body answered every question asked of it with the screen dark.
- ⛔ **What `_EXT` is** — an extender, a second band, a second radio: not established here. ⚠️ **The board now remembers that name in NVS**, so it will ask for it at the next boot.
