<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-19-the-machine-recovers-itself.md | translated: 2026-10-19 -->

**Language:** [English](2026-10-19-the-machine-recovers-itself.md) | [日本語](2026-10-19-the-machine-recovers-itself-ja.md) | [中文](2026-10-19-the-machine-recovers-itself-zh.md)

# The machine recovers itself — 2026-10-19

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.**

**What was counted.** One unit, one pair of hands, and one deliberate action: `bench power off` was typed into the board's console and then the hands were taken away. The console was read for **40 seconds** afterwards. **What was not counted:** how long a silence lasts in ordinary use, how often one occurs, and what causes one — this file has no evidence about any of the three.

## What was already known when this file starts

**The servo bus had been found silent three times on this unit, and each time the console itself answered while `bench scan` found 0 id(s).** The first was at boot on 2026-10-19 (0.19.29). The second came after one bounded move, and the rail's switch cleared it (0.19.31, 0.19.32). ✅ **What clears it was measured the same day**: `bench power off`, three seconds, `bench power on`, and both ids came back reporting **5.1 V, status 0x00**. ⛔ **Nothing shorter had been tried.**

**The third was found in the installed daemon's log at the start of this session, and it left a window behind it.** The last read-back that carried a position was `[100, 487]` at `at=17537.504`; the first probe that provably met nothing was at `at=18906.163`. **Between them lie 1,368.7 seconds — about 22.8 minutes.** ⚠️ **The log holds no read-back row in that span, so no gesture was sent in it; and neither the daemon nor the board restarted in it.** ⇒ **The bus can go silent with nothing being asked of it.** ⛔ **The window does not name the moment inside it**, and ⛔ **it does not say whether a frame was written in that span** — a frame leaves no position row.

## Seven shapes that did not make it silent

**Before the switch was thrown into the firmware, the silence was chased by command.** Each line below was run on the unit on 2026-10-19, and after each one `bench pos` was asked; every one of them was answered.

| what was done | how many | the bus afterwards |
|---|---|---|
| `bench timed 100 500 0` — one 45° goal with a time field, read every 200 ms for 70 s | once | answered at every read |
| a stream of 50 poses over 1.00 s | once | answered |
| `bench sound hello` — the amplifier at the boot volume | once | answered |
| a frame carrying `chime` written first, then a stream of 78 poses over 1.545 s | once | answered |
| the same event in the daemon's order — probe, stream, then the frame | once | answered, and again at +6, +16, +36 and +66 s |
| the frame written **mid-stream** on its own file descriptor, as the daemon does | once | answered, and again at +1, +4, +10 and +25 s |
| 24 gestures back to back — six rounds of `look_up` / `look_side` / `nod` / `look_up`, each followed by a question | 24 | answered after every one |

⚠️ **A failing reproduction is a measurement too.** ⛔ **It does not say the bus is reliable** — it says that none of these seven shapes is the trigger, so the trigger is somewhere the host cannot type.

## The recovery, in the board's own words

**The firmware now asks the bus two questions every five seconds when it is idle: is id 1 there, is id 2 there.** Three silences in a row are treated as a state; the rail is then thrown for three seconds — the measured clearing duration — and the bus is asked again. **The console printed this, and nothing else touched the machine:**

```
bench: servo power OFF — the expander took the write; the head is limp
servo: no answer (1 of 3 before the rail is cycled)
servo: no answer (2 of 3 before the rail is cycled)
servo: silent for 3 checks — cycling the rail (1 since this boot)
servo: rail cycled — ping yaw=0/3 pitch=3/3
servo: present yaw=496 pitch=777; goals set; torque off
bench: yaw=ok pitch=ok
```

⚠️ **The times, as they were printed against the reader's clock**: first strike at **0.5 s**, second at **5.5 s**, the cycle at **10.5 s**, the bus back at **15.0 s**, and the position read at **15.2 s**. ⇒ **From a rail switched off to a bus answering in about fifteen seconds, with no hand on it.** ⛔ **The first strike came 0.5 s after the command because the five-second tick happened to land there; that is the tick's phase, not the watchdog's speed.**

⚠️ **One reading in that block is not a clean answer**: `ping yaw=0/3 pitch=3/3` — the yaw servo missed three pings 0.3 s after power returned and then read **496** on the next try. **The two axes do not come up at the same instant**, and a single count of pings at one moment cannot say how long that gap is.

## What changed in the source

- **`kRailOffMs = 3000`** — the rail's off time is now the duration that was measured to clear the state. ⛔ **The boot had used 300 ms**: a number that had been chosen and never measured, standing in for a measurement made with three seconds. Boot now costs 3.3 s instead of 0.6 s.
- **`ServoWatchdog()`** in the main loop, beside the pose watchdog and for the same reason — **the console's read blocks, so the console task cannot notice a silence it is not in.** It asks every **5 s**, cycles on the **third** silence, and prints every step.
- ⛔ **`main.cpp` is compiled by no check** — `tests/test_stackchan_frame_parser.py` builds `command_frame.cpp` and `tests/test_stackchan_face.py` builds `face_bitmap.cpp`; the watchdog, like the rest of the entry point, is verified by the board printing what it did.

## What this does not say

- ⛔ **It is not the diagnosis.** The trigger of the silence is still unnamed. **This is a recovery, and a recovery is not a diagnosis.**
- ⛔ **It does not say the rung is closed.** The seventh rung asks that answering be **guaranteed**; what is now guaranteed is that a silence is noticed and cleared within seconds — ✅ **and that each one is printed**, so the next occurrence leaves a line where none existed before.
- ⛔ **It does not say the watchdog cannot fire wrongly.** A ping that fails for a reason other than a silent servo — a bus contention, a lost byte — counts as a silence like any other. **Three in a row is what a race would have to do to fool it**, and nothing here measured how often a single ping fails on a healthy bus.
- ⚠️ **It does not describe the goal.** A bus that answers is the body. Whether anything is there is a different file.
