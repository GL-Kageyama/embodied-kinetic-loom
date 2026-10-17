<!-- i18n-version: 1.20.0 | canonical: README.md | translated: 2026-10-18 -->

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

⛔ **No byte of that has reached a machine.** That is measured, not asserted: a scan of this workshop's own Python — **277 files**, vendored trees excluded, searched for `import hid`, `hidapi`, `pygame`, `joystick`, `evdev`, `pyserial`, `import serial` and `IOHID` — returned **zero**. **The backend stops one layer short of the wire, on purpose** — see below.

**And the writer now exists.** `skills/embodied-kinetic-loom/` holds the one skill — **the only thing that writes a `Motion Intent`.** ⛔ **It is a document, not a program: no code in this repository calls a model, and that is what makes the trajectory underneath it testable.** Its source of words is `references/README.md`, and ⚠️ **as of 2026-09-28 that file is a mapping rather than a fixed table** — written as rows, drawn from by name, **and grown by use, which is the only way it grows.** ⛔ **Drawn from by whom is the whole question: by Claude, not by a program** — so the canonical form is a table a reader reads, and no second, machine-only copy is built, because nothing would read it.

✅ **And since 2026-10-18 there is a layer above the wire for the second machine.** `projects/stackchan/` turns Claude Code's hook events into six phases, the Pet's five faces, six lights and five candidate gestures — ⛔ **and sends nothing, because no number for that machine has been measured.** It keeps one neck on one window when two or more run at once. It is the part of the Stack-chan route that can be verified before a firmware is burned. ⚠️ **The daemon that will hold its state exists** — `projects/stackchan/daemon/`, a pure core and a socket edge — **and so does the client a hook runs** — `projects/stackchan/hook/`, one process per event, silent and exit 0. ✅ **Both are installed as of 2026-10-18**: a launchd user agent starts the daemon at login, and all thirty-three hook events in `~/.claude/settings.json` call the client. ✅ **And since the same day the wire exists as source** — `engine/backend/protocol_stackchan.py` frames one ASCII line, `schemas/stackchan-command.schema.json` is the contract both ends read, and `projects/stackchan-firmware/` parses it and **refuses every gesture**. ✅ **And since 0.19.1 the room writes the frame it would send** — `projects/stackchan/outbound.py` diffs the visible state, and the daemon logs `{"frame": …, "sent": false}`. ⛔ **A line in a log is not a wire**: nothing is sent to a machine — the transport is not chosen, and the daemon opens none. ✅ **What did happen on 2026-10-18 is narrower and it did happen**: `projects/stackchan-firmware/` was built, written at `0x510000`, and the head turned — **under a bench command typed into its console, not under a frame.** The record is `projects/stackchan-firmware/records/2026-10-18-first-arrival.md`.

⚠️ **The core, the backend, the Pet's screen and motion, the Stack-chan behaviour layer, its daemon, its outbound frame and its wire are green — twenty-seven files, three hundred and ninety-seven tests, measured 2026-10-18 — and green means the mechanism computes what it was told to compute. It says nothing about whether anything is *there*.**

## Before you connect a machine

⛔ **Nothing here opens a port, and nothing here stops a motor.** If you are about to plug a control box into a computer, read **[`docs/first-contact.md`](docs/first-contact.md)** first — the four questions to settle in the first hour, the one check that gates the backend design, and the nine things about the machine that no document settles.

⚠️ **It is a checklist and nothing rings on it**; that cost is written down on the page. **What it is for is the day the machine arrives** — reconstructing all of this from a design note while standing in front of the box is the situation it exists to prevent.

## Structure

```
.claude-plugin/     plugin.json and marketplace.json — the two files that must carry one version
docs/               the documents, canonical English with -ja and -zh mirrors beside them
tools/              check_i18n.py — the mirrors; check_vocabulary.py — the vocabulary table; purity.py — the forbidden imports
tests/              the suites — twenty-seven files, three hundred and ninety-seven tests
schemas/            motion-intent.schema.json — the Motion Intent type; stackchan-command.schema.json — the frame to machine 2
engine/             the deterministic core. ⚠️ It calls no LLM and imports nothing that varies
engine/backend/     the sending side — protocol, cycle, gate, axis map, transmitter, mock
skills/             the one writer — the skill that writes a Motion Intent
references/         the motion vocabulary — written as rows, drawn from by name, grown by use
assets/             the repository's face (the README hero)
locales/            the program's own words — en / ja / zh
projects/pet/       the Pet — the five faces, the frame that carries them, and the motion that runs
projects/stackchan/ the layer above the wire — events to phases, faces and lights; no numbers for machine 2
projects/stackchan-firmware/  the machine's end of that wire — built, flashed, and one bench move on 2026-10-18
install.sh          installs the skill (--local writes .claude/skills/, which is committed)
```

