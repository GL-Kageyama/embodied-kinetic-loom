<!-- i18n-version: 1.6.0 | canonical: README.md | translated: 2026-09-28 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# embodied-kinetic-loom

<p align="center">
  <img src="assets/repo-hero.png" width="100%" alt="embodied-kinetic-loom">
</p>

**An intent becomes motion, and the motion leaves the file.**

The other looms in this workshop stop at a file. Images are written to disk, audio is written to disk, a shot list is written to disk — and a file can be re-rendered, re-cut, deleted. **Motion is an event in a room.** It happens once, in front of whoever is there, and it cannot be taken back. There is no undo, no second take, and no way to see it again after the fact unless someone wrote down what happened.

That single difference is what this repository is built around.

## The proposition

**The boundary between the reproducible and the variable is drawn at one typed value — the `Motion Intent` — and the machine reads it.**

Everything upstream of that type is free: it may vary, it may be a judgement, it may come from a session with a person in it. Everything downstream of it must be a function: the same input produces the same output, every time. Interpolation, easing, smoothing and limiting are the core of this engine — not the model call.

This is a favourable position, and it is worth stating plainly: **a trajectory is a function, so a trajectory can be tested exactly.** Very little of what this workshop builds can be. **What cannot be tested is whether the result is alive** — and this repository does not pretend otherwise. `CLAUDE.md` said so in its first commit — before any check had gone green.

## What exists today

⚠️ **The vessel, the deterministic core, the sending side down to — but not including — the serial port, and the one writer.**

This repository holds what the engine *is*, what must never be assumed about the machine it will drive, which checks exist, and the part that computes and sends: the `Motion Intent` type with its schema and its reader, the trajectory profiles, easing, smoothing, planning, the limit envelope, admission — and a backend that frames what leaves, gates each frame against the elapsed time, and drives a mock of the control box from a periodic loop.

**And now one motion runs end to end.** `python3 -m projects.pet --motion greeting` reads an intent off disk, admits it, computes the trajectory, passes it through the gate, sends it to the mock — **and draws the face from the same clock, on the same tick.** ⚠️ **That sentence is the whole point of the exercise, and it is asserted rather than described**: two of the Pet's five faces are the same drawing, so *one clock for the face and the body* is not a style preference, it is the only thing separating two states.

⛔ **No byte of that has reached a machine.** That is measured, not asserted: a scan of this workshop's own Python — 143 files, searched for `import hid`, `hidapi`, `pygame`, `joystick`, `evdev`, `pyserial`, `import serial` and `IOHID` — returned **zero**. **The backend stops one layer short of the wire, on purpose** — see below.

**And the writer now exists.** `skills/embodied-kinetic-loom/` holds the one skill — **the only thing that writes a `Motion Intent`.** ⛔ **It is a document, not a program: no code in this repository calls a model, and that is what makes the trajectory underneath it testable.** Its source of words is `references/README.md`, and ⚠️ **as of 2026-09-28 that file is a mapping rather than a fixed table** — written as rows, drawn from by name, **and grown by use, which is the only way it grows.** ⛔ **Drawn from by whom is the whole question: by Claude, not by a program** — so the canonical form is a table a reader reads, and no second, machine-only copy is built, because nothing would read it.

⚠️ **The core, the backend, the Pet's screen and the Pet's motion are green — twenty-two files, two hundred and sixty-seven tests, measured 2026-09-28 — and green means the mechanism computes what it was told to compute. It says nothing about whether anything is *there*.**

## Structure

```
.claude-plugin/     plugin.json and marketplace.json — the two files that must carry one version
docs/               the documents, canonical English with -ja and -zh mirrors beside them
tools/              check_i18n.py — the mirrors; check_vocabulary.py — the vocabulary table; purity.py — the forbidden imports
tests/              the suites — twenty-two files, two hundred and sixty-seven tests
schemas/            motion-intent.schema.json — the Motion Intent type
engine/             the deterministic core. ⚠️ It calls no LLM and imports nothing that varies
engine/backend/     the sending side — protocol, cycle, gate, axis map, transmitter, mock
skills/             the one writer — the skill that writes a Motion Intent
references/         the motion vocabulary — written as rows, drawn from by name, grown by use
assets/             the repository's face (the README hero)
locales/            the program's own words — en / ja / zh
projects/pet/       the Pet — the five faces, the frame that carries them, and the motion that runs
install.sh          installs the skill (--local writes .claude/skills/, which is committed)
```

**`projects/` is the only place for work and for records; there is no `examples/`.** ⚠️ **The unit is deliberately undecided** — one reaction, one day's session, or the Pet's whole life all go into the same vessel.

⚠️ **`projects/pet/` is the first thing to live there.** The five faces are copied verbatim from the concept document, and the Pet is a cat by decision rather than by default — see that directory's README, which records the two decisions behind it. **The core and the screen are now joined: `motions/greeting.json` is a `Motion Intent` written by a session, and `motion.py` carries it through admission, the gate and the mock while the face is drawn from the same tick.**

## What is not here yet

- **No serial layer.** The backend frames, gates and transmits; nothing opens a port. ⛔ **This is the one part the machine gates**, because the control box has two generations and the protocol differs between them — and it is exactly where a mock and the machine diverge most.
- ⚠️ **The vocabulary has one row, not five.** Of the five verbs it starts from — 傾く / 倒れる / 沈む / 跳ねる / 後退 — **three name a degree of freedom this machine does not have**, and the mapping carries an explicit column saying what the difference is. ⛔ **The four missing rows are the ones that were not used**, and writing them now would be writing down what has never run.

## Next

1. **The serial layer** — the one step that reaches the wire. ⛔ **Gated on the machine**: confirm which generation of control box is in hand before trusting any protocol document, including this repository's.
2. **A second motion** — the vocabulary starts from five verbs. ⚠️ **Three of them name a translation this machine does not have, so not one row has yet crossed the difference column** — and how that column behaves has never been exercised.

⚠️ **Step 1 is the only one the machine gates; step 2 is waiting on work.** **And finishing either says nothing about whether anything is *there*.**

## Language

**Canonical English, with `-ja` and `-zh` mirrors in the same directory** (suffix style, never subfolders — a subfolder changes the depth, and a changed depth breaks every relative path in the document). `tools/check_i18n.py` reads them.

⚠️ **The program speaks three languages too.** `--lang {en,ja,zh}` — or the `EMBODIED_KINETIC_LOOM_LANG` environment variable — picks the language of what the Pet prints; **the default is `en`.** The strings live in `locales/`, and **the core cannot reach them**: it returns codes, and the edge turns them into sentences.

**The working language of this workshop is Japanese**, which is why `HISTORY.md` and commit messages are written in it. That is a different thing from the canonical language of the documents.

## License

MIT — see [LICENSE](LICENSE).
