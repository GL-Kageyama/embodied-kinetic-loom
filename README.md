<!-- i18n-version: 1.26.0 | canonical: README.md | translated: 2026-10-21 -->

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

⚠️ **The vessel, the deterministic core, the sending side down to — but not including — machine 1's serial port, and the one writer.**

This repository holds what the engine *is*, what must never be assumed about the machine it will drive, which checks exist, and the part that computes and sends: the `Motion Intent` type with its schema and its reader, the trajectory profiles, easing, smoothing, planning, the limit envelope, admission — and a backend that frames what leaves, gates each frame against the elapsed time, and drives a mock of the control box from a periodic loop.

**And now one motion runs end to end.** `python3 -m projects.pet --motion greeting` reads an intent off disk, admits it, computes the trajectory, passes it through the gate, sends it to the mock — **and draws the face from the same clock, on the same tick.** ⚠️ **That sentence is the whole point of the exercise, and it is asserted rather than described**: two of the Pet's five faces are the same drawing, so *one clock for the face and the body* is not a style preference, it is the only thing separating two states.

⛔ **No byte of that motion has reached a machine.** That is measured, not asserted: a scan of this workshop's own Python — **277 files**, vendored trees excluded, searched for `import hid`, `hidapi`, `pygame`, `joystick`, `evdev`, `pyserial`, `import serial` and `IOHID` — returned **zero**. **Machine 1's backend stops one layer short of the wire, on purpose** — see below.

**And the writer now exists.** `skills/embodied-kinetic-loom/` holds the one skill — **the only thing that writes a `Motion Intent`.** ⛔ **It is a document, not a program: no code in this repository calls a model, and that is what makes the trajectory underneath it testable.** Its source of words is `references/README.md`, and ⚠️ **as of 2026-09-28 that file is a mapping rather than a fixed table** — written as rows, drawn from by name, **and grown by use, which is the only way it grows.** ⛔ **Drawn from by whom is the whole question: by Claude, not by a program** — so the canonical form is a table a reader reads, and no second, machine-only copy is built, because nothing would read it.

✅ **And there is a layer above the wire for the second machine.** `projects/stackchan/` turns Claude Code's hook events into six phases, the Pet's five faces, six lights and five gestures — ⛔ **and every gesture it chooses is a word: no number for that machine lives in the package.** It keeps one neck on one window when two or more run at once. ⚠️ **The daemon that holds its state exists** — `projects/stackchan/daemon/`, a pure core and a socket edge — **and so does the client a hook runs** — `projects/stackchan/hook/`, one process per event, silent and exit 0. ✅ **Both are installed**: a launchd user agent starts the daemon at login, and all thirty-three hook events call the client. ✅ **The transport is chosen** — `--port`, one `os.open`/`os.write`/`os.close` per frame, the board's console named in the installed plist — **and the machine's end plays what it receives**: five postures measured on the unit, so a frame carrying a gesture moves the head (`projects/stackchan-firmware/`).

⛔ **What is not guaranteed is that the board answers.** `sent: true` means the host's tty took the line, not that the board received it; since 0.19.41 the frame's acceptance is the board's own line, and four of four were accepted in one run — ⛔ **four frames are not a guarantee.** The bus falls silent on its own, with no trigger named, and the read-back answers sometimes. **The dated record of what was measured is `HISTORY.md`; what was observed is `projects/stackchan-firmware/records/`.**

⚠️ **The core, the backend, the Pet's screen and motion, the Stack-chan behaviour layer, its daemon, its outbound frame and its wire are green — forty-seven files, eight hundred and eighty-seven tests, measured 2026-10-21 — and green means the mechanism computes what it was told to compute. It says nothing about whether anything is *there*.**

## Before you connect a machine

⛔ **Nothing on machine 1's path opens a port, and nothing stops a motor.** If you are about to plug a control box into a computer, read **[`docs/first-contact.md`](docs/first-contact.md)** first — the four questions to settle in the first hour, the one check that gates the backend design, and the nine things about the machine that no document settles.

⚠️ **It is a checklist and nothing rings on it**; that cost is written down on the page. **What it is for is the day the machine arrives** — reconstructing all of this from a design note while standing in front of the box is the situation it exists to prevent.

## Structure

```
.claude-plugin/     plugin.json and marketplace.json — the two files that must carry one version
docs/               the documents, canonical English with -ja and -zh mirrors beside them
tools/              check_i18n.py — the mirrors; check_vocabulary.py — the vocabulary table; purity.py — the forbidden imports
tests/              the suites — forty-seven files, eight hundred and eighty-seven tests
schemas/            motion-intent.schema.json — the Motion Intent type; stackchan-command.schema.json — the frame to machine 2; stackchan-pose.schema.json — its per-tick pose line
engine/             the deterministic core. ⚠️ It calls no LLM and imports nothing that varies
engine/backend/     the sending side — protocol, cycle, gate, axis map, transmitter, mock
skills/             the one writer — the skill that writes a Motion Intent
references/         the motion vocabulary — written as rows, drawn from by name, grown by use
assets/             the repository's face (the README hero)
locales/            the program's own words — en / ja / zh
projects/pet/       the Pet — the five faces, the frame that carries them, and the motion that runs
projects/stackchan/ the layer above the wire — events to phases, faces and lights; no numbers for machine 2
projects/stackchan-firmware/  the machine's end of that wire — built, flashed, and the source of eleven records
install.sh          installs the skill (--local writes .claude/skills/, which is committed)
```

