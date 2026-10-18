<!-- i18n-version: 2.11.0 | canonical: projects/stackchan-firmware/README.md | translated: 2026-10-19 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/stackchan-firmware/ — the device end of the wire

✅ **Built, flashed, and the head turned — 2026-10-18.** This directory produced `build/stackchan-vessel.bin`, wrote it at `0x510000`, verified it by hash, and ran it: the app printed `ready.`, both servos answered a ping, and `bench move 5` turned the head. ✅ **And later the same day, for the first time, a goal that came from a host:** 678 `pose` lines at 20 ms, none refused, and the author watching said 「動いた」. ✅ **And after that, the twelve LEDs lit and followed a word** — `warm` became orange, `alert` became yellow, `breathe` became a breath — **including when the word came from the installed daemon, through the transport, over the console.** ✅ **And after that the screen drew the vendor's own face** — two eye discs with lids and a mouth bar, anti-aliased, from the `face` field of a frame. ✅ **And after that, the five gestures were measured, named and played from frames** — a gesture no longer needs to invent an angle, and a frame that carries one moves the head. ⚠️ **The five words were renamed the same day, by the author's judgement**: `look_up`, `look_side`, `nod`, `rest`, `recoil`. **The records are `records/2026-10-18-first-arrival.md`, `records/2026-10-18-the-lights.md` and `records/2026-10-18-the-gestures.md`, and the observation is the spine of all three.**

**What is here:** a parser for one command frame, and a gesture table — five postures measured on this unit with the author's eye. **What is not here:** interpolation. ⛔ **A gesture played from the table is one move at one speed and a stop; the author's word for it is 「動きが硬い」.** Smoothness is the engine's job, and ✅ **since 0.19.10 the engine has driven this machine**: `projects/stackchan/neck/` streamed `engine/trajectory` samples as 20 ms `pose` lines — seven segments, 822 applied, 0 refused, 0 clamped. ⛔ **And since 0.19.11 the pose stream writes what the stock firmware writes** — `WritePos(id, angle, 20, 0)` — because the old call (`time=0, speed=100`) was a 40°/s cap of our own, not the servo's ceiling. **Measured on this unit, one goal each way: 112 counts (35°) in under 200 ms with the stock's call, about 1.0 s with ours.** ✅ **The same seven segments at one-third the length then played: 228 poses, 410 applied on the board, 0 refused, 0 clamped — and the author's judgement is 「かなり良い。これでOKだと思う。」** ⚠️ **The record is `records/2026-10-18-the-neck.md`.**

⚠️ **The table is not a guess.** Every number in it came from placing a posture with `bench set` and asking the author whether the head was showing that word (`records/2026-10-18-the-gestures.md`). **A guessed angle is indistinguishable from a measured one in the source**, which is why none was written before the measurement — and why the two postures that sit on the pitch floor say so.

## What the frame carries

**One line of JSON per command**, and a command arrives when what the machine should show changes — a phase, a face, a light, a chosen gesture, or a word to say. This is not a stream. ⚠️ **The neck moves only at a transition**: a gesture is chosen there and nowhere else. The contract is `schemas/stackchan-command.schema.json`, and both ends read it.

| field | values | meaning |
|---|---|---|
| `face` | the Pet's five faces, or `null` | show this expression; `null` = do not change |
| `light` | `off` / `dim` / `breathe` / `warm` / `alert` / `error` | always present, never `null` |
| `gesture` | `look_up` / `nod` / `look_side` / `rest` / `recoil`, or `null` | move the neck; `null` = do not move |
| `sound` | `hello` / `pip` / `chime` / `fall`, or `null` | play this word; `null` = this frame is silent |

