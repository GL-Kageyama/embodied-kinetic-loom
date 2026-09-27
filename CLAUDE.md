<!-- i18n-version: 1.0.0 | canonical: CLAUDE.md | translated: 2026-09-27 -->

**Language:** [English](CLAUDE.md) | [日本語](CLAUDE-ja.md) | [中文](CLAUDE-zh.md)

# embodied-kinetic-loom — Project Instructions

## Document Rules

- **The canonical language of every document is English.** `-ja` and `-zh` mirrors sit in the same directory, with a suffix — never in a subfolder (`docs/usage.md`, `docs/usage-ja.md`, `docs/usage-zh.md`). A subfolder changes the depth, and a changed depth breaks every relative path inside the document.
- `tools/check_i18n.py` reads the mirrors. It checks four things: that all three exist and are non-empty, that the `<!-- i18n-version: … -->` header is byte-identical across the three and names the canonical, that the `**Language:**` line is byte-identical, and that code fences containing `←` and the heading-level sequence are byte-identical. **Run it before every commit that touches a document.**
- ⚠️ **The working language and the canonical language are two different things.** Commit messages and `HISTORY.md` are written in Japanese. `README.md`, `CLAUDE.md` and `docs/` are written in English.
- **Numbers are read as measurements.** Before writing any count, count it. Name what was counted and what was not. A count that moves depending on where you cut it does not belong in a rule.
- **A blank is not neutral.** If a decision is to leave something out, write the reason for the omission. An empty field is filled by someone else's default.

## Where the Design Lives

**The design notes for this engine are not in this repository.** This repository holds the vessel, the deterministic core, and — in time — the rest of the implementation. The reasoning behind a fixed policy is recorded with the policy, in the section that states it.

**Where the boundary is argued — `docs/verification-boundary.md`.** The distinction between what can be verified and what cannot is the single most load-bearing document here. Read it before claiming that something works.

## Fixed Policy (do not change)

- **The output is not a file.** Every other repository in this workshop writes a file and stops: images, audio, text. **Motion is an event in a room, and an event that has happened cannot be taken back.** There is no undo, no re-render, and no second take.
- **The boundary between the deterministic and the free is drawn at one type — the `Motion Intent`.** Everything upstream of it may vary. Everything downstream of it must be a function: the same input produces the same output. Interpolation, easing, smoothing and limiting are the core of this engine, not the model call.
- **Code in this repository does not call an LLM.** The `Motion Intent` is written in the session, by Claude, guided by the skill. The code reads it and computes. This is what makes the trajectory testable.
- **`projects/` is the only place for work and for records.** There is no `examples/`. ⚠️ **The unit is not decided** — one reaction, one day's session, or the Pet's whole life all go into the same vessel.
- **The machine is not a monitor.** It does not report back what it did. Assume every command lands.

## Safety

⚠️ **This is the only repository in this workshop that leaves the file.** A scan of this workshop's own Python — 143 files, searched for `import hid`, `hidapi`, `pygame`, `joystick`, `evdev`, `pyserial`, `import serial` and `IOHID` — returned **zero**. Nothing here has ever driven a physical machine. Read this section before writing any line that reaches a backend.

**What the machine will not do for you:**

- **The other end does not check the values it receives.** The vendor's own reference code says so. **Clamping to the valid range is the host's job.**
- ⛔ **There is no stop command in the protocol.** `[mo0]` means *stop reporting*. `[sav]` writes to EEPROM. **Neither one stops a motor.**
- **If you stop sending, torque falls to roughly a quarter within 15 seconds — and the motors do not stop.** A dropped connection is not a stopped machine.
- **If one of the three axes enters a forced stop, the other two can no longer be operated.** The vendor's own phrase for this is `one motor locks all`.
- **The upstream firmware has no soft start and no soft stop.** A step command arrives as a step. **Never send a step.**
- **By default, the host may only command targets in the range 190–833** (`Clip Input`). The box's limits are feedback-driven; they are not constants you can read off the protocol.
- **Emergency stop is not standard equipment** (the eBreak is a separate purchase). ⛔ **And the same vendor's CE declaration cites EN 60204-1:2018** — the standard that requires one. **Do not describe this machine as compliant with a standard its own documentation argues with.**
- ⚠️ **This machine has a failure mode in which it leaves the floor.** The owner's report of "one centimetre" is a single visual estimate, not a measurement. **Treat it as an unbounded failure, not a small one.**

