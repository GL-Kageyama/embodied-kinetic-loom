<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/README.md | translated: 2026-10-18 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/stackchan-firmware/ — the device end of the wire

⛔ **Source only. Never built. Never flashed.** Nothing in this repository has ever written a byte to machine 2, and this directory does not change that.

**What is here:** a parser for one command frame, and an `apply_command` that refuses every gesture. **What is not here:** an angle. ⛔ **Every number that would turn `perk` into a servo position is in no record**, so the honest firmware does not have one — it receives the symbol and does not move.

⚠️ **The refusal is not a placeholder for a line someone forgot to write.** It is the line, until the unit in hand has been measured (`docs/first-contact-stackchan.md`). **A guessed angle is indistinguishable from a measured one in the source**, which is why none is written.

## What the frame carries

**One line of JSON per command**, and commands arrive only at a phase transition — this is not a stream. The contract is `schemas/stackchan-command.schema.json`, and both ends read it.

| field | values | meaning |
|---|---|---|
| `face` | the Pet's five faces, or `null` | show this expression; `null` = do not change |
| `light` | `off` / `dim` / `breathe` / `warm` / `alert` / `error` | always present, never `null` |
| `gesture` | `perk` / `nod` / `turn` / `settle` / `flinch`, or `null` | move the neck; `null` = do not move |

⛔ **There is no `sound` field.** The speaker is a channel that does not exist yet.

## What this source deliberately does not decide

- **the angle table** — no record, no measurement, no line;
- **the LED mapping** — twelve pixels and their colour order are not recorded for this unit;
- **the display renderer** — the face is a meaning here, not pixels;
- **the transport** — this file parses a line; how the line reaches the board is the wire's framing problem, and the unit in hand is a client of the vendor's cloud rather than a server on the LAN.

## What must happen before the first flash

⛔ **One restore of the stock image, and then the version read back.** The safety net exists and was verified by reading; the write path has never been exercised on this host. `docs/first-contact-stackchan.md` holds the file, its hashes, and the choice that must be written down before anything is pressed.

⚠️ **Nothing rings on this directory.** There is no C++ test here, and no build. `tests/test_stackchan_wire.py` reads these literals and refuses the day they disagree with the schema — that is the only check, and it checks a copy, not the machine.
