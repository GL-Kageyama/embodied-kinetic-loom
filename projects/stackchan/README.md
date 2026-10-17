<!-- i18n-version: 2.8.0 | canonical: projects/stackchan/README.md | translated: 2026-10-18 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/stackchan/ — the layer above the wire

**It decides what the robot is doing, which face it wears, what colour it glows, and which gesture it means. It does not decide how far anything moves.**

⛔ **It holds no number for machine 2, and it borrows none of machine 2's.** The scale, the zero, the sign, the envelope, the velocity ceiling, the period and the settle of the unit in hand are in no record (`docs/first-contact-stackchan.md`). ⇒ **Every gesture it chooses is a symbol with no counts behind it, and `Decision.sent` is `False` on every line.** That is the finding, not a fault.

⚠️ **This is the part of the Stack-chan route that can be verified before a line of firmware is burned.** The mapping from events to phases needs no machine measurement; the motion does. **This layer is built on the side of that line where the checks can ring.**

✅ **The four rulings of 2026-10-18 are the shape of this page:** the robot is a **companion**, not a mirror; **only transitions move the body**; the wire will carry **gesture commands**, not a 20 ms stream; and the **twelve RGB LEDs are a first-class channel, always on**.

## What it is joined to, and what it is not

✅ **It imports the Pet's `State`; it does not copy it.** The five expressions were drawn once (decision A, `projects/pet/expressions.py`), and a second set would be a second answer to the same question.

⛔ **It is not joined to a machine.** No port, no wire, no firmware, no record. Its only consumers outside the tests are its own CLI and the daemon's log. ⚠️ **It was not joined to Claude Code until 2026-10-18.** ✅ **Since then it is** — every one of the thirty-three events in `~/.claude/settings.json` runs `projects/stackchan/hook/`, and a launchd user agent starts the daemon at login. ⛔ **This directory is the layer, not the installation**: the plist here is a copy, and the record is `docs/stackchan-daemon.md`.

## The six phases

**The five faces are the Pet's; the six phases are this layer's.** A phase is what the robot is doing; a face is what it shows.

| phase | entered by | face | light | body |
|---|---|---|---|---|
| `present` | an expression expiring, or waking | `curious` | `breathe` | still |
| `greeting` | `SessionStart` | `greeting` | `warm` | `perk` |
| `working` | `UserPromptSubmit` | `curious` | `dim` | **still** |
| `blocked` | `PermissionRequest` | `curious` | `alert` | `turn` |
| `closing` | `Stop` / `StopFailure` | `happy` / `angry` | `warm` / `error` | `nod` / `flinch` |
| `resting` | no event for 90 s, or `SessionEnd` | `sleepy` | `off` | `settle` (on leaving) |

⚠️ **`working` is held up by the twenty-five events it does not express.** `PreToolUse` and `PostToolUse` are **not shown by the body, but they are received** — every one of them resets the idle clock. ⛔ **That is why the robot does not doze off during a long build.**

⚠️ **An expression has a life.** `greeting` and `closing` return to `present` after three seconds; that is a product decision, not a measurement. **A face that waits for the next event is a face that lies about how long the moment lasted.**

## The thirty-three events, in three kinds

**Thirty-three names, from the hooks reference, read 2026-10-18.** ⛔ **The names are not invented here.** A name that is not in the list raises `UnknownEvent`, so an event added upstream surfaces as an error rather than as a silent default.

⛔ **The split is not "react / do not react". It is three ways of receiving the same event.**

### Transitions — six, and they change the phase

| event | phase | why |
|---|---|---|
| `SessionStart` | `greeting` | the session has begun |
| `UserPromptSubmit` | `working` | the human's turn ended and the machine's began |
| `PermissionRequest` | `blocked` | **the one interrupt**: the machine needs a person |
| `Stop` | `closing` | the turn is over |
| `StopFailure` | `closing` | the turn died on an API error |
| `SessionEnd` | `resting` | the session is going away |

### Evidence — twelve, read but not shown