⚠️ **`sound` is the one field that is an event and not a state**: `null` does not mean *keep the last word*, it means *say nothing*. ⛔ **The board knows the four words and nothing about when they are right** — the host decides that, and the mapping is `projects/stackchan/behaviors.py`.

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
- **the display renderer** — ✅ **decided on 2026-10-18: this repository's own rasterizer, drawing the vendor's default skin** (see [The face](#the-face--2026-10-18)). ⛔ **The eyelid's animation, the blink, the breath and the mouth's speech motion are not drawn** — the six emotion pairs are, as stills;
- **the transport** — ✅ **decided on 2026-10-18, and it is the console**: the daemon opens the USB serial path, writes one line per frame and closes it. ⛔ **Nothing is held open, so `bench` and `idf.py` still own the port between frames.** ⚠️ **The path is not stable across a replug** — see [The lights](#the-lights--2026-10-18).

## The first flash — 2026-10-18

✅ **The restore was written, read back, and watched booting.** On 2026-10-18, on the unit in hand: the stock image was written and read back bit-for-bit, **it booted — its own USB log showed the launcher opening and every app being created** — then the current snapshot was written back, read back the same way, and **that booted too.** `docs/first-contact-stackchan.md` holds the files, their hashes, the measured diff, and the exact boot observations.

✅ **Then the image this directory produces was built and written.** `build/stackchan-vessel.bin`, 272,976 bytes, at `0x510000`, hash verified; the app reached `ready.` and the bench turned the head. ⚠️ **A later build the same day, 273,808 bytes, added `bench timed` and was written the same way** — the size here is that build's, not a constant. ⛔ **What that did not close is the gate at the top of this page:** at that point every gesture in a frame was still refused, because no angle had been measured. **The move was a bench command — no `Motion Intent`, no trajectory, no gate** (`records/2026-10-18-first-arrival.md`). ✅ **The gesture gate closed later the same day**, when the five postures were measured (`records/2026-10-18-the-gestures.md`).

⚠️ **One thing rings on this directory now, and it is narrow.** ✅ **Since 2026-10-18 `tests/test_stackchan_frame_parser.py` compiles `command_frame.cpp` with `clang++` or `g++` and runs it** — fourteen claims about which lines it accepts and which it refuses. ⛔ **It does not build the firmware**: `main.cpp`, `leds.cpp`, `servo.cpp` and `display.cpp` are never compiled here, and `idf.py build` was run by hand and no check repeats it. ✅ **Since 0.19.12 a second file is compiled and run** — `tests/test_stackchan_face.py` builds `face_bitmap.cpp` and asks the pixels — ⛔ **and that is the layer the day's tear was *not* in.** `tests/test_stackchan_wire.py` still reads these literals and refuses the day they disagree with the schema — **a copy checked against a copy**. ⚠️ **The parser test exists because that gap had a defect in it**: on 2026-10-18 the parser refused every well-formed frame by failing to step over the closing brace, and the literal comparison passed it.

## What the servo's time field answered — 2026-10-18

✅ **`bench timed <yaw_deg> <time> [speed]` was added to the bench and flashed the same day.** It writes **one** goal carrying a time field and a speed field — unlike `bench move`, which rewrites the goal once a second — and then reads the yaw shaft every 200 ms for up to 70 s.

⚠️ **On this unit, when `time` is zero the speed field governs; when `time` is not zero, the time field does** — two trials on 2026-10-18 changed only one field each: `time=20, speed=0` moved 112 counts (35°) in under 200 ms, and `time=0, speed=100` moved the same 112 counts in about 1.0 s. ⛔ **An earlier pair changed both fields at once** (`time=5000, speed=0`: 5 counts and stopped; `time=500, speed=100`: 32 counts in about 0.3–0.4 s), **so it cannot separate them — that reading is superseded, not confirmed.** **Every trial stopped 6 to 8 counts short of the goal** — a fixed offset by the look of it, and not yet separated from backlash or from the read-back itself.

⇒ **What this means for the engine, in one line: smoothness cannot be delegated to the servo here.** A neck without steps needs the host to write interpolated goals — which is what `engine/trajectory/` exists for, and which at that point had never run on this machine. ✅ **It has since 0.19.10; and since 0.19.11 the servo's own ceiling, about 175°/s, sizes a followable motion — not the 127 counts/s this section measured** (see above). ⚠️ **The numbers live in `records/2026-10-18-first-arrival.md`, where the observations they came with are the spine; the neck's own record is `records/2026-10-18-the-neck.md`.**

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

## The face — 2026-10-18

✅ **The screen draws the vendor's default skin, and the author's verdict is 「OK」「綺麗に写っている」.** The numbers are the vendor's, lifted from `skins/default/eyes.cpp` and `mouth.cpp`; the rasterizer is this repository's, because this firmware carries no LVGL.

| what | where it comes from | what it is here |
|---|---|---|
| the panel | ILI9342C at SPI3 — MOSI GPIO 37, SCK GPIO 36, CS GPIO 3, DC GPIO 35, mode 2, 40 MHz | `main/display.cpp`, driven through the core `esp_lcd` panel-IO API, so no vendored tree is added |
| its rails | AW9523 at I²C `0x58` (reset, P1.7) and AXP2101 at I²C `0x34` (DLDO1 backlight) | `main/display.cpp`, the vendor's own boot sequence; **no value here was measured on this unit** |
| the panel's init | `esp_lcd_ili9341` v1.2.0's sequence, `MADCTL 0x08` (BGR), no mirror, no swap | `main/display.cpp` — ⚠️ **the driver's source was not on this host; the copy read was `esp-bsp` master, and the vendor pins `==1.2.0`** |
| the eyes | `_eye_pos = (-70, -16)`, `setSize(0)` = 20 px, six emotion pairs | `main/face_bitmap.cpp` — rows 94–113 |
| the mouth | `_mouth_pos = (0, 26)`, `setWeight(0)` = a 90 × 6 bar, radius 0 | `main/face_bitmap.cpp` — rows 143–148 |
| the smoothness | ⛔ **LVGL anti-aliases its circles; a 1-bit renderer reproduced the shape and not the edge** | an 8-bit coverage buffer, 8 × 8 supersampled; 76,800 bytes of grey, sent as RGB565 **byte-swapped** |

⛔ **The defect that had been reported four times was not in the drawing and not in the panel: it was between them.** `esp_lcd_panel_io_tx_color()` queues a DMA transfer and returns, and `Push()` refilled the eight-row chunk buffer immediately — so the hardware read rows that had already been overwritten. **On the glass every shape had a thinner copy of itself below it, further below the lower the shape was**, which is why one fault was read as 「ギザギザ」, then as 「ずれている」, then as 「目の描画が、二行だけ、下に」, then as 「画面全体が下にずれる」. ✅ **The fix is `on_color_trans_done` and a semaphore taken after every chunk** — about 30 ms a frame, and a face changes on an event.

⚠️ **A `-2` row shift was written into `face_bitmap.cpp` on the strength of the fourth report and then removed.** ⛔ **The nine tests in `tests/test_stackchan_face.py` did not catch it, because they were moved with it.** The file now draws the vendor's rows and carries a comment saying why no offset belongs there.

**The record is `records/2026-10-18-the-face.md`, and the observation is its spine.**

## The voice — 2026-10-18

✅ **The board plays the fourth field, and the author heard all four words.** The amplifier is an **AW88298** at I²C `0x36`, on the bus the display already owns; its reset is **P0.2 on the AW9523**, so `display::pulse_amplifier_reset()` holds the pulse and `sound` calls back into it — **one bus, one owner**. The audio path is `I2S_NUM_0` as master, **24,000 Hz, 16-bit stereo**, MCLK 256 × fs.

| what | the vendor's number | what this repository changed |
|---|---|---|
| the amplifier's table | eight registers written in order, `0x00` `0x55AA` first and 50 ms of silence after it | ⛔ **nothing — not one value was measured on this unit** |
| the sample-rate code | `0x06` = `0x3CC8`, the code for 48,000 Hz | **`0x3CC5`** — rate code 5, put there by hand so that the code and the 24,000 Hz stream agree |
| the volume | `0x0C` = `0x3064`, the vendor's −18 dB at boot | **`0x0C` = `0x1864`, −10 dB at boot** — the ear's judgement of 2026-10-19, not the vendor's default; `bench volume <0..100>` rewrites the high byte only |
| the pins | MCLK GPIO 0, BCLK 34, WS 33, DOUT 13 (DIN 14 unused) | nothing |

⛔ **A rate code and a sample rate that disagree is a silent, wrong-pitch channel, and nothing on this board reports it** — which is why the one number changed is named here and in the record rather than left in the source.

⚠️ **The four tones are choices, not measurements** — the same standing as the twelve LEDs' colours. `hello` rises, `pip` is one bright point, `chime` rises and rings longer, `fall` drops. **Nothing has judged them but one pair of ears**, and that judgement is only *it was audible* (`records/2026-10-18-the-voice.md`). ✅ **On 2026-10-19 the same ear judged the level**: the four were 「少し小さい」 at the vendor's boot volume, and **`fall` — the only word ending on 440 Hz — was smaller than the other three**. ⇒ **The boot volume is −10 dB and `fall` alone is written at 0.34** (the other three at 0.22); the author heard it again and said 「OK」. ⛔ **That is a comparison of loudness, not of tone** — the shapes themselves still rest on nothing but a choice.

⚠️ **`i2s_channel_write` returns when the DMA buffers have taken the samples, not when the note has finished** — so the board's `playing` → `done` lines are not note lengths, and must not be read as any.

⛔ **`main/sound.cpp` is compiled by no check.** `idf.py build` is run by hand; a test builds `command_frame.cpp` and `face_bitmap.cpp`, and nothing here builds the I²S channel or the amplifier's bring-up.

## The landing — 2026-10-19

⛔ **This section is not a record.** Every file in `records/` has a person's observation as its spine; this one has the board's own read-back and no eye. **It answers where the head stopped, not whether anything moved** — and it is here, in the document that holds this machine's numbers, rather than in the records vessel.

`records/2026-10-18-the-neck.md` closed with a sentence it could not resolve: *every segment landed six to eight counts short of its goal — 452 against 460, 517 against 524, 404 against 396 — the same fixed offset every trial shows, and not yet separated from backlash.* **The construction memo asked for it to be closed once, after stage 3, so that the record does not stay wrong.** Stage 3 closed on 2026-10-19; this is that once.

**What was counted.** One unit, both axes: nine yaw landings and four pitch landings under `bench set` at speed 80, and one posture driven through the real pose line — thirty lines at 40 ms, `time=20 speed=0`, the call the daemon streams with. **What was not counted:** any other unit, the servo's deadband register, the load, the temperature, and the cause.

**Yaw**, both goals at pitch 50.0°, `bench set <yaw> 50.0 80`. The travel column is the direction the head moved to reach the goal, read from the position before the write.

| goal raw | held raw | held − goal | travel |
|---|---|---|---|
| 396 | 404 | +8 | leftward |
| 435 | 442 | +7 | leftward |
| 460 | 467 | +7 | leftward |
| 485 | 478 | −7 | rightward |
| 485 | 497 | +12 | leftward |
| 524 | 516 | −8 | rightward |
| 572 | 566 | −6 | rightward |
| 524 | 534 | +10 | leftward |
| 485 | 491 | +6 | leftward |

**Pitch**, yaw held at 8.0°.

| goal raw | held raw | held − goal | travel |
|---|---|---|---|
| 629 | 630 | +1 | downward |
| 716 | 714 | −2 | upward |
| 844 | 841 | −3 | upward |
| 780 | 781 | +1 | downward |

## The rail's switch — 2026-10-19

⛔ **Until this day `bench power on` printed ON whatever the expander did with the write.** The command had never asked whether the write landed — **the print was the claim, not the answer.** ⇒ **It now checks the return of `leds::servo_power()`**, prints `the expander took the write` or `THE EXPANDER DID NOT TAKE THE WRITE`, and then calls `servo_power_probe()`.

**What the probe reads**, pin 0, the servo rail's enable line:

| register | value | meaning |
|---|---|---|
| `M_L` `0x03` | `0x01` | pin 0 is an output |
| `O_L` `0x05` | `0x01` | the output is high |
| `I_L` `0x07` | `0x00` | the input register reads the pin low |
| `PU_L` `0x09` | `0x01` | pull-up on |
| `PD_L` `0x0B` | `0x00` | pull-down off |
| `DRV_L` `0x13` | `0xFE` | push-pull |

⚠️ **The write landed. The bit that would say the line reads high did not.** ⛔ **What `I_L = 0x00` means is not settled here**: an expander's input register may report a pad only while the pin is an input, so it is consistent both with a line held low and with a register that is not reading the output. ⇒ **This probe closes "the expander took the write". It does not close "the rail is powered".**

⚠️ **A push-pull trial was written and removed the same day.** Writing `DRV_L` moved it from `0xFF` to `0xFE`, the input bit stayed `0x00`, and `bench scan` stayed at **0 id(s)** — **the trial changed one register and nothing the bus could hear.**

⛔ **The expander is not reset by the ESP.** `DRV_L` stayed `0xFE` across a flash and a hard reset: **the PY32's registers outlive the ESP's boot**, and the vendor's driver writes them once at start-up because its boot is the board's first. ⇒ **A boot that inherits the previous run's registers is not a boot with a known state.** `leds::begin()` now writes direction, pull-up, push-pull and level on every boot, before the rail is switched on.

**And the bus is silent earlier than the host is.** The first boot log captured on 2026-10-19 reads `servo: ping yaw=0/3 pitch=0/3` and `servo: a position did not read — nothing will move`, with this unit's NVS centres at **yaw 460, pitch 620**. ⇒ **No line the host writes is the cause of the silence — it is there at boot.**

⚠️ **Two more answers came the same day, and neither closes the rail.** `bench pmu` reads the AXP2101: `0x00=0x38`, `0x01=0x32`, **`vbat=4624 mV`**, direction 1 (charging), charge state 2 — **a battery is present and charging.** ⛔ **That is the PMIC's register, not the rail's voltage.** `bench level` reads pin 0's pad twice: **as an input with a pull-up it reads LOW** — something external holds the line down, which is what an enable line whose default is off normally looks like — and **as an output driving high it still reads LOW**, ⛔ **which is either a register that does not mirror an output or a pad that is heavily loaded; the two are not separated here.** ⇒ **The supply exists at the battery; the power switch, the VM path and the rail's actual volts are still unmeasured** — the switch is the next thing a person can test, and a meter closes the rest.

### The switch was the rail's own power — 2026-10-19

⛔ **The remaining questions were physical, and the first of them was answered by cutting the power.** `bench power off`, three seconds, `bench power on`, then `bench scan`: **2 id(s) answered.** ⇒ **The rail, the switch, the VM path, the expander's pin and the wiring were never what was wrong.** (The author had already closed the power-switch question from the outside: USB unplugged, the screen stayed on — **the unit runs from its battery.**)

✅ **`bench state <id>` was added the same day** — one read of registers 56–63, which the SCSCL table puts at position, speed, load, voltage and temperature. At the moment the bus came back:

| id | raw | volts | °C | load | status |
|---|---|---|---|---|---|
| 1 | 469 | **5.1 V** | 32 | 0 | `0x00` |
| 2 | 776 | **5.1 V** | 31 | 0 | `0x00` |

⚠️ **Those volts are the servo's own reading, not a meter's** — the rail, as the servo sees it. ⛔ **They are not a measurement of current or of the load path**, and a servo that is dark says nothing.

⛔ **So the silence is a state the servos hold.** It survives a reset of the ESP32 — a DTR/RTS pulse that rebooted the board left the bus silent — and only cutting the servos' power clears it. A bounded `bench move 0 60` then turned the head (yaw 474→460, pitch 767→812), and **the bus went silent again after that move**; another rail cycle returned it.

✅ **Since 0.19.31 `app_main` throws the rail switch itself**, before the bus comes up: `servo_power(false)`, 300 ms, `servo_power(true)`, 300 ms, then `scs::begin()`. ⚠️ **No torque is on that early, so nothing can move because of it** — but a head that was being held when the chip reset will droop for those 300 ms.

⚠️ **`bench raw <id>` was added the same day**, because `read_position` calls a non-zero status byte "no answer" — **a servo that refuses and a servo that is absent were the same word.** It prints every byte, names the status by bit, and refuses nothing.

⛔ **What is still not answered**: what puts the servos into that state. It followed a bounded move once and was absent for many minutes at other times, so the trigger is not yet named — **and a boot that cycles the rail is a recovery, not a diagnosis.**

**Through the stream's own call.** Thirty `pose 350 500*<checksum>` lines at 40 ms, which the board applied with `time=20 speed=0` — the call the daemon uses. Goal raw yaw 572, held 565: **−7, leftward** — the same landing as `bench set` at speed 80. Pitch goal 780, held 781: +1.

⚠️ **The offset is not a constant and not a scale error: it is short in the direction of travel.** Every yaw landing moving left sits above its goal; every landing moving right sits below it. The pitch axis does the same, smaller.

⚠️ **The size differs by axis.** Yaw: 6–8 counts on eight of the nine landings, with two readings of 10 and 12. Pitch: 1–3 counts. One count is 0.3125° by the vendor's scale, so the yaw error is about 1.9–3.8° and the pitch error about 0.3–0.9°. **A deadband register is per servo, but it is not the whole story here**: the axis that carries the head's weight loses more than the axis beside it.

⚠️ **The servo knows it is short.** The position read back is the servo's own present position, not a host estimate — so what stopped short is the servo itself, not a gear train the sensor cannot see. ⚠️ **The cause is not separated further**: the control deadband and friction under torque both fit these numbers, and this console can read position only — it cannot read the deadband register, and there is no gauge on this bench to separate lost motion from a servo that is not driving the last counts.

⚠️ **Speed is not the explanation.** The stream's own call — `time=20 speed=0`, thirty poses at 40 ms — landed seven counts short, exactly as the slow bench call did.

⚠️ **One reading of +12 did not stay at +12.** After `bench set 8.0`, the head was declared held at 497. When the same goal was written again, it moved to 491 and stayed there. ⛔ **Whether that was creep or the re-issued goal is not separated here** — the repeat from a different approach landed at 491 and did not move over the five seconds it was watched.

✅ **The sentence in the neck record is now answered as far as this bench can answer it**: the landing offset's size and sign are measured, on both axes, and the direction of travel is what decides the sign. ⛔ **The cause is narrowed, not named** — deadband against friction is still open, and it stays open honestly rather than being assigned.

⛔ **Nothing was compensated.** A constant bias would be wrong half the time, because the sign follows the travel direction; a directional bias would be a new machine-specific number written into the host or the firmware. **Whether to write one, and where, is a decision not taken here.**

⚠️ **What it means for the join**: the daemon plans each gesture from the last pose it wrote, and the head sits six to eight counts short of that pose. The next plan's first sample is near the same place, so the discrepancy is bounded by the offset rather than accumulating across gestures — **but the jump between two gestures has not been measured**, and ⚠️ **the daemon asks the board for its position at each gesture since 0.19.23, but on this unit the servo bus answers nothing** (`bench scan` → 0 ids), so the query is answered without a pose.

⚠️ **The head was left at yaw 8.0°, pitch 50.0°** — raw yaw 491, pitch 781, torque on. **That is the posture the daemon believes the head is in**, so the next streamed gesture starts within the offset of where the daemon thinks it starts.
