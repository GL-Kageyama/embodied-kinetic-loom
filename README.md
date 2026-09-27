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

⚠️ **The vessel, the deterministic core, and the sending side down to — but not including — the serial port.**

This repository holds what the engine *is*, what must never be assumed about the machine it will drive, which checks exist, and now the part that computes and sends: the `Motion Intent` type with its schema and its reader, the trajectory profiles, easing, smoothing, planning, the limit envelope, admission — and a backend that frames what leaves, gates each frame against the elapsed time, and drives a mock of the control box from a periodic loop.

⛔ **No byte of that has reached a machine.** That is measured, not asserted: a scan of this workshop's own Python — 143 files, searched for `import hid`, `hidapi`, `pygame`, `joystick`, `evdev`, `pyserial`, `import serial` and `IOHID` — returned **zero**. **The backend stops one layer short of the wire, on purpose** — see below.

⚠️ **The core, the backend and the Pet's screen are green — eighteen files, two hundred and thirteen tests, measured 2026-09-28 — and green means the mechanism computes what it was told to compute. It says nothing about whether anything is *there*.**

## Structure

```
.claude-plugin/     plugin.json and marketplace.json — the two files that must carry one version
docs/               the documents, canonical English with -ja and -zh mirrors beside them
tools/              check_i18n.py — the check that reads the mirrors; purity.py — the forbidden-import list
tests/              the suites — eighteen files, two hundred and thirteen tests
schemas/            motion-intent.schema.json — the Motion Intent type
engine/             the deterministic core. ⚠️ It calls no LLM and imports nothing that varies
engine/backend/     the sending side — protocol, cycle, gate, axis map, transmitter, mock
skills/             ⚠️ not yet — one skill, gated
references/         ⚠️ not yet — the motion vocabulary, partly gated
projects/pet/       the Pet's screen — the five faces, and the frame that carries them
```

**`projects/` is the only place for work and for records; there is no `examples/`.** ⚠️ **The unit is deliberately undecided** — one reaction, one day's session, or the Pet's whole life all go into the same vessel.

⚠️ **`projects/pet/` is the first thing to live there, and it is a face and nothing else.** The five faces are copied verbatim from the concept document, and the Pet is a cat by decision rather than by default — see that directory's README, which records the two decisions behind it. **No motion reaches it: the core computes trajectories, and nothing yet connects that computation to this screen.**

## What is not here yet

- **No serial layer.** The backend frames, gates and transmits; nothing opens a port. ⛔ **This is the one part the machine gates**, because the control box has two generations and the protocol differs between them — and it is exactly where a mock and the machine diverge most.
- **No `skills/`.** One skill is decided. ⚠️ **The question that gated it — *who writes when no session is running* — was answered on 2026-09-28: the application's AI does, and the Pet lives inside this repository. What still gates the skill is a narrower question: whether the motion vocabulary is a fixed table or a catalogue that can be drawn from.**
- **No `references/`.** The motion vocabulary exists as research. Of the five verbs it starts from — 傾く / 倒れる / 沈む / 跳ねる / 後退 — three name a degree of freedom this machine does not have. ⚠️ **That was decided on 2026-09-28: the verbs stay in the vocabulary, and the mapping carries an explicit column saying that this machine has no such freedom, which is the nearest thing it can do, and what the difference is.** The table itself is not written yet.
- **No `install.sh`.** It is written the way the sister repositories write it, and that way pre-validates that the skill exists — so it cannot be written before the skill is.
- **No `assets/repo-hero.png`.** The picture on the front says what a repository is about; that sentence did not exist until this file did.

## Next

1. **The serial layer** — the one step that reaches the wire. ⛔ **Gated on the machine**: confirm which generation of control box is in hand before trusting any protocol document, including this repository's.
2. **The Pet's motion** — connecting the screen in `projects/pet/` to the core in `engine/`, from one clock. ⚠️ **The faces show why: two of the five states are the same drawing, and only the motion separates them.**
3. **`references/`** — the motion vocabulary, now that the three missing verbs have a decided place to go.
4. **`skills/`** — gated on the narrower vocabulary question above.

⚠️ **None of 2, 3 or 4 is waiting on the machine; each is waiting on work. Step 1 is the only one the machine gates.** **And finishing any of them says nothing about whether anything is *there*.**

## Language

**Canonical English, with `-ja` and `-zh` mirrors in the same directory** (suffix style, never subfolders — a subfolder changes the depth, and a changed depth breaks every relative path in the document). `tools/check_i18n.py` reads them.

**The working language of this workshop is Japanese**, which is why `HISTORY.md` and commit messages are written in it. That is a different thing from the canonical language of the documents.

## License

MIT — see [LICENSE](LICENSE).
