<!-- i18n-version: 2.0.0 | canonical: projects/stackchan-firmware/README.md | translated: 2026-10-18 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/stackchan-firmware/ — the device end of the wire

✅ **Built, flashed, and the head turned — 2026-10-18.** This directory produced `build/stackchan-vessel.bin`, wrote it at `0x510000`, verified it by hash, and ran it: the app printed `ready.`, both servos answered a ping, and `bench move 5` turned the head. ⛔ **The refusal below is unchanged** — no gesture has an angle, and a frame that carries one is still refused. **The record is `records/2026-10-18-first-arrival.md`, and the observation is its spine.**

**What is here:** a parser for one command frame, and an `apply_command` that refuses every gesture. **What is not here:** an angle. ⛔ **The number that would turn `perk` into a servo position is in no record** — the vendor's source gives the **scale** between degrees and counts, and that is a different number from **which** angle a `perk` is.

⚠️ **The refusal is not a placeholder for a line someone forgot to write.** It is the line, until the unit in hand has been measured (`docs/first-contact-stackchan.md`). **A guessed angle is indistinguishable from a measured one in the source**, which is why none is written.

## What the frame carries

**One line of JSON per command**, and a command arrives when what the machine should show changes — a phase, a face, a light, or a chosen gesture. This is not a stream. ⚠️ **The neck moves only at a transition**: a gesture is chosen there and nowhere else. The contract is `schemas/stackchan-command.schema.json`, and both ends read it.

| field | values | meaning |
|---|---|---|
| `face` | the Pet's five faces, or `null` | show this expression; `null` = do not change |
| `light` | `off` / `dim` / `breathe` / `warm` / `alert` / `error` | always present, never `null` |
| `gesture` | `perk` / `nod` / `turn` / `settle` / `flinch`, or `null` | move the neck; `null` = do not move |

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

⛔ **What is still in no record is the table this directory refuses to invent: what angle a `perk` is.** The scale tells you how to send an angle. It does not tell you which angle.

## What this source deliberately does not decide

- **the gesture table** — what angle a `perk` is: no record, no measurement, no line. ✅ **The degrees-to-counts scale is no longer on this list** — the vendor's source holds it, above;
- **the LED colours** — ✅ **the order is now known to be RGB565 behind the expander**; what is missing is the choice of colour, which is a choice and not a measurement;
- **the display renderer** — the face is a meaning here, not pixels;
- **the transport** — this file parses a line; how the line reaches the board is the wire's framing problem, and the unit in hand is a client of the vendor's cloud rather than a server on the LAN.

## The first flash — 2026-10-18

✅ **The restore was written, read back, and watched booting.** On 2026-10-18, on the unit in hand: the stock image was written and read back bit-for-bit, **it booted — its own USB log showed the launcher opening and every app being created** — then the current snapshot was written back, read back the same way, and **that booted too.** `docs/first-contact-stackchan.md` holds the files, their hashes, the measured diff, and the exact boot observations.

✅ **Then the image this directory produces was built and written.** `build/stackchan-vessel.bin`, 272,976 bytes, at `0x510000`, hash verified; the app reached `ready.` and the bench turned the head. ⛔ **What that did not close is the gate at the top of this page:** every gesture in a frame is still refused, because no angle has been measured. **The move was a bench command — no `Motion Intent`, no trajectory, no gate** (`records/2026-10-18-first-arrival.md`).

⚠️ **Still nothing rings on this directory.** There is no C++ test here, and **nothing in this repository builds it** — `idf.py build` was run by hand that day and no check repeats it. `tests/test_stackchan_wire.py` reads these literals and refuses the day they disagree with the schema — that is the only check, and it checks a copy, not the machine.
