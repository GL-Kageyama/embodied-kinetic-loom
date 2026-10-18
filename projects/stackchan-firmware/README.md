<!-- i18n-version: 2.4.0 | canonical: projects/stackchan-firmware/README.md | translated: 2026-10-18 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/stackchan-firmware/ — the device end of the wire

✅ **Built, flashed, and the head turned — 2026-10-18.** This directory produced `build/stackchan-vessel.bin`, wrote it at `0x510000`, verified it by hash, and ran it: the app printed `ready.`, both servos answered a ping, and `bench move 5` turned the head. ✅ **And later the same day, for the first time, a goal that came from a host:** 678 `pose` lines at 20 ms, none refused, and the author watching said 「動いた」. ✅ **And after that, the twelve LEDs lit and followed a word** — `warm` became orange, `alert` became yellow, `breathe` became a breath — **including when the word came from the installed daemon, through the transport, over the console.** ✅ **And after that, the five gestures were measured, named and played from frames** — a gesture no longer needs to invent an angle, and a frame that carries one moves the head. ⚠️ **The five words were renamed the same day, by the author's judgement**: `look_up`, `look_side`, `nod`, `rest`, `recoil`. **The records are `records/2026-10-18-first-arrival.md`, `records/2026-10-18-the-lights.md` and `records/2026-10-18-the-gestures.md`, and the observation is the spine of all three.**

**What is here:** a parser for one command frame, and a gesture table — five postures measured on this unit with the author's eye. **What is not here:** interpolation. ⛔ **A gesture is one move at one speed and a stop; the author's word for it is 「動きが硬い」.** Smoothness is the engine's job, and **the engine has never run on this machine.**

⚠️ **The table is not a guess.** Every number in it came from placing a posture with `bench set` and asking the author whether the head was showing that word (`records/2026-10-18-the-gestures.md`). **A guessed angle is indistinguishable from a measured one in the source**, which is why none was written before the measurement — and why the two postures that sit on the pitch floor say so.

## What the frame carries

**One line of JSON per command**, and a command arrives when what the machine should show changes — a phase, a face, a light, or a chosen gesture. This is not a stream. ⚠️ **The neck moves only at a transition**: a gesture is chosen there and nowhere else. The contract is `schemas/stackchan-command.schema.json`, and both ends read it.

| field | values | meaning |
|---|---|---|
| `face` | the Pet's five faces, or `null` | show this expression; `null` = do not change |
| `light` | `off` / `dim` / `breathe` / `warm` / `alert` / `error` | always present, never `null` |
| `gesture` | `look_up` / `nod` / `look_side` / `rest` / `recoil`, or `null` | move the neck; `null` = do not move |

⛔ **There is no `sound` field.** The speaker is a channel that does not exist yet.

## What the vendor's source records

✅ **Since 2026-10-18 these are in a record** — `m5stack/StackChan`, branch `firmware-dev`, MIT: the firmware that ships on the unit in hand. ⚠️ **They are the vendor's numbers, read out of code, not measurements taken here.** This repository reads them; it does not own them.

| what | the vendor's record |
|---|---|
| servo bus | UART1, 1,000,000 baud, TX GPIO 6, RX GPIO 7; Feetech SCSCL |
| scale | `raw = zero + angle × 16 / 5 / 10`, `angle` in 0.1° ⇒ **one count is 0.3125°**; inverse `(raw − zero) × 5 × 10 / 16` |
| yaw (ID 1) | zero 460 default, limits ±1280 tenths = **±128.0°**, raw 0–1000 |
| pitch (ID 2) | zero 620 default, limits 30–870 tenths = **+3.0° to +87.0°**, raw 0–1000, stall protection on |
| the zeros | NVS, namespace `servo`, keys `zero_pos_1` / `zero_pos_2` — ⚠️ **this is where this unit's measured zeros live** |
| LEDs | 12, behind a PY32 IO expander at I²C `0x6F` (SDA GPIO 12, SCL GPIO 11); the same expander switches **servo power** on pin 0 |

✅ **Since 2026-10-18 the angle exists** — five postures, measured on this unit (`records/2026-10-18-the-gestures.md`). The table is `main/main.cpp`, beside the comment that says where each number came from.

| gesture | yaw | pitch | what it does |
|---|---|---|---|
| `look_up` | +8.0° | 50.0° | the face goes up |
| `look_side` | +35.0° | 50.0° | the face goes to one side |
| `rest` | 0.0° | 3.0° | the face comes down and stays |
| `nod` | +8.0° | 50.0° → 3.0° → 50.0° | down and back |
| `recoil` | −8.0° | 70.0° | the face pulls back and up |

⛔ **`rest` and `nod`'s down point sit on the machine's pitch floor** — 3.0°, the vendor's minimum. A word wanting to go lower cannot here.

