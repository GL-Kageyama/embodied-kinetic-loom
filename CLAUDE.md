<!-- i18n-version: 1.5.0 | canonical: CLAUDE.md | translated: 2026-09-28 -->

**Language:** [English](CLAUDE.md) | [日本語](CLAUDE-ja.md) | [中文](CLAUDE-zh.md)

# embodied-kinetic-loom — Project Instructions

## Document Rules

- **The canonical language of every document is English.** `-ja` and `-zh` mirrors sit in the same directory, with a suffix — never in a subfolder (`docs/usage.md`, `docs/usage-ja.md`, `docs/usage-zh.md`). A subfolder changes the depth, and a changed depth breaks every relative path inside the document.
- `tools/check_i18n.py` reads the mirrors. It checks four things: that all three exist and are non-empty, that the `<!-- i18n-version: … -->` header is byte-identical across the three and names the canonical, that the `**Language:**` line is byte-identical, and that code fences containing `←` and the heading-level sequence are byte-identical. **Run it before every commit that touches a document.**
- **`tools/check_vocabulary.py` reads the vocabulary table in `references/README.md`.** ⛔ **A word that is not in the table is not in the vocabulary**, and a row is written *before* the intent that needs it — never after. **Run it before every commit that touches `references/`.**
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
- ⛔ **The vocabulary is a mapping, not a fixed table, and a word that is not in it is not in the vocabulary.** A row is written **before** the intent that needs it, and it carries a column for the difference this machine cannot cover. **This is D-02, answered 2026-09-28** — ⚠️ **the drawer is Claude, not a program**, which is why the canonical form is a table a reader reads and no machine-only second copy exists.
  ⚠️ **The word is *mapping*, by the author's ruling of 2026-09-28** — **a catalogue lists what exists; a mapping says what a word becomes on this machine.** ⇒ **A row can only exist where that actually happened.** The file was called a catalogue until that day; the name changed, the rule did not.
- **`projects/` is the only place for work and for records.** There is no `examples/`. ⚠️ **The unit is not decided** — one reaction, one day's session, or the Pet's whole life all go into the same vessel.
  ⛔ **The records vessel is empty, and nothing fills it.** `--motion` prints its numbers and the terminal scrolls; **printing is not recording.** It is empty because **the machine has never been reached** — and with no machine there is nothing to observe, and **observation is the only route to the goal.**
  ⚠️ **The shape of the first record is deliberately not decided here.** Two candidates: a log the program writes (*what left the host*) and a note the session writes (*what the author saw*). ⛔ **The first cannot contain the thing the record is for** — whether anything moved — **so a green log reads as evidence it is not.** **The shape is decided on the day there is something to put in it** — not after the first live run, when the wanting to write it down is loudest.
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

**Twenty-two files, two hundred and sixty-seven tests, all green — measured 2026-09-28.** The five checks, and where each one lives, are in `tests/README.md`. ⚠️ **Three checks are not tests and do not live there** — `claude plugin validate --strict .`, `tools/check_i18n.py` and `tools/check_vocabulary.py`; the two tools have a `--self-test`.

⚠️ **The core is implemented** — the trajectory family, easing, smoothing, plan, limits and admission, and the `Motion Intent` reader. **So is the sending side** — the frame protocol, the periodic loop, the run-time gate, the axis map, the transmitter, and a mock of the control box. **So is the Pet's screen** — `projects/pet/`, the five faces and the frame that carries them. **And so is one motion, end to end** — `motions/greeting.json` is an intent off disk, and `motion.py` carries it through admission and the gate to the mock **while drawing the face from the same tick.** ⛔ **That last one is the repository's first claim about a joint between the two, and it is asserted, not described**: two of the five faces are the same drawing. **What is tested is that and nothing else**: interpolation, easing, smoothing, limiting, framing, deadlines, refusals, the shape of a frame, and that one clock drives both the face and the body. **A twelfth file checks something else: that every word the entry point can print exists in all three languages, and that the core cannot emit a refusal code the tables cannot render.** Those are functions, so they can be checked exactly. **What is not tested is whether the result is alive.**

⚠️ **`tests/test_purity.py` walks `engine/**` and nothing else.** `projects/pet/` came to live inside this repository on 2026-09-28, and it gets its own scan — `tests/test_pet_purity.py` — **over the same forbidden list, which now sits in `tools/purity.py` so that there is one list and not two.** ⛔ **That does not make the two directories equally safe: the scan reads imports, and imports are all it reads.**

