<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-24-the-body-that-slept-itself.md | translated: 2026-10-24 -->

**Language:** [English](2026-10-24-the-body-that-slept-itself.md) | [日本語](2026-10-24-the-body-that-slept-itself-ja.md) | [中文](2026-10-24-the-body-that-slept-itself-zh.md)

# The body that slept itself — 2026-10-24

⛔ **This page is a record of one night, one shutdown, one power-on, and four sentences.** The author shut the Mac down, looked, powered it on, and looked again. **What the eye saw is the spine, and the daemon's numbers are quoted inside it as evidence** — ⚠️ **and the eye is the only witness of the moment the screen went dark, because the row that records the connection carries no time.**

**What was counted.** One unit, one Mac, one night, one pair of eyes. **What was not counted:** the instant the shutdown was given — the link drops when the daemon exits, and that instant is in no log; the instant the power button was pressed — the boot time is read from `kern.boottime`, and the minutes before it are the author's estimate; the twelve LEDs; and ⛔ **the moment the board reconnected**, because `{"link": "the board dialled in", "peer": …}` has no `at` field.

## What the author saw

> macを落として５分間くらいはお休みの顔
> →5分後、お休みの顔すら暗くなった：OK
> 電源を入れても1分くらい顔が暗いまま
> 2分くらいしたら、お休みの顔で起動した

⚠️ **The word the vocabulary gives that face is `sleepy`** — the `resting` phase draws it (`projects/stackchan/behaviors.py`). ⛔ **The panel's own history is in no log**: the daemon's log on this machine holds **12 lines and the first of them is `listening`**, so not one frame from before the shutdown survives, and **what was on the glass at the last moment before it went dark is known only from the eye.**

## What the log has

| what | value | where it came from |
|---|---|---|
| the Mac booted | **04:38:14.811** | `kern.boottime` |
| the daemon started | **04:38:38** — 24 s after the boot | `ps -o lstart` on the process, and `{"daemon": "listening", …}` is the log's first line |
| the board dialled in | ⛔ **no `at`** | `{"link": "the board dialled in", "peer": "192.168.0.100:57946"}` — the log's second line |
| the first frame | `at 179.956` = **04:41:14.8** | the first `ok` row, `UserPromptSubmit`, this session |
| where the probe found the head | `position: [25, 28]`, **yaw raw 468 — 2.5°** (zero 460), **pitch raw 629 — 2.8°** (zero 620) | the probe row, same `at`, `heard: true`, `servo: {strikes: 0, rail: 1}` |
| the first gesture | `look_up`, `[25, 28] → [80, 500]`, 40 poses, 0.787 s | the neck rows, same `at`; its frame `sent: true, accepted: true` |

⚠️ **`at` is `time.monotonic()` — seconds since boot, not since the daemon started.** The cross-check is the daemon's own start: the process began 24 s after `kern.boottime`, and `at` on that first row would be 24 — so the two clocks are one clock.

## The window held, on a real shutdown

0.19.77 measured the same rule by booting the daemon out and opening a stand-in listener. ⚠️ **This one is a Mac actually shut down**: the author's five minutes is the rule running from the link dropping, and the link drops when the daemon exits — a few seconds into the shutdown, before the screen of the Mac is dark.

⛔ **The eye's "about five minutes" is an estimate, not the 301 ± 1 s of the 0.19.77 arithmetic, and the two are not comparable as measurements.** What it settles is coarse and worth having: **the window is not thirty seconds and not thirty minutes** — ⚠️ **one night brackets it; it does not measure it.**

## The screen went dark, and an eye said so

⛔ **0.19.77 recorded this as missing — "no eye saw the screen go dark".** ✅ **This is that eye.** The glass went dark and stayed dark until the host returned.

⚠️ **What the sentence says is that the glass went dark; it does not say the dark reads as asleep.** The author's 「OK」 was given to the sequence — *that is what was expected* — and not as a verdict on how it looked. ⛔ **Whether a dark screen reads as a sleeping body is still the eye's question, and it was not asked that way.**

⚠️ **The drawing survived.** 0.19.77 measured a `bench backlight off` holding the picture for **120 s**; this night carried it from a minute to a whole night, because the face came back without anything redrawing it — see below.

## What came back was the face that was left

⛔ **Nothing redrew it.** The first frame reaches the daemon at **04:41:14.8**, and the eye puts the face back at about two minutes after power-on — **before any frame**. ⇒ **the wake was the connection** (`WakeNow` on the dial link), and what rose with the backlight was the drawing the panel had kept: **the lamp came on over the same face, and the face was the resting one.**

⚠️ **The ~1 minute of dark after power-on and the ~2 minutes until the face are the author's estimates.** ⚠️ **And that minute cannot be told apart from the board's retry-and-sweep cycle**: the daemon started **24 s after boot**, and 0.19.77 measured **97 s** from a listener opening to the connection when the board was caught mid-cycle — ⛔ **this night does not bound that wait either.**

## What this does not establish

- ⛔ **The twelve LEDs.** The author named the face and the darkness and nothing else. The rule writes them `kOff` and `g_light` remembers the last light the host asked for, but no eye said either one came back.
- ⛔ **The instant it went dark.** The eye says about five minutes; the log has no row for it. Neither `display::backlight` nor `bench` writes a line to either wire, and no bench command was typed during the night.
- ⛔ **The instant the link came back.** The `link` row carries no `at`, so the earliest thing the log can place is the first *frame* the connection carried — a minute or so after the eye says the face was already back.
- ⛔ **Where the head sat during the night.** The probe's `yaw 2.5° / pitch 2.8°` is **after the wake**; the neck is limp asleep, and nothing read it between the shutdown and the morning.
- ⛔ **The keepalive.** It has still never fired on the machine. This night's link ended when the daemon exited **and the Mac powered down** — a closed side, not a half-open socket, which is the case `KeepAlive` was written for.
- ⛔ **The USB console.** 0.19.77's run ended with it wedged at `/dev/cu.usbmodem1101`. On this morning `/dev/cu.usb*` **does not exist at all**, and ⚠️ **whether the cable was out or the port did not re-enumerate is not established** — so ⛔ **this page does not say the reboot freed it; there was no node to ask.** Every number above came over the link.
- ⚠️ **One night is not a curve.** The three numbers (5 minutes / 20 s / 10-5-3) remain chosen, and this page measures one shutdown, not their fit.