**`projects/` is the only place for work and for records; there is no `examples/`.** ⚠️ **The unit is deliberately undecided** — one reaction, one day's session, or the Pet's whole life all go into the same vessel.

⚠️ **`projects/pet/` is the first thing to live there.** The five faces are copied verbatim from the concept document, and the Pet is a cat by decision rather than by default — see that directory's README, which records the two decisions behind it. **The core and the screen are now joined: `motions/greeting.json` is a `Motion Intent` written by a session, and `motion.py` carries it through admission, the gate and the mock while the face is drawn from the same tick.**

✅ **`projects/stackchan/` is the second.** It maps Claude Code's hook events onto six phases, those five faces and six lights — ⛔ **and every gesture it chooses is a word.** **The mapping needs no measurement; the motion does.** It is built on the side of that line where a check can ring, and it is the part of the Stack-chan route that can be verified before a firmware is burned.

## What is not here yet

- **No serial layer.** The backend frames, gates and transmits; nothing opens a port to machine 1. ⛔ **This is the one part the machine gates**, because machine 1's control box has two generations and the protocol differs between them — and it is exactly where a mock and the machine diverge most. ⚠️ **The author has parked machine 1 for now; this waits without blocking anything else.**
- ⛔ **The board does not always answer.** The transport exists and a frame leaves the host; `sent: true` means the tty took the line, and since 0.19.41 acceptance is the board's own line — four of four accepted in one run is not a guarantee. The bus falls silent on its own, the trigger is unnamed, and the read-back answers sometimes. When it does not, every motion starts from the last pose actually written. ⛔ **A face, a light or a gesture can be lost, and `sent: true` cannot say so.**
- ⚠️ **The vocabulary has one row, not five.** Of the five verbs it starts from — 傾く / 倒れる / 沈む / 跳ねる / 後退 — **three name a degree of freedom machine 1 does not have**, and the mapping carries an explicit column saying what the difference is. ⛔ **The four missing rows are the ones that were not used**, and writing them now would be writing down what has never run.
- ⚠️ **The records vessel holds eleven records, before their `-ja` and `-zh` mirrors.** The first is `projects/stackchan-firmware/records/2026-10-18-first-arrival.md`, where **what was observed is the spine and the program's numbers are quoted inside it as evidence**; later ones carry the engine's own streams, the first day, and one sentence about the goal. ⛔ **A record of motion is not a verification of the goal** — the goal's one record is one person in one room, at N=1, and ⚠️ **the sentence had been offered a moment before.** **Printing is not recording**: `--motion` prints its numbers and they scroll away. ⛔ **And *the machine has never moved* was never the missing thing** — **the author's own unit has moved**, under the vendor's SETUP wizard. **What had been missing was an arrival, and the first one is written down.**

## Next

1. **A read-back that keeps answering** — `docs/stackchan-progress.md` row 7. The host asks the board where the head is at each gesture; the answer comes back sometimes. What closes it is an answer that survives a move, and ⛔ **answering once is not the rung** — the trigger of the silent bus is still unnamed.
2. **A second day, written down** — row 8. One day is in the records; ⛔ **one day is not "day after day".**
3. **The serial layer to machine 1** — the one step that reaches that wire. ⚠️ **The author parked machine 1 for now**; it waits without blocking the climb, and **a second motion waits with it** — the vocabulary starts from five verbs and holds one row, and not one row has crossed the difference column.

⚠️ **Machine 1 is the one the machine gates; the rest waits on work and on a measurement.** **And finishing any of them says nothing about whether anything is *there*.**

## Language

**Canonical English, with `-ja` and `-zh` mirrors in the same directory** (suffix style, never subfolders — a subfolder changes the depth, and a changed depth breaks every relative path in the document). `tools/check_i18n.py` reads them.

⚠️ **The program speaks three languages too.** `--lang {en,ja,zh}` — or the `EMBODIED_KINETIC_LOOM_LANG` environment variable — picks the language of what the Pet prints; **the default is `en`.** The strings live in `locales/`, and **the core cannot reach them**: it returns codes, and the edge turns them into sentences.

**The working language of this workshop is Japanese**, which is why `HISTORY.md` and commit messages are written in it. That is a different thing from the canonical language of the documents.

## License

MIT — see [LICENSE](LICENSE).
