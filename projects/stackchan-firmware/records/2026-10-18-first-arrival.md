<!-- i18n-version: 1.2.0 | canonical: projects/stackchan-firmware/records/2026-10-18-first-arrival.md | translated: 2026-10-18 -->

**Language:** [English](2026-10-18-first-arrival.md) | [日本語](2026-10-18-first-arrival-ja.md) | [中文](2026-10-18-first-arrival-zh.md)

# The first arrival — 2026-10-18

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A log that holds only what the program emitted cannot contain the thing this record is for — whether anything moved — and it reads as proof when it is not.

**What was counted.** One command, typed once, into one machine, on one day. **What was not counted:** anything about whether the result is alive, and anything about this engine's trajectories — none ran here.

## What was seen

**The author was watching the unit.** In their words: the head had been turned to the right, and it **turned to face front**. It did not glide. It moved a little, stopped, moved a little, stopped — audible as a small repeated *jiji* — and the stops were visible as stops.

⚠️ **No instrument recorded this. It is an eye on a desk, and it is the only thing in this file that can say the machine moved at all.**

## What was typed

One line, into the app's console, over the same USB cable that carried the build:

```
bench move 5
```

⛔ **This is a bench command, not the engine.** It does not read a `Motion Intent`, and it does not interpolate, ease, smooth or limit. **It writes a new goal position every second and lets the servo step to it** — by design, because the point of this first arrival was to learn whether *anything* arrives, not to move well.

## What the program said

```
bench: yaw=ok pitch=ok
bench: yaw raw 604, angle 45.0 deg (zero 460)
bench: pitch raw 894, angle 85.6 deg (zero 620)
bench: yaw 604 -> 476 (raw), one step per second
bench: yaw -> raw 601
bench: yaw -> raw 598
bench: yaw -> raw 595
   … one line per second, three counts each …
bench: yaw -> raw 478
```

**What the numbers say:** the yaw servo (ID 1) was **read** at 604 before the move — that read is the one the bench printed — and the target was 476 raw. The once-per-second lines are the **commands written**, not read-backs: the last one written was 478, two counts short of the target. **The one read-back after the motion** came from the next boot, which reported yaw 484. **The scale is the vendor's** — one count is 0.3125° — so the head was asked to travel 128 counts, 40°, and was found 120 counts from where it started.

**What the numbers cannot say:** whether the head moved. ⛔ **A servo that is told a new position is not a witness; only the read-back after the fact is, and it says the shaft ended somewhere else.** That 484 is a measurement; *that the head turned* is the author's eye. The two agree to within six counts — about 1.9°, which is the sag of an unpowered head after torque was released, and is not itself measured.

⚠️ **The move was interrupted, not finished.** The last two counts of the target were never written: the read-back opened the serial port, the chip restarted, and the boot released torque at whatever position the shaft was in. **The console window I had opened was shorter than the move** — 40 seconds for a 43-second command. That is my error, recorded here because a later reader will see 478 and 476 and wonder.

## Why it moved in stops

⚠️ **The stops are the command, not a fault.** `bench move` computes a target, then rewrites the goal a few counts closer once per second (`kStepIntervalMs` 1000, `kStepCounts` 3). Between writes the servo is stationary — so the machine spends most of each second not moving. **Measured only as the console's own once-per-second line; the smoothness was not measured at all.**

⇒ **The visible result is what this repository exists to remove.** The trajectory family, easing and smoothing turn a list of stops into a path. **On 2026-10-18 none of them ran on this machine.** What ran was the bench.

## Two defects that stopped everything before this

⚠️ **Nothing had moved before this day, and neither reason was the hardware.**

| what was wrong | how it showed | what it was |
|---|---|---|
| the ping checksum summed **four** bytes instead of three | `ping yaw=0/3 pitch=0/3` while `read` on the same id answered | a ping carries no parameters, so the checksum covers ID + LEN + INST and stops; the fourth byte was the unwritten checksum itself |
| the two-byte fields were written and read **low byte first** | a present position of 604 arrived as `0x02, 0x5C` and parsed as **23554** | the vendor's SCSCL driver is built with `End = 1`, whose `Host2SCS`/`SCS2Host` put the **high byte first** |

⛔ **The second one was not only a reading error.** The same byte order was used when writing a goal: a commanded 604 would have reached the servo as 23554 — a position it cannot reach, and one it would have driven toward. **It was fixed before any goal was written.** That is the whole of why the first move happened when it did.

## What happened afterwards

⚠️ **The app restarted during the read-back, before the console could hold the whole move.** The cause is not established, and the two candidates are not equally likely:

- **the read-back opened the serial port**, and on this chip the host's control lines can pulse the reset pin — this is the ordinary explanation, and it happened at the read, not during the motion;
- **a supply dip**, because both servos held torque for about forty seconds on battery — ⚠️ **this one would have happened mid-move, and the console shows the move continuing to its last written step, so it fits worse.**

⛔ **This file does not choose between them.** The motion had already happened when the console was reopened; the reboot does not retract the observation, and it does not explain it either.

