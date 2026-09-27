---
name: embodied-kinetic-loom
description: 'Writes a Motion Intent — the one typed value where this engine draws the line between the reproducible and the free. Use when a motion has to be given to the machine: a greeting, a reaction, a settling. Draws words from the motion vocabulary in references/README.md, turns them into counts on the machine''s three degrees of freedom, and writes the JSON the engine reads. ⛔ The output is not a file: it is what the machine will do in a room, once, with no undo.'
argument-hint: '(optional) the work, and the motion in words. e.g. /embodied-kinetic-loom:embodied-kinetic-loom pet "a small forward tilt, and back"'
---

<!-- i18n-version: 1.0.0 | canonical: skills/embodied-kinetic-loom/SKILL.md | translated: 2026-09-28 -->

**Language:** [English](SKILL.md) | [日本語](SKILL-ja.md) | [中文](SKILL-zh.md)

# embodied-kinetic-loom — writing a Motion Intent

**This skill writes the one value this engine is built around.** Everything upstream of that value may be free — a judgement, a conversation, a person in the room. Everything downstream of it is a function. **This skill is the upstream end.**

⚠️ **This is a document, not a program.** It instructs a session. ⛔ **No code in this repository calls a model** — the writer is the session's Claude, and this file is what guides it. That is decision D-03, and it is why the trajectory underneath can be tested exactly.

## What this skill is

- **It is the only writer.** ⛔ **Not *the writer in this repository* — the writer.** When no session is running and the Pet is on, the application's own AI writes the intent (decision C), **and it writes it by following this file.** One specification, two callers. **That is why one skill is enough.**
- **Its product is a `Motion Intent`** — a small JSON object, in counts and milliseconds, on the machine's three degrees of freedom.
- **Its source of words is `references/README.md`** — the vocabulary. **Read it before writing anything.**

## ⛔ Read this before the first motion

**The output is not a file.** A file can be re-rendered, re-cut, deleted. **Motion happens once, in a room, and cannot be taken back.**

- **The machine does not check the values it receives.** Clamping to the valid range is the host's job — the vendor's own reference code says so.
- **There is no stop command in the protocol.** `[mo0]` means *stop reporting*. `[sav]` writes to EEPROM. ⛔ **Neither one stops a motor.**
- **The firmware has no soft start and no soft stop.** A step command arrives as a step. **The engine's profiles exist to avoid this, and this skill must not defeat them.**
- **Only the host can hold the machine still.** If sending stops, torque falls to about a quarter within fifteen seconds — **and the motors do not stop.**
- **If one axis enters a forced stop, the other two can no longer be operated.**

⚠️ **These are not cautions about this skill.** They are the reason the deterministic core exists. **They are written out, with the measurements behind them, in `CLAUDE.md`.**

## The procedure

### 1. Draw the words

**Read `references/README.md`.** Its table is the vocabulary: a word, the degree of freedom the machine has, the amount, the time, and ⛔ **a column for the difference the machine cannot cover.**

**Take the words the motion needs, by name.** ⛔ **Do not turn them into numbers in your head and then write the numbers.** The number comes from the row — not from a feeling about what *gentle* means.

### 2. If the word is not in the table

⛔ **A word that is not in the table is not in the vocabulary.** **Do not invent one at the point of writing the intent.**

**Write the row first** — into `references/README.md` **and both of its mirrors, in the same commit** — and fill in every column, **including the difference column.** When a word names a freedom the machine does not have, **that column is where the distance is stated**, and it is the reason the column exists.

**The intent is written second.** ⚠️ **This is the only way the vocabulary grows**, and it is deliberate: **a row costs a column that has to be filled in honestly.**

### 3. Write the intent

**The shape is fixed by `schemas/motion-intent.schema.json`** — one object, one key, an array of moves:

```json
{
  "moves": [
    { "dof": "pitch", "target": 552, "duration_ms": 600, "group": 0 },
    { "dof": "pitch", "target": 512, "duration_ms": 600, "group": 1 }
  ]
}
```

- **`dof` is one of `pitch`, `roll`, `yaw`.** ⚠️ **These names are ours, not the machine's** — the control box documents no canonical axis correspondence, and the sign of every axis depends on the wiring.
- **`target` is in counts**, the protocol's own unit. ⛔ **The admissible range is deliberately not in the type.** By default the host may command 190–833, and the box's limits are feedback-driven rather than constants. **The envelope is supplied at run time; do not write a range into an intent and then trust it.**
- **`duration_ms`** is how long the move takes. **Moves sharing a `group` run together**, every move in a group must have the same duration, **and groups run in ascending order from zero.**
- ⛔ **The words are not written into the intent.** The schema is closed, and it is right to be. **An intent is already counts, and it cannot say why the number is that number** — `references/README.md` is the only place the two are held together.
- **`quality` is the one field left open, and the engine ignores it.** A value written there changes nothing that runs. **It stays open because the half of the mapping that would fill it does not exist yet** — the adverbs.

**Where it goes: `projects/<the work>/motions/<name>.json`.** `projects/` is the only place for work and for records in this repository.

### 4. Run it, and run the checks

```bash
python3 -m projects.pet --motion <name>   # the face and the body, from one clock
python3 -m pytest tests/ -q               # what is checked, and where, is in tests/README.md
python3 tools/check_vocabulary.py         # the table: columns, degrees of freedom, paths
python3 tools/check_i18n.py               # the mirrors, including any row just added
claude plugin validate --strict .         # only when .claude-plugin/ was touched
```

⛔ **`--motion` sends to a mock, not to the machine.** The serial layer is the one part the machine gates, and it is not written.

## What this skill must not do

- ⛔ **Invent a word.** See §2.
- ⛔ **Write the words into the intent.** The schema would refuse them, and the schema is right.
- ⛔ **State a range.** The safety envelope belongs to the run-time host.
- ⛔ **Write the row afterwards, to match what was sent.** The row is written first, deliberately.
- ⛔ **Reach the machine.** Nothing in this repository opens a port.

## What this skill cannot do

**Say whether the motion is right.** The mechanism is checkable; **the goal is not.** ⚠️ **A green suite means the mechanism computed what it was told to compute** — nothing more. `docs/verification-boundary.md` is where that line is argued.

⛔ **And the mapping itself has no check.** `tools/check_vocabulary.py` reads the table's shape, not its truth. **The round trip through your judgement is the one step nothing verifies.**
