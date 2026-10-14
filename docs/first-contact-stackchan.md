<!-- i18n-version: 1.0.0 | canonical: docs/first-contact-stackchan.md | translated: 2026-10-15 -->

**Language:** [English](first-contact-stackchan.md) | [日本語](first-contact-stackchan-ja.md) | [中文](first-contact-stackchan-zh.md)

# First Contact — machine 2, and this page begins at the other end

⚠️ **This page is a checklist, like `docs/first-contact.md`. It is not the safety argument** — what a motor may be commanded to do is `CLAUDE.md` § Safety, and this page does not repeat it. What is here is only what you would otherwise have to reconstruct from a record kept outside this repository, while standing in front of the unit.

⛔ **And it begins from the opposite end.** On machine 1's page, **not one item has been done** — there was no machine. **Here, most of them have been**: the unit in hand was put in front of a computer on 2026-10-15, and a second unit was driven on 2026-10-04 — **and they are not the same machine.**

⇒ **The warning here is the mirror of the other page's.** There, a tidy list could read as *answered* when nothing was. **Here, a tidy list can read as though the answers are about the unit in your hand — and most of them are not.** ⚠️ **Every fact below names the unit it was measured on.** A fact about one unit is not a fact about the other.

## (a) First — which Stack-chan

| | the unit that was driven | the unit in hand |
|---|---|---|
| measured | 2026-10-04 | 2026-10-15 |
| MAC | `68:ee:8f:d8:55:60` | `80:45:6B:54:6D:B0` |
| firmware | `shi3z` "Stack-chan Web Server" — Arduino, M5Unified, M5GFX | M5Stack stock **v1.5.1** (built 2026-07-31), ESP-IDF v5.5.4 |
| host → motor | ✅ **exists** — a text shell over `/dev/cu.usbmodem1101`: `head <pan> <tilt>` | ⛔ **none** |
| servo zero | not recorded | yaw (ID 1) **460**, pitch (ID 2) **620** — ⚠️ **written by the SETUP wizard on 2026-10-15** |
| SKU / UUID | — | `m5stack-stack-chan` / `05fc3176-7236-46ac-8f33-0dfb43d46d55` |

⛔ **The path does not exist on the unit in hand, and this is the finding that shaped the whole route.** It is not switched off — **it was never there:**

- **The UART console is off.** `help`, `?` and a bare newline get no response at all.
- **There is no local API.** All ports 1–65535 were scanned; **every one is closed.**
- **The device is not a server.** It connects **as a client** to `ws://47.113.125.164:12800`, so the MCP tools (`self.robot.set_head_angles` and the rest) are reachable only through the vendor's cloud, not over the LAN.
- The launcher's apps — Launcher / AI.AGENT / AVATAR / ESPNOW.REMOTE / APP.CENTER / EZDATA / DANCE / SETUP — offer no way out to a host.

⇒ **Writing our own firmware is not a preference here. It is the only way the unit in hand gets a path at all.**

⚠️ **And "it moved" on this unit is an observation, not a measurement.** On 2026-10-15 the SETUP wizard's own "Move To Home" moved the neck, and the owner watched it. That confirms **the servo, the SCS bus, the servo power and the torque control are all sound** — ⛔ **and it says nothing about this repository, because no value from this repository has ever reached this unit.**

## The one check that gates the firmware

**Can the stock image be written back?** Do this before anything else, because ⛔ **a flash is the one act on this page that nothing you send afterwards can undo.**

The safety net exists, and it is verified:

| | |
|---|---|
| file | `backup/stackchan-stock.bin` — ⚠️ **on the Desktop, not in this repository** |
| length | **16,777,216 bytes** |
| SHA256 | `012fe9d0b3c6075f78dd5426d5da7ed451c96c77ff685b1540c33a1f7594b466` |
| MD5 | `57de1620c3d1d4653927382abc7528d5` |
| read back | ✅ esptool `verify-flash` reported a **bit-for-bit** match with the device |
| restore | `esptool --port /dev/cu.usbmodemXXXX write-flash 0 backup/stackchan-stock.bin` |

eFuse, measured: **`SECURE_BOOT_EN` False**, **`SPI_BOOT_CRYPT_CNT` Disable**, **`DIS_DOWNLOAD_MODE` False**, **`DIS_USB_SERIAL_JTAG` False**, and `SOFT_DIS_JTAG` / `DIS_PAD_JTAG` not disabled. ⇒ **No lock is set, and a custom image can be flashed.**