⛔ **These are postures, not trajectories.** Each gesture is one move at the servo's own speed field, followed by a stop. **Nothing interpolates.**

## What this source deliberately does not decide

- **the gesture table** — ✅ **measured 2026-10-18, and no longer on this list**: the five postures are in `main/main.cpp`, judged one at a time by the author's eye. ⛔ **What is still not decided is how a gesture should move** — the table names where it goes, not how it gets there;
- **the LED colours** — ✅ **the order is RGB565 behind the expander, and since 2026-10-18 every light has a colour**; ⛔ **each one is a choice in `main/leds.cpp`, and no colour is a measurement of anything the Pet should look like**;
- **the display renderer** — the face is a meaning here, not pixels;
- **the transport** — ✅ **decided on 2026-10-18, and it is the console**: the daemon opens the USB serial path, writes one line per frame and closes it. ⛔ **Nothing is held open, so `bench` and `idf.py` still own the port between frames.** ⚠️ **The path is not stable across a replug** — see [The lights](#the-lights--2026-10-18).

## The first flash — 2026-10-18

✅ **The restore was written, read back, and watched booting.** On 2026-10-18, on the unit in hand: the stock image was written and read back bit-for-bit, **it booted — its own USB log showed the launcher opening and every app being created** — then the current snapshot was written back, read back the same way, and **that booted too.** `docs/first-contact-stackchan.md` holds the files, their hashes, the measured diff, and the exact boot observations.

✅ **Then the image this directory produces was built and written.** `build/stackchan-vessel.bin`, 272,976 bytes, at `0x510000`, hash verified; the app reached `ready.` and the bench turned the head. ⚠️ **A later build the same day, 273,808 bytes, added `bench timed` and was written the same way** — the size here is that build's, not a constant. ⛔ **What that did not close is the gate at the top of this page:** at that point every gesture in a frame was still refused, because no angle had been measured. **The move was a bench command — no `Motion Intent`, no trajectory, no gate** (`records/2026-10-18-first-arrival.md`). ✅ **The gesture gate closed later the same day**, when the five postures were measured (`records/2026-10-18-the-gestures.md`).

⚠️ **One thing rings on this directory now, and it is narrow.** ✅ **Since 2026-10-18 `tests/test_stackchan_frame_parser.py` compiles `command_frame.cpp` with `clang++` or `g++` and runs it** — fourteen claims about which lines it accepts and which it refuses. ⛔ **It does not build the firmware**: `main.cpp`, `leds.cpp` and `servo.cpp` are never compiled here, and `idf.py build` was run by hand and no check repeats it. `tests/test_stackchan_wire.py` still reads these literals and refuses the day they disagree with the schema — **a copy checked against a copy**. ⚠️ **The parser test exists because that gap had a defect in it**: on 2026-10-18 the parser refused every well-formed frame by failing to step over the closing brace, and the literal comparison passed it.

## What the servo's time field answered — 2026-10-18

✅ **`bench timed <yaw_deg> <time> [speed]` was added to the bench and flashed the same day.** It writes **one** goal carrying a time field and a speed field — unlike `bench move`, which rewrites the goal once a second — and then reads the yaw shaft every 200 ms for up to 70 s.

⛔ **On this unit the time field did not govern the duration; the speed field did.** Two trials: `time=5000, speed=0` moved 5 counts and stopped; `time=500, speed=100` moved 32 counts (10°) in about 0.3–0.4 s at about 127 counts/s. **Both stopped exactly 6 counts short of the goal** — a fixed offset by the look of it, and not yet separated from backlash or from the read-back itself.

⇒ **What this means for the engine, in one line: smoothness cannot be delegated to the servo here.** A neck without steps needs the host to write interpolated goals — which is what `engine/trajectory/` exists for, and what has never run on this machine. ⚠️ **The numbers live in `records/2026-10-18-first-arrival.md`, where the observations they came with are the spine.**

## The pose line, and the board reads it — 2026-10-18

✅ **The board's end of `pose <yaw_tenths> <pitch_tenths>*<CC>` is in `main/main.cpp`.** It is dispatched on the first word, exactly as the host codec assumes, and it does five things:

| what | how |
|---|---|
| length | over **64** bytes → `pose: refused (too-long)` |
| checksum | the two hex digits after the last `*` must equal the sum of everything before it, `& 0xFF` |
| fields | exactly one space, and both parse by the same spelling rules as the Python decoder — `05`, `-0`, `+5` are all refused |
| clamping | against **this machine's** limits (`board::kYawAngleLimitTenths`, `kPitchAngleMin/MaxTenths`), never the protocol's |
| the first line | both goals are set to the present positions, torque on, 200 ms — so the first pose is a move and not a jump |

⛔ **A refusal is printed once per code per stream.** A print per refused pose at 50 Hz would bury the one line that matters: `pose: stream lost after 500 ms — torque released`.

⚠️ **The watchdog runs in the main loop, not the console task**, because the console task blocks in `read()`. That put two tasks on one UART, so `servo.cpp` now holds a mutex around the bus — ⛔ **an interleaved packet is not a refused command, it is a different command, or silence.**

✅ **Measured the same day, six round trips of ±5°:** 678 poses, **0 refused, 0 clamped**, and the watchdog fired once per round trip. **Pitch was commanded as `857` tenths and read 894 before and after** — not the printed 85.6°, which converts back to 893. ⚠️ **Every round trip ended about six counts below its centre**, the same shortfall as the timed bench.

⛔ **What this does not mean: the engine ran.** The interpolation was in a host tool outside this repository (`~/stackchan/pose_stream.py`), not in `engine/trajectory/`. **No `Motion Intent` was read, and the transport is still not chosen.** **The record is `records/2026-10-18-first-arrival.md`.**

⚠️ **`bench` is refused while a stream is running** (`bench: refused — a pose stream is running; wait for 500 ms of silence`), because `bench` blocks the console for seconds and a pose that arrives late is not a pose.

## The lights — 2026-10-18

✅ **The twelve LEDs work, and a frame from the daemon reaches them.** ⛔ **They did not work earlier the same day** — a frame the board accepted produced 「光っていない」, while the expander's registers held exactly the right colour. **The record is `records/2026-10-18-the-lights.md`, and the observation is its spine.**

| light | colour (RGB565 source) | chosen in |
|---|---|---|
| `off` | `{0, 0, 0}` | `main/leds.cpp` |
| `dim` | `{24, 24, 40}` | `main/leds.cpp` |
| `breathe` | `{40, 48, 72}`, a triangle between 20 % and 100 % over 3 s | `main/leds.cpp` |
| `warm` | `{112, 64, 24}` | `main/leds.cpp` |
| `alert` | `{160, 104, 0}` | `main/leds.cpp` |
| `error` | `{144, 0, 0}` | `main/leds.cpp` |

⛔ **Not one of those is a measurement.** The twelve are written behind a PY32 IO expander at I²C `0x6F`: `LED_CFG` at `0x24` carries the count in bits 0–5 and a refresh in bit 6, and the pixels are RGB565 little-endian from `0x30`.

✅ **`bench leds` was added to make two questions out of one.** It reads the expander back — version, `LED_CFG`, the six registers behind the data pin, the first four pixels — then writes full red to all twelve and reads pixel 0 again. **"The registers took the values" and "a pixel is lit" are asked separately, and the answer is printed either way.**

⚠️ **What changed the outcome is one thing, and it is a hypothesis:** the expander was power-cycled. The board had been unplugged to recover from a hang, and the twelve lit after it went back in, with no new code. ⛔ **Nothing here separated the power cycle from the plug-in, the re-enumeration, or the reflash that had just preceded it.**

### Two hangs on this board

⛔ **A bench command that wrote `LED_CFG` bit 7 — a bit no vendor driver writes — stopped the console, the heartbeat and the USB-Serial-JTAG ROM, with the USB device still enumerated.** Only unplugging recovered it; the command was deleted, and `main/leds.cpp` keeps the reason: **an untouched register bit is not "unused", it is "unknown".**

⛔ **The second hang came from a reader, not from the wire.** A `pyserial` open reset the board (`rst:0x15 (USB_UART_CHIP_RESET)`), the reader lost the stream mid-boot, and the ROM stopped answering. **The daemon's own path — `os.open`, `os.write`, `os.close`, one frame at a time — was then run alone and did not reset anything**; the console was read with `os.open` and raw `termios`. ⚠️ **A reader that asserts DTR and RTS is rebooting this machine.**

### One actor instead of two

⚠️ **This unit shipped with a vendor app in `ota_0` that could replace the app in `ota_1`.** Once, booting it by erasing `otadata` made it connect to a network and start an OTA into this repository's slot. ⇒ **The vendor image was read off the board (5,177,344 bytes, SHA-256 `97b176…cf64ab5b`, kept outside this repository at `~/stackchan/vendor-image/`), and then `ota_0` was erased** (`erase-region 0x20000 0x4f0000`, 4.9 s). ⛔ **The file is the only copy; no check covers it.**

⚠️ **And the console's path is not an identity.** It read `/dev/cu.usbmodem1101` before the hang and `/dev/cu.usbmodem101` after one replug — **sixteen minutes apart, one board.** The installed plist names the second; the next replug may name a third, and a frame written to a missing path is logged as `sent: false`, not raised.