⚠️ **Nothing in `engine/backend/` opens a port.** The serial layer is the one part the machine gates — two generations of control box, two protocols — and **it is where a mock and the machine diverge most**: `flush()` was measured blocking forever on a macOS pty. **A green suite says nothing about the wire.**

**This section must not say "there is nothing yet" while test files sit on disk.** That state is not hypothetical — a sister repository is in it right now: it has seven test files and fifty-four tests, and its `CLAUDE.md` still reads "not yet built". ⚠️ **That is why this section changed in the same commit as the tests** — the rule was applied to itself, on the day it was written.

Run: `python3 -m pytest tests/`

## Language (i18n)

- **Canonical English, with `-ja` and `-zh` mirrors in the same directory** (suffix style — see Document Rules).
- **The default language is `en`.** A `--lang` argument and an environment variable may lower it to `ja` **or to `zh`** — ⚠️ **the sentence said `ja` alone until the tables arrived, and the document mirrors were already trilingual.**
- ✅ **The runtime string tables arrived on 2026-09-28: `locales/{en,ja,zh}.json`.** They were not built up front, alongside the document mirrors — **they arrive with the first stage that has runtime strings, and that stage was 0.5.0.** ⚠️ **So the rule held and the table was late: five versions of the entry point printed strings that nothing could change.** The priority is `--lang` > `EMBODIED_KINETIC_LOOM_LANG` > `en`, and `zh` is included because the document mirrors are already trilingual.
  ⛔ **`resolve()` is pure; the entry point reads the environment.** `os` is on the forbidden list with the reason *environ*, **so the core cannot settle a language** — `projects/pet/strings.py` is the reader and `tests/test_strings.py` is the check. ⚠️ **The shape is the clock's**: the edge reads the world, the core receives values.
  ⛔ **An exception message is not a runtime string.** The messages that remain Japanese throughout `engine/` are written to the workshop, and **whether they should move is a decision not yet taken.** What moved is the one thing that reached a user's eyes: **`Rejection.reason` was a Japanese sentence, and it is now a code plus the values to fill in** — a sentence is not a value, and neither a machine nor a table can reach it.
- **`tools/check_i18n.py` is the check for documents.** A mirror set that nothing checks rots without anyone noticing — three of the four sister repositories have mirrors and no checker. ⚠️ **It does not read the JSON tables** — a different medium, with a different shape — **so the same rule is asserted a second time in `tests/test_strings.py`, and neither check covers the other.**

## Git

- **`git push` only when the user explicitly asks for it.** A push without a request is forbidden. **The user pushes.**
- ⛔ **Never `git add -A`.** Stage only the paths you actually touched. `git add -A` sweeps up whatever else is in the working tree, including the user's uncommitted work.
- Append `Co-Authored-By: Claude Code <noreply@anthropic.com>` to the end of commit messages.
- **The manifest version tracks `HISTORY.md`.** When a `## <version>` heading goes into `HISTORY.md`, **the same version goes into both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`**. ⚠️ **Two files, one version** — and a third value that must agree: the newest `## <version>` in `HISTORY.md`, **which is the first one, because that file is written newest-first**.
  ✅ **`tests/test_versions.py` checks all three, since 2026-09-28.** ⛔ **Before that, the third value was the one nobody read**: `validate --strict` compares the two manifests and stops there, and a `HISTORY.md` left at the last version is exactly the file a reader trusts to say what this version contains. **A rule with no check is this repository's own definition of a defect** — the same shape as the easing docstring that the four checks all passed over.
- ⚠️ **Do not write `languages` into either manifest.** Claude Code does not know the field; `claude plugin validate --strict .` fails on it. Three sister repositories carry it and all three fail validation.
- ⚠️ **Do not declare a path in `plugin.json` that does not exist yet.** Measured 2026-09-27: a `"skills": ["./skills/"]` entry with no `skills/` directory on disk fails validation with `Path not found: ./skills/. The runtime loader will report this as a load failure.` **The `skills` key arrives in the same commit as the first file under `skills/`** — not before, and the manifest does not announce a directory that is still gated. ✅ **It arrived on 2026-09-28, with `skills/embodied-kinetic-loom/SKILL.md`, and `validate --strict` passes with it.**
- **`claude plugin validate --strict .` must pass before a commit that touches `.claude-plugin/`.**