## A second command, later the same day

**The author was watching the unit.** In their words: 「ジジっと、2回少し動いた」 — *it moved a little, twice, with a jiji sound.*

One line was typed:

```
bench move 0
```

⛔ **The program's lines from this command are not in this file.** The capture kept the last thirty lines of a stream that the heartbeat fills every three seconds, so what survived was thirty `alive` lines and nothing else. **This file does not reconstruct them.** What it has is one number taken afterwards, and one pair of eyes.

**The number**, read by `bench pos` through the next boot: yaw raw **468**, 2.5° from the zero of 460; pitch raw **894**, 85.6°, unchanged.

| | first command | second command |
|---|---|---|
| typed | `bench move 5` | `bench move 0` |
| last recorded before it | 604 (45.0°) | 484 (7.5°) — the previous read-back |
| read back after it | 484 (7.5°) | 468 (2.5°) |
| what the author saw | the head turned toward front | the head moved a little, twice |

⚠️ **What 468 says, and what it does not.** The target was the zero itself, 460, and `MoveAxis` steps to it exactly, three counts a second, so the last goal written was 460. **The shaft was found eight counts away from it** — 2.5°, of the same order as the six-count sag the first read-back showed, and this time after a move nobody interrupted. ⚠️ **How far this command travelled is not known**: the head was limp between the two commands and no read was taken, so 484 is the last *recorded* value and not necessarily the one this command started from. That the shaft ended nearer the zero than 484 is a measurement; **that the head moved is the author's eye again.**

⚠️ **The lost lines were the bench tool's fault, not the firmware's.** The tool ended a read after two seconds of silence and this firmware prints `alive` every three — so it never saw silence, never stopped early, and held the port until its own deadline. **The tool lives outside this repository, and no check covers it.**

## The servo's time field — and it does not do what its name says

**What was asked.** The author, watching the neck, asked whether the stock firmware's flexible movement had been lost. It had not been lost; it was never carried over — `bench move` rewrites the goal three counts closer once a second and stops between steps, and this engine's trajectory has never run on this machine.

**What was measured.** A bench command was added and flashed the same day: `bench timed <yaw_deg> <time> [speed]` writes **one** goal carrying a time field and a speed field, then reads the shaft every 200 ms for up to 70 s.

| trial | written | what the shaft did |
|---|---|---|
| 1 | `bench timed 5 5000 0` | 5 counts in about 400 ms, then still for the remaining 70 s, **6 counts short** of the goal |
| 2 | `bench timed 15 500 100` | 32 counts (10°) in about 300–400 ms at about 127 counts/s, then still, **again exactly 6 counts short** |

⛔ **The time field did not govern the duration in either trial; the speed field did.** ⚠️ **The six-count shortfall was the same for a 16-count and a 38-count move**, so it reads as a fixed offset rather than a proportion — **which is an observation, not yet a measurement**: nothing here separated an offset inside the servo from backlash or from the read-back itself.

⚠️ **The first trial was also too small to see, and the author said so** — in their words: 「動いていないよ」. It had moved 1.6° of a 3.4° command, because the angle given was absolute and the head already stood at 1.6°. **The second trial was visible**, and the author's word for it was 「動いた」.

⇒ **What this settles:** on this unit, smoothness cannot be taken from the servo's own time field. If the neck is to move without steps, **the host must write interpolated goals** — which is what this repository's trajectory family is for, and which has still never run here.

## What this record does not establish

- **It does not establish that the engine works.** No `Motion Intent` was read, no trajectory was computed, no gate was passed. **The engine has still never run on any machine.**
- **It does not establish that the machine is safe.** One slow 40° yaw move, with both goals set to the present positions before torque came on and torque released at the end, is one move — not a test of failure modes.
- **It does not establish that the Pet is there.** ⛔ **That is the goal, and it cannot be verified in this workshop.** What arrived was a value, not a presence.
- **It does not name an angle for any gesture.** The refusal in `command_frame.cpp` is unchanged: `perk` is still not a number.

## The numbers, in one place

| what | value | where it comes from |
|---|---|---|
| machine | M5Stack Stack-chan, ESP32-S3 | MAC `80:45:6B:54:6D:B0`, read by `esptool` |
| image | `build/stackchan-vessel.bin`, 272,976 bytes | written at `0x510000`, hash verified after writing |
| zeros in use | yaw 460, pitch 620 | this unit's NVS, namespace `servo` |
| before | yaw 604 (45.0°), pitch 894 (85.6°) | read from the servos |
| commanded | yaw 476 raw | `bench move 5`, clamped to ±20° |
| last command written | yaw 478 (5.6°) | two counts short of the target |
| read back after the motion | yaw 484 (7.5°) | the next boot's own read, torque already released |
| pitch | unchanged at 894 | held, never commanded to move |
| duration | 42 steps at one per second; interrupted after about 40 s | the console's own lines |
| second command, read back after it | yaw 468 (2.5°), pitch 894 unchanged | `bench pos` through the next boot; that command's own lines were lost |