**`projects/` is the only place for work and for records; there is no `examples/`.** ⚠️ **The unit is deliberately undecided** — one reaction, one day's session, or the Pet's whole life all go into the same vessel.

⚠️ **`projects/pet/` is the first thing to live there.** The five faces are copied verbatim from the concept document, and the Pet is a cat by decision rather than by default — see that directory's README, which records the two decisions behind it. **The core and the screen are now joined: `motions/greeting.json` is a `Motion Intent` written by a session, and `motion.py` carries it through admission, the gate and the mock while the face is drawn from the same tick.**

✅ **`projects/stackchan/` is the second.** It maps Claude Code's hook events onto six phases, those five faces and six lights — ⛔ **and sends nothing, because machine 2's numbers are in no record.** **The mapping needs no measurement; the motion does.** It is built on the side of that line where a check can ring, and it is the part of the Stack-chan route that can be verified before a firmware is burned.

## What is not here yet

- **No serial layer.** The backend frames, gates and transmits; nothing opens a port. ⛔ **This is the one part the machine gates**, because machine 1's control box has two generations and the protocol differs between them — and it is exactly where a mock and the machine diverge most.
- ⛔ **No transport to machine 2, and no frame has arrived there.** The frame is decided, encoded, decoded, tested, and **written to the daemon's log as the line it would send**; **the path it would travel is not chosen**, and the daemon opens none. ⚠️ **What the firmware does today is refuse**: there is no `gesture → angle` table, and an invented angle cannot be told from a measured one in a source file. ✅ **It is no longer source only** — on 2026-10-18 it was built and written, and a bench command turned the head; **that is the machine moving, and it is not a frame arriving.**
- ⚠️ **The vocabulary has one row, not five.** Of the five verbs it starts from — 傾く / 倒れる / 沈む / 跳ねる / 後退 — **three name a degree of freedom machine 1 does not have**, and the mapping carries an explicit column saying what the difference is. ⛔ **The four missing rows are the ones that were not used**, and writing them now would be writing down what has never run.
- ⚠️ **No record of the engine running, and one record of a machine moving.** `--motion` prints its numbers and they scroll away. **The vessel for records is `projects/`** (see `CLAUDE.md`) — ✅ **and since 2026-10-18 it holds one**: `projects/stackchan-firmware/records/2026-10-18-first-arrival.md`, where **what was observed is the spine and the program's numbers are quoted inside it as evidence.** ⛔ **That record is of a bench command, not of this engine** — no `Motion Intent` was read, no trajectory computed, no gate passed. ⛔ **And *the machine has never moved* was never the missing thing** — the author's own unit has, under the vendor's SETUP wizard, seen on 2026-10-15. **What had been missing was an arrival, and the first one is now written down.**

## Next

1. **The serial layer** — the one step that reaches the wire. ⛔ **Gated on the machine**: confirm which generation of control box is in hand before trusting any protocol document, including this repository's.
2. **A second motion** — the vocabulary starts from five verbs. ⚠️ **Three of them name a translation machine 1 does not have, so not one row has yet crossed the difference column** — and how that column behaves has never been exercised.
3. **The transport to machine 2, and one gesture actually arriving** — ✅ **both conditions this step waited on are now met on the unit in hand: the stock image was restored, read back, and watched booting** (`docs/first-contact-stackchan.md`), **and this repository's own firmware has been built, written and seen to move the head** (`projects/stackchan-firmware/records/2026-10-18-first-arrival.md`). ⛔ **What is still missing is the two things neither step could give: a transport, and a `gesture → angle` table** — ⚠️ **the frame is ready; the first angle is not**, and it is written only after that one unit is measured.

⚠️ **Step 1 is the only one the machine gates; steps 2 and 3 are waiting on work and on a measurement.** **And finishing any of them says nothing about whether anything is *there*.**

## Language

**Canonical English, with `-ja` and `-zh` mirrors in the same directory** (suffix style, never subfolders — a subfolder changes the depth, and a changed depth breaks every relative path in the document). `tools/check_i18n.py` reads them.

⚠️ **The program speaks three languages too.** `--lang {en,ja,zh}` — or the `EMBODIED_KINETIC_LOOM_LANG` environment variable — picks the language of what the Pet prints; **the default is `en`.** The strings live in `locales/`, and **the core cannot reach them**: it returns codes, and the edge turns them into sentences.

**The working language of this workshop is Japanese**, which is why `HISTORY.md` and commit messages are written in it. That is a different thing from the canonical language of the documents.

## License

MIT — see [LICENSE](LICENSE).
