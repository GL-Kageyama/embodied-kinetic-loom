<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-board-that-would-not-answer.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-board-that-would-not-answer.md) | [日本語](2026-10-21-the-board-that-would-not-answer-ja.md) | [中文](2026-10-21-the-board-that-would-not-answer-zh.md)

# The board that would not answer — 2026-10-21

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A frame the tty accepted is not a frame the board received.

**What was counted.** One unit, one Mac, one USB cable, one replug, and the installed daemon's log from its start at login to the frame that came back. **What was not counted:** why the board went silent, whether its power switch was on, whether anything moved while it was silent, and what the glass showed.

## What was seen

**The author's own account is one sentence:** on 2026-10-20 they shut the Mac down, **and turned the board's power off with it.** On the morning of 2026-10-21 the Mac came back, and the daemon started with it.

**What the host saw, before the replug:**

- the launchd job was running (`embodied-kinetic-loom.stackchan-next`, PID 822) and the socket was up;
- `/dev/cu.usbmodem101` existed, and USB listed **`USB JTAG_serial debug unit` (Espressif)**;
- the daemon wrote **8 frames, all `sent: true`, and not one `accepted: true`**.

**What the host could not get:** the daemon's own probe at `SessionStart` read `{"position": null, "heard": false, "read": ""}`; a hand-written `bench pos` read **nothing**; and `esptool.py read_mac` from the IDF environment failed with **`No serial data received`** — twice, once plainly and once with `--before usb_reset`.

⇒ **The USB device was there and the chip was not answering.**

## The gesture that was planned from a guess

⚠️ **The daemon did not wait.** At `SessionStart` it streamed `look_up`: `{"neck": "look_up", "from": [0, 30], "to": [80, 500], "poses": 40, "seconds": 0.783}`.

⛔ **`from: [0, 30]` is not a measurement.** The board had answered nothing, so there was no last pose and no probe — **and the plan was computed from a default.** Its verdict never arrived (`verdict: null`, `read: ""`).

⚠️ **This is the shape that made the page necessary:** a silent board and a dead board look the same from here, and **the schedule does not distinguish them.**

## The replug

The author wrote 「差し直した」 — the cable came out and went back in. **Then, from the same host and the same code:**

```
bench: yaw=ok pitch=ok
bench: yaw raw 482, angle 6.8 deg (zero 460)
bench: pitch raw 778, angle 49.3 deg (zero 620)
alive
```

and a hand-written frame returned `(sent, accepted) = (True, True)`. **The daemon's own next frames carried `accepted: true`.**

## The numbers, as evidence

| what | value | where it came from |
|---|---|---|
| frames written while silent | 8, every one `sent: true` | the daemon's log |
| frames accepted while silent | **0** | the daemon's log |
| the daemon's probe | `position: null`, `heard: false`, `read: ""` | the daemon's log |
| a hand-written `bench pos` | empty | the host's own tty |
| `esptool.py read_mac` | `No serial data received`, twice | the IDF venv, esptool 4.12.0 |
| poses streamed from `[0, 30]` | 40 — `applied` and `late` never confirmed | the daemon's log |
| after the replug | `yaw raw 482`, `pitch raw 778`, `alive` | the board's own line |
| the frame after that | `sent: true`, `accepted: true` | the board's own line |

## What this file does not say

- ⛔ **It does not say why the board was silent.** The power switch, the cable's seating, a hung firmware and the ROM's own state are **four candidates, and not one was separated.**
- ⛔ **It does not say whether anything moved while the board was silent.** Forty poses were written; **not one was confirmed**, and the board's verdict never came.
- ⛔ **It does not say the glass was black.** ⚠️ **The firmware draws no face at boot**, so a board that is running and a board that is not look the same on the screen — **that is why this file exists, and not a remark about this morning.**
- ⚠️ **It is not a diagnosis.** **A recovery is not a diagnosis** — the page for 2026-10-19 says exactly that about the rail, and this is the same shape a second time.
