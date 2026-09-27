<!-- i18n-version: 1.0.0 | canonical: README.md | translated: 2026-09-27 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# embodied-kinetic-loom

**An intent becomes motion, and the motion leaves the file.**

The other looms in this workshop stop at a file. Images are written to disk, audio is written to disk, a shot list is written to disk — and a file can be re-rendered, re-cut, deleted. **Motion is an event in a room.** It happens once, in front of whoever is there, and it cannot be taken back. There is no undo, no second take, and no way to see it again after the fact unless someone wrote down what happened.

That single difference is what this repository is built around.

## The proposition

**The boundary between the reproducible and the variable is drawn at one typed value — the `Motion Intent` — and the machine reads it.**

Everything upstream of that type is free: it may vary, it may be a judgement, it may come from a session with a person in it. Everything downstream of it must be a function: the same input produces the same output, every time. Interpolation, easing, smoothing and limiting are the core of this engine — not the model call.

This is a favourable position, and it is worth stating plainly: **a trajectory is a function, so a trajectory can be tested exactly.** Very little of what this workshop builds can be. **What cannot be tested is whether the result is alive** — and this repository does not pretend otherwise. `CLAUDE.md` said so in its first commit — before any check had gone green.

## What exists today

⚠️ **The vessel, and the deterministic core inside it — and nothing that moves.**

This repository holds what the engine *is*, what must never be assumed about the machine it will drive, which checks exist, and now the part that computes: the `Motion Intent` type with its schema and its reader, the trajectory profiles, easing, smoothing, planning, the limit envelope, and admission. **It does not hold a backend, a mock, or a single line that has driven a physical machine.**

That last point is measured, not asserted. A scan of this workshop's own Python — 143 files, searched for `import hid`, `hidapi`, `pygame`, `joystick`, `evdev`, `pyserial`, `import serial` and `IOHID` — returned **zero**.

⚠️ **The core is green — eight files, eighty tests, measured 2026-09-27 — and green means the mechanism computes what it was told to compute. It says nothing about whether anything is *there*.**

## Structure

```
.claude-plugin/     plugin.json and marketplace.json — the two files that must carry one version
docs/               the documents, canonical English with -ja and -zh mirrors beside them
tools/              check_i18n.py — the check that reads the mirrors
tests/              the suites — eight files, eighty tests
schemas/            motion-intent.schema.json — the Motion Intent type
engine/             the deterministic core. ⚠️ It calls no LLM and imports nothing that varies
skills/             ⚠️ not yet — one skill, gated
references/         ⚠️ not yet — the motion vocabulary, partly gated
projects/           work and records. ⚠️ not yet — the record starts when the machine arrives
```

**`projects/` is the only place for work and for records; there is no `examples/`.** ⚠️ **The unit is deliberately undecided** — one reaction, one day's session, or the Pet's whole life all go into the same vessel.

## What is not here yet

- **No backend and no mock.** The core computes a trajectory; nothing sends one. ⚠️ **And the limit check runs at plan time — there is no gate on what actually leaves.**
- **No `skills/`.** One skill is decided; what it contains is gated on a question that is still open — *who writes when no session is running*.
- **No `references/`.** The motion vocabulary exists as research. Of the five verbs it starts from — 傾く / 倒れる / 沈む / 跳ねる / 後退 — three name a degree of freedom this machine does not have, so three cannot be written yet.
- **No `install.sh`.** It is written the way the sister repositories write it, and that way pre-validates that the skill exists — so it cannot be written before the skill is.
- **No `assets/repo-hero.png`.** The picture on the front says what a repository is about; that sentence did not exist until this file did.

## Next

1. **The sending side** — a backend, a mock, and the gate that checks each frame as it leaves. ⚠️ **This one is gated on the machine**: the control box has two generations, and the protocol differs between them.
2. **`skills/`** — one skill is decided, and what it contains is still gated on *who writes when no session is running*. **That question is the author's, not this repository's.**
3. **`references/`** — the motion vocabulary. Three of its five starting verbs name a degree of freedom this machine does not have, and how to carry them across is also the author's.

⚠️ **Steps 2 and 3 are not waiting on the machine; they are waiting on a decision. Step 1 is the only one the machine gates.** **And finishing any of them says nothing about whether anything is *there*.**

## Language

**Canonical English, with `-ja` and `-zh` mirrors in the same directory** (suffix style, never subfolders — a subfolder changes the depth, and a changed depth breaks every relative path in the document). `tools/check_i18n.py` reads them.

**The working language of this workshop is Japanese**, which is why `HISTORY.md` and commit messages are written in it. That is a different thing from the canonical language of the documents.

## License

MIT — see [LICENSE](LICENSE).