⛔ **And here is the part the safety net does not cover.** ⚠️ **Nothing in the record shows a write.** The image was made by *reading* the flash, and confirmed by *reading* it again. ⇒ **The write path — the cable, the chip, the driver, the offset — has never been exercised on this host.** **A verified read proves the image is the device's. It does not prove the image can be put back.**

⇒ **Perform one restore before the first custom flash.** Write the stock image, let it boot, read the version back. **Then you know the net holds.** ⛔ **A safety net that has never been loaded is a file, not a net.**

⚠️ **And decide one thing before you press anything: the servo zeros live in NVS.** A full-image restore returns them to 455 / 603 — ⚠️ **it does not return the 460 / 620 the wizard wrote on 2026-10-15.** ⛔ **A partition-only restore returns something else again.** ⇒ **Know which of the three you are choosing, and write the choice down before you flash, not after.**

## ⛔ One trap that will cost you an hour, and it looks like a dead board

**The port name is not an identity, and it is not stable.**

- **A Fresco Logic USB hub** (the Realtek-Ethernet dock) **kills serial completely while still enumerating correctly.** `/dev/cu.usbmodem*` appears, the USB strings and the MAC read back correctly — and then: esptool fails with `No serial data received` in every reset mode, pyserial reads **0 bytes at every baud rate**, some rates raise `OSError: [Errno 83] Device error`, and **no boot log appears at all.**
  ⛔ **This is the shape that gets misdiagnosed as a dead board.** The fix is to plug **directly into the Mac** — and `Mac14,10` has no USB-A port, so it takes a USB-C ↔ USB-C **data** cable.
- **The name moves.** Removing the hub moved the unit from `/dev/cu.usbmodem1401` to `/dev/cu.usbmodem1101`. ⚠️ **And the 10/04 records disagree with each other about which of `/dev/cu.usbmodem101` and `1101` was the Stack-chan.**

⇒ **Identify the unit by its MAC, never by the port name.** ⚠️ **A path that appears is not a path that works** — and a device that enumerates is exactly the case where you will believe it.

## What machine 2 answers — and which unit answered

⚠️ **These are the questions machine 1's page still lists as unknown. Here they have answers — some about the 10/04 unit, some about the unit in hand.**

- **How many axes.** **Two** — yaw (servo ID 1) and pitch (ID 2). ⛔ **There is no roll.** The `Motion Intent`'s three names do not change; **this machine simply does not have one of them**, and the vocabulary's difference column is where that gets written down.
- **The unit of the numbers.** **Degrees in, servo counts out.** ⛔ **And the conversion between the two is in no record.** What is recorded is a **zero**, not a scale.
- **What the numbers do.** On the 10/04 unit: `head 45 90` → yaw 322, `head 90 90` → 454, `head 135 90` → 597, `head center` → 454; `head 90 45` → pitch 637, `head 90 90` → 762. ✅ **Three points on one axis, and the spacing is even** — ⚠️ **on that unit.** ⛔ **Do not carry it to yours:** the unit in hand's zeros were rewritten to 460 / 620 by the wizard, and **a zero is not a scale.**
- **The transport.** ESP32-S3 **native USB Serial/JTAG** — VID `0x303A` / PID `0x1001` — on **both** units. ⛔ **No CP210x and no CH9102**, so the line settings and the auto-reset behaviour are the ESP32-S3's, not a USB-UART bridge's.
- **What the shell can be told.** `head nod|shake|center|<pan> <tilt>`, `vmen on|off`, `track on|off|mirror`, `follow`, `search`, `say` / `greet` / `tts`, `brain <url>`, `wifi` / `scan` / `target` / `gw`, `rover`, `i2cint` / `camtest`, `status` / `ping` / `clear` / `reboot`. ⚠️ **That is the 10/04 unit's shell, and it came with the other firmware.** ⛔ **The unit in hand has no shell.**
- **The flash layout** on the 10/04 unit: nvs 20 KB, otadata 8 KB, app0 3072 KB, app1 3072 KB, ffat 10112 KB, coredump 64 KB. ⚠️ **The same layout is not the same firmware** — the unit in hand boots slot `ota_1` at `0x510000`.

## ⛔ One measured fact that collides with this engine

⚠️ **This is the row that should stop you before you send anything at a cycle.**

Quoted from the sample game written against the 10/04 unit:

> If the next command is sent before the servo finishes moving, the servo stalls, the power rail drops, and **both axes become unresponsive.** Commands that involve movement must be at least one second apart. (`MOVE_SETTLE = 1.0`)

⛔ **And this engine is built to send a target every 15–20 ms.** Whether that is survivable on this machine **has not been measured** — and the one datapoint on the record points the other way: `head 90 135` **stalled the servo, dropped the rail, and left both axes reporting `yaw=-1 pitch=-1`.** Recovery was `vmen off` → `vmen on`, which worked 3 times out of 3.

⇒ **The period, the velocity ceiling and the envelope for this route are all unmeasured, and carry no defaults** — the same rule as machine 1's `Envelope`: a number nobody measured is not a default, it is a guess wearing a default's clothes. ⚠️ **And the gate is the only thing that can answer it** — `velocity` is what makes it refuse the one frame that is too fast. **Without that number, the gate protects nothing.**

⚠️ **And send `track off` before anything else.** The camera's face tracking floods the stream with `cam_hal: EV-VSYNC-OVF` and makes the shell unresponsive. **Whether that was the firmware's doing or the camera's is not recorded** — but on the 10/04 unit, the shell looked broken until tracking was turned off.

## What "stop" is, here

⛔ **There is no stop command on this machine either.**

| command | what it actually does |
|---|---|
| `vmen off` | turns the **servo power** off — ⚠️ **and a servo with no power holds no position** |
| `reboot` | ⚠️ **a reboot is not a stop** — the rail comes back, and the servo resumes whatever it was last told |
| "hold still" | **there is no such command** |
| pulling the cable | ⛔ **the same trap as machine 1** — the machine does not stop because the host left |

⚠️ **And here it is worse than machine 1, not better.** There, the failure mode was torque decaying to a quarter. **Here the recorded failure mode is the rail itself dropping** — ⛔ **which takes the axis you were not commanding down with the one you were.**

⇒ **The stop you will actually use is the power switch, or the battery.** **Know where it is before you open a port** — and on this unit that means before you plug the USB-C cable in, because on the 10/04 unit it was the *flash* path that was live.

## ⛔ The ending that must not be misread

⚠️ **On this machine the green-log ending is easier to reach than it is on machine 1, and that is what makes it more dangerous.**

**The firmware answers.** `ping` comes back with `yaw(id1)=ok pitch(id2)=ok`; `status` prints `raw pos yaw=266 pitch=753`. ⇒ **You can build a log full of numbers coming back from the machine and still not know whether anything moved.** ⛔ **And the servo's own answer is not the proof either.** The record says it exactly:

> `[ScsServo] id: 1 get zero pos: 455 from settings` is only a read from NVS — **it is not evidence of bus communication.** The only evidence that it moves is **that the neck actually moved.**

⇒ **Here, as there: a green log can hold what left the host and what came back over the wire. Neither of those is "it moved."**

**What to write down, and where it goes.** ⚠️ **Two different things, going to two different places** — the same rule as machine 1's page.

| what | where |
|---|---|
| **Everything that happened, in order** — which MAC, which port name, what you flashed, **and whether anything moved.** | **`projects/`** — the record vessel. ⛔ **It is empty, and its shape is deliberately undecided** (see `CLAUDE.md`). |
| **The findings — the ones that change what a document now says.** | ⚠️ **Back into the documents that currently say "unknown"** — `CLAUDE.md` § Safety, machine 1's page, and this one. **A finding that is not folded back leaves the document lying.** |

⛔ **And `examples/` does not exist.** **`projects/` is the only place for work and for records.**

## What is not here

- ⛔ **No serial layer, and no firmware.** `engine/backend/` frames, gates and transmits to a mock, and stops there. ⚠️ **The port-opening code is planned to arrive *after* this page, not before** — a route that touches the wire before its checklist exists is a step with no procedure over it.
- ⛔ **Nothing on this page rings on a check.** ⚠️ **The same reason and the same cost as machine 1's page**: these are confirmations performed once, by hand, at a unit, and a checker asserting that a list of strings was typed would be noise in the shape of a check. **This page can go stale, and nothing will say so.**
- ⛔ **This page is not the record vessel.** **Nothing here has been observed by this repository.**
- ⚠️ **And it is written from records kept outside this repository** — two directories on a Desktop, and one throwaway checkout of the vendor's source that no longer exists. **Where a line came from a record rather than from this repository's own measurement, the line says so.**