| event | why |
|---|---|
| `PreToolUse`, `PostToolUse`, `PostToolBatch` | the turn is alive; the body does not speak per tool call |
| `PostToolUseFailure` | counted; the third in a turn is the first sign of trouble |
| `PermissionDenied` | the wait has ended — a refusal is an ending |
| `Notification` | it wakes the robot and resets the idle clock; ⛔ it is not the human's answer |
| `MessageDisplay` | it has no beginning; it fires while text is displayed |
| `SubagentStart`, `SubagentStop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted` | inside the turn; the outer `Stop` is the signal |

### Ignored — fifteen, not read, still signs of life

| event | why |
|---|---|
| `Setup`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove` | the session's context changed; the body was not part of it |
| `UserPromptExpansion` | it fires immediately after `UserPromptSubmit` |
| `PreCompact`, `PostCompact`, `PreModelSwitch`, `PostModelSwitch`, `Elicitation`, `ElicitationResult` | no behaviour with numbers exists yet — ⛔ **and a word is not added before the numbers** |

⚠️ **`ignored` does not mean "not delivered".** Every one of the thirty-three resets the idle clock and wakes the robot from `resting`. **"Not expressed" is not "not seen".**

⚠️ **`no-behavior` means no behaviour *with numbers*, not no behaviour at all.** The vocabulary is a mapping, and a word that is not in it is not in the vocabulary (`references/README.md`). ⇒ **Reacting to one of these would spend a word without turning it into anything the machine can do.**

## The four channels

| channel | sound | default | what it carries |
|---|---|---|---|
| the screen | silent | always | the face — the information when you look |
| **12 RGB LEDs** | **silent** | **always** | breathing, warmth, attention, dark — **presence in peripheral vision** |
| the neck (2 axes) | servo noise | `--motion on` | **only at transitions** |
| the speaker | audible | `--sound off` | ⛔ **it does not exist yet** |

⛔ **There is no "silent mode" here, because the name would be false.** The servos are audible. **Motion and sound are two axes, not one enum**, and the face and the light obey neither — they make no noise.

✅ **The light is semantic, not RGB.** `Light` is `off`, `dim`, `breathe`, `warm`, `alert` or `error`; the mapping to twelve pixels is firmware's job, and **the LED order and colour order of this unit are in no record here.** The stock firmware exposes `set_led_color`; this layer does not call it.

## Density: transitions only

⚠️ **A gesture is chosen only at a phase transition, and the rhythm is capped by the events themselves:** one `perk` when the turn opens, one `nod` when a long turn closes — **two rhythm gestures per turn.** A `PermissionRequest` is an interrupt, not a rhythm, and is exempt from that count; **but not from the body's own floor.**

⛔ **A gesture closer than one second to the previous one is dropped, not queued** — the body field says `cooldown`, and `Companion.dropped` counts it. Two reasons: a queue would make this layer choose the gap between commands, and **on the 10/04 unit a gap shorter than about one second stalled the servos and dropped the rail** (`MOVE_SETTLE = 1.0`). ⚠️ **That 1.0 s is the one borrowed number in this package** — it is a floor from another unit, not a measurement of this one. **It is borrowed on the safe side, it is named as borrowed, and it is replaced the day this unit is measured.**

✅ **The light never waits for the body.** If the servo is in cooldown, the phase still changes and the LED still changes: **the one interrupt can lose its neck, and it cannot lose its colour.**

## Two or more windows, one room

⚠️ **VSCode can run two or more sessions at once** — two windows, or more (the author's requirement, 2026-10-18). **There is one neck and one face**, so the robot cannot show all of them — and it must not alternate among them, because every turn would land inside the one-second floor and **the neck would tremble between terminals.**

✅ **So the gaze is single and sticky** (`Focus`): **the first window to speak takes it, and a window keeps it until it goes quiet.** After 90 s of the holder's silence — the same `IDLE_SECONDS`, so no new number — the gaze is free, and the next window to speak takes it. **The rule counts nothing but whether there is one holder.**

✅ **The gaze moves to the window where the person acts** — `SessionStart` and `UserPromptSubmit` — **or where the machine needs a person** — `PermissionRequest`. ⛔ **A background window's `Stop` does not move it**: the machine finishing is not the person looking. Letting it move would swing the neck every time a background job ended.

⚠️ **The other windows are not discarded.** Their events reset the room's idle clock and are reported with the reason `distant` — **seen, alive, not this one**. ⛔ **The `sent` field is `False` there too.**

## Failure: three in a row

⚠️ **A single failed tool call is routine and is retried.** It gets `observed` and nothing else.

- **Three consecutive `PostToolUseFailure` in one turn** — with no successful `PostToolUse` between them — set `concern`: **the light turns `alert` and the face does not change.** ⛔ **Anger is not the reaction to a test failing.**
- **`angry` is reserved for `StopFailure`** — the turn died on an API error. That is the abnormal event, and it is the only one that earns the face.
- **A successful `PostToolUse` resets the count.**

## Running it

From the repository root:

```
python3 -m projects.stackchan                                   # the thirty-three, in three kinds
python3 -m projects.stackchan --event SessionStart@0 --event Stop@3
python3 -m projects.stackchan --motion off --event Stop@0.1
python3 -m projects.stackchan --sound on --event SessionStart@0
python3 -m projects.stackchan --json --event PostToolUseFailure@0
python3 -m projects.stackchan --event left:SessionStart@0 --event right:PermissionRequest@2
python3 -m projects.stackchan.daemon --socket /tmp/ekl.sock   # listen; Ctrl-C or SIGTERM stops it
echo '{"session_id": "main", "hook_event_name": "SessionStart"}' | python3 -m projects.stackchan.hook --socket /tmp/ekl.sock
```

⚠️ **A window is written `window:EVENT@seconds`; a window left unwritten is `main`, so a one-window script reads as it did before.** ⚠️ **Times are supplied in the script, not read from a clock.** The script must not run backwards; a script that does is refused. That is what makes a run reproducible — and it is why the CLI is not the thing a hook calls (see below). ⚠️ **The trace shows the light and the body on every line, and the face drawing whenever a face changes**, so a refused gesture is still readable as a reaction.

## What the hook still needs

⛔ **A Claude Code hook is one process per event. `Companion` is one object that keeps the phase, the timers and the cooldown between events.** Nothing here carries that state across processes.

⇒ **A long-lived process now exists** — `projects/stackchan/daemon/`, which holds the clock, the companion and the socket. **Its core (`room.py`) reads no clock and opens no socket; its edge (`__main__.py`) holds both alone.** ✅ **It is installed**: a launchd user agent starts it at login, and all thirty-three hook events reach it through the client. ⚠️ **A hook wired straight to this CLI would reset the phase and the idle clock on every event** — the flood it is meant to prevent, and worse: the robot would never settle or sleep.

✅ **And since the same day, the client exists** — `projects/stackchan/hook/` reads one event from standard input, sends one line, **prints nothing and exits 0 whatever happens.** ✅ **It is registered in `settings.json` for all thirty-three events.**

✅ **The client sends the event name and the window's name — and not the prompt.** The daemon stamps the time when the line arrives, so the client carries no clock and no state. The robot needs to know that a turn began, not what was said; it needs the window's name only because windows share one body. **Privacy by construction, not by policy.** ⚠️ **The start-and-stop design is `docs/stackchan-daemon.md`** — **the loop, the socket, the client, the launchd job and the registration in `settings.json` are all built and installed on this host.**

⚠️ **And the device path is missing too:** a renderer for the display, a driver for the LEDs, a sound, and **a transport**. **This layer's output is a `Decision`; nothing consumes it but the terminal and the daemon's log.**

✅ **Since 2026-10-18 the frame it would be sent in exists as source** — `engine/backend/protocol_stackchan.py` encodes and decodes one ASCII line, `schemas/stackchan-command.schema.json` is the contract both ends read, and `projects/stackchan-firmware/` parses that line and **refuses every gesture**. ⛔ **The transport has not been chosen, and the firmware has never been built or flashed.** ⚠️ **The wire carries symbols only; the first number for this machine is written after the unit is measured, not before.**

## What leaves the room

✅ **`projects/stackchan/outbound.py` turns a `Decision` into a `Frame`** — a face (or `null`), a light, and a gesture (or `null`). **It is pure, it holds no clock, and it names no machine.**

- **A frame is emitted when what the machine should show changes** — a face, a light — **or a gesture was chosen, or it is the process's first decision.** ⛔ **The first decision is always emitted, because the machine's state before it is unknown**; a face the decision does not name is filled in from the frame's own state, so the machine never has to remember what it was showing.
- ⛔ **The event's reason does not partition state changes.** A `PostToolUse` inside `blocked` returns the phase to `working` with reason `OBSERVED`, and the light may not move; a concern changes the light and not the phase. **Counting frames by event kind would have emitted frames that carried no change and missed changes that carried no transition.** So the rule reads the state, not the reason.
- ⚠️ **This is not a stream.** A hundred evidence events inside one phase produce one frame.
- **The daemon writes the frame as a row** — `{"frame": "<one ASCII line>", "sent": false, "at": …, "session": …}` — and the line is produced by the same codec the wire tests hold, **so the log cannot drift from the contract.**
- ⛔ **Nothing is sent.** The row says *would have sent*; there is no transport, no renderer and no LED driver on the other side. ✅ **On 2026-10-18 the installed daemon wrote its first frame row on a real hook event** — and ⛔ **what was observed is a line, not a movement.**

## The process that holds the room (2026-10-18)

✅ **`projects/stackchan/daemon/` is the one long-lived process.** `room.py` is the core — the request schema, the room and the next deadline — and it reads no clock, no socket and no environment. `__main__.py` is the edge, and it is the only file that opens the socket and reads `time.monotonic()`.

- **The socket is the lock.** A second instance probes it and exits with code 3 without a word to a device; a stale socket is unlinked and replaced. There is no pidfile.
- **One JSON line in, one JSON line out** — `{"session": …, "event": …}`. **An unknown key is refused**, so the prompt cannot ride along; an unknown event and a malformed line are refused with a code.
- **The daemon stamps the time.** The client sends no clock.
- **The loop waits on the socket or on the next deadline** — `min(hold_until, idle_until, quiet_until)` — and wakes to emit `settled` or `slept`. **No fixed tick.**
- **`SIGTERM` stops it**, unlinks the socket and exits 0. **Nothing is sent to a device**, because there is still no device.

**The client** is `projects/stackchan/hook/` — one process per event. It reads standard input (bounded at 1 MiB), **rebuilds exactly two fields**, sends, and closes without reading a reply. **A missing daemon is not a hook failure: exit 0, silent.** The rebuilding is `client.line_from`, which is pure and tested without a process.

✅ **Installed on 2026-10-18.** The job is `launchd/embodied-kinetic-loom.stackchan.plist` — a copy of the live one at `~/Library/LaunchAgents/` — and the client is registered for all thirty-three events. **The record, the measured behavior and the uninstall path are `docs/stackchan-daemon.md`.**

## What is checked

**`tests/test_stackchan_behaviors.py` holds thirty-four claims, `tests/test_stackchan_daemon.py` holds twenty-six, `tests/test_stackchan_hook_client.py` holds twenty-one, `tests/test_stackchan_wire.py` holds twenty-five, and `tests/test_stackchan_outbound.py` holds ten**, and they run with the rest of the suite:

- the list is 33 and none is repeated; every event has exactly one of three kinds, and the kinds partition it;
- every event carries a reason code — **there is no blank**;
- all six phases, all five faces and all six lights are reached by one script;
- a long turn nods and a short turn does not;
- three failures in a row are the first concern, a fourth is not, and success resets the count;
- `angry` is reached only through `StopFailure`;
- `PermissionRequest` is the one interrupt, and a `Notification` does not end the wait;
- **every one of the 33 events wakes the robot from `resting`** — the ignored ones included;
- an evidence event resets the idle timer;
- an expression expires and returns to `present`;
- a gesture inside the cooldown is dropped **while the light still changes**;
- motion off keeps the face and the light;
- sound is off by default and follows transitions only;
- **no gesture is ever sent** — `sent` is `False` on every line;
- **with more than one window, the first to speak takes the gaze**, a person's act in another window moves it, a tool call and a background `Stop` do not, and a background `PermissionRequest` steals it;
- **the rule does not count to two**: three windows behave by the same rule;
- the gaze is freed when the holder is quiet, when it ends, and its events keep the room awake until then;
- a script can name its windows, and every row says which one it came from;
- the reason and body sets are closed, and both are reached;
- the trace is reproducible, and a script that runs backwards is refused;
- the parser builds in three languages, and the help differs;
- **no machine-1 name, number or module is in the package** — the AST is walked for `DofRealityWire`, `Envelope`, the counts 190, 512 and 833, and any import from `engine` — and there is no `motions/` directory.

**The daemon adds twenty-six more:**

- the socket answers, and the logged row is the same row the client received;
- a second instance exits with 3 and leaves the first answering;
- a stale socket is unlinked and replaced;
- an unknown key, an unknown event and a malformed line are each refused with their own code;
- **the prompt never reaches the log** — the secret is absent from everything the daemon printed;
- a client that sends nothing is closed, and the next request still gets through;
- a clean exit removes the socket;
- the next wake is the expression first, then the idle clock, and `blocked` and `resting` have no deadline;
- **a greeting logs one frame row, and `sent` is `False` in it** — the row is decoded back into `Command(face="greeting", light="warm", gesture="perk")`;
- **an unchanged event logs no second frame.**

**The client adds twenty-one more:**

- a full hook payload yields a line with exactly `session` and `event` — **the prompt, the cwd and the tool input are not in it**;
- a payload without the two fields is dropped, and an unknown event is dropped before it reaches the socket;
- the line parses against the daemon's own schema, and fits the daemon's bound;
- **the socket path is spelled once**, and both entry points use it;
- a real payload reaches the room, and its prompt is absent from the daemon's log;
- no daemon, malformed input and an over-long input are each silent, with exit 0;
- **the client does not wait for a reply** — a listener that never answers does not delay it;
- **one daemon carries the phase across two separate processes**: a `SessionStart` in one and a `Stop` in the next read `greeting` then `closing`, though neither process held any state;
- **two windows through two clients keep one gaze**, and a background `Stop` is reported as `distant` without changing the phase.

**The wire adds twenty-five more** — the frame, its contract and the machine's end of it:

- 216 frames round-trip — **150 of them carrying no `null`** — and not one carries a number;
- a frame is one ASCII line, and a `null` field is present as a value rather than missing;
- an unknown key is refused (`prompt` cannot ride along), an unknown word is refused per field, and `light` is required and never `null`;
- the encoder refuses exactly what the decoder refuses;
- the contract, the codec and the firmware literals spell the same words, and **the firmware contains no angle for either machine**;
- the wire imports only `json` and `dataclasses`, and **imports nothing from machine 1's `protocol`**;
- the mock records what would have been sent and answers nothing.

**The outbound frame adds ten more** — what the room decides to put in front of the machine, before there is a wire:

- the first decision always emits, and fills in a face it did not name;
- a decision that changes nothing emits no frame — **a hundred evidence events produce one**;
- a change of light alone emits a frame with `face: null`, and a gesture alone emits a frame;
- every emitted frame parses against the contract and round-trips on the codec;
- **no field of a frame is a number.**

⚠️ **Not one of these claims is about the machine.** A green run says the layer computes what it was told to compute — **the same sentence `CLAUDE.md` requires for the five checks.**

## What is not here

- **No counts for machine 2.** The five gestures are candidate words, not rows in the vocabulary; a row is written the day a word becomes numbers on that machine. `projects/pet/motions/greeting.json` is machine 1's counts, and borrowing it would make this layer claim motion that will not happen.
- **No transport, and no firmware on the board.** The frame is decided and tested, and the daemon logs the line it would send — ⛔ **a line in a log is not a transport.** **The path to the board is not chosen**, and `projects/stackchan-firmware/` is source only — never built, never flashed. See `docs/first-contact-stackchan.md`.
- **No LED driver and no display renderer.** The light is a meaning; nothing turns it into pixels.
- **No sound.** `--sound on` names a channel that does not exist, and the speaker has never been verified on this unit.
- **No head-touch input.** The sensor works on this unit (observed in AI.AGENT, 2026-10-18), but it is machine input, and a firmware would have to read it. **A hook is not a head.**
- **No live installation in this directory.** The plist here is a copy, and `settings.json` is not in the repository at all; both are recorded in `docs/stackchan-daemon.md`.
- **No record.** `projects/` holds work; the record vessel is still empty, and this layer has never observed a machine.