**The first thing to check on the real machine:** ⛔ **the control box has two generations.** The earlier one is serial; the current one is an STM32 reached over HID. **Axis correspondence has no canonical form, and the sign of every axis depends on the wiring.** Confirm the generation before trusting any protocol document, including this one.

## What Must Not Be Broken

- ⛔ **Mock is a test of the protocol. A green Mock does not guarantee the safety of the machine.**
  **And the place where Mock and the machine diverge most is the serial layer** — `flush()` was measured blocking forever on a macOS pty. **That is where the Mock is most likely to be lying to you.**
- ⛔ **The goal of this Pet cannot be verified in this workshop. Only the mechanism can be verified. For the goal, only a record of observations remains.**
  ⚠️ **This sentence is placed here on the first day, on purpose.** Added later, it arrives after the checks have gone green — and a green check is read as "it works". **Five green checks mean the mechanism computes what it was told to compute. They mean nothing about whether anything is there.**
- **Verify the mechanism and the goal with different words.** The mechanism is decided: trajectories, range checks, measured latency. The goal has no established method here — a study that measured it at N=1, in a home, was not found. **When you write "verified", say which of the two you mean.**
- **Do not raise contingency as a goal.** A faster reply looks like an improvement and can read as less autonomy.
- **Do not touch `distill-essence-engine`.** The cards are its property. You may read from it; do not rewrite it.

## Tests

**Fifteen files, one hundred and sixty-four tests, all green — measured 2026-09-27.** The five checks, and where each one lives, are in `tests/README.md`.

⚠️ **The core is implemented** — the trajectory family, easing, smoothing, plan, limits and admission, and the `Motion Intent` reader. **So is the sending side** — the frame protocol, the periodic loop, the run-time gate, the axis map, the transmitter, and a mock of the control box. **What is tested is that and nothing else**: interpolation, easing, smoothing, limiting, framing, deadlines, refusals. Those are functions, so they can be checked exactly. **What is not tested is whether the result is alive.**

⚠️ **Nothing in `engine/backend/` opens a port.** The serial layer is the one part the machine gates — two generations of control box, two protocols — and **it is where a mock and the machine diverge most**: `flush()` was measured blocking forever on a macOS pty. **A green suite says nothing about the wire.**

**This section must not say "there is nothing yet" while test files sit on disk.** That state is not hypothetical — a sister repository is in it right now: it has seven test files and fifty-four tests, and its `CLAUDE.md` still reads "not yet built". ⚠️ **That is why this section changed in the same commit as the tests** — the rule was applied to itself, on the day it was written.

Run: `python3 -m pytest tests/`

## Language (i18n)

- **Canonical English, with `-ja` and `-zh` mirrors in the same directory** (suffix style — see Document Rules).
- **The default language is `en`.** A `--lang` argument and an environment variable may lower it to `ja`.
- **Runtime string tables are not built yet.** They arrive with the first stage that has runtime strings. They are not built up front, alongside the document mirrors.
- **`tools/check_i18n.py` is the check.** A mirror set that nothing checks rots without anyone noticing — three of the four sister repositories have mirrors and no checker.

## Git

- **`git push` only when the user explicitly asks for it.** A push without a request is forbidden. **The user pushes.**
- ⛔ **Never `git add -A`.** Stage only the paths you actually touched. `git add -A` sweeps up whatever else is in the working tree, including the user's uncommitted work.
- Append `Co-Authored-By: Claude Code <noreply@anthropic.com>` to the end of commit messages.
- **The manifest version tracks `HISTORY.md`.** When a `## <version>` heading goes into `HISTORY.md`, **the same version goes into both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`**. ⚠️ **Two files, one version** — and a third value that must agree: the newest `## <version>` in `HISTORY.md`, **which is the first one, because that file is written newest-first**.
- ⚠️ **Do not write `languages` into either manifest.** Claude Code does not know the field; `claude plugin validate --strict .` fails on it. Three sister repositories carry it and all three fail validation.
- ⚠️ **Do not declare a path in `plugin.json` that does not exist yet.** Measured 2026-09-27: a `"skills": ["./skills/"]` entry with no `skills/` directory on disk fails validation with `Path not found: ./skills/. The runtime loader will report this as a load failure.` **The `skills` key arrives in the same commit as the first file under `skills/`** — not before, and the manifest does not announce a directory that is still gated.
- **`claude plugin validate --strict .` must pass before a commit that touches `.claude-plugin/`.**
