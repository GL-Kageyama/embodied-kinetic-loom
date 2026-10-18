<!-- i18n-version: 2.17.0 | canonical: projects/stackchan/README.md | translated: 2026-10-19 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/stackchan/ — the layer above the wire

**It decides what the robot is doing, which face it wears, what colour it glows, and which gesture it means. It does not decide how far anything moves.**

⛔ **It holds no number for machine 2, and it borrows none of machine 2's.** The zero, the sign and the envelope of the unit in hand are not in this package. ⇒ **Every gesture it chooses is a word, and the counts a word becomes live with the machine** — `projects/stackchan-firmware/main/main.cpp`, measured on the unit on 2026-10-18 (`projects/stackchan-firmware/records/2026-10-18-the-gestures.md`). `Decision.sent` is `True` only when a port is named and the host's tty took the whole line.

⚠️ **This is the part of the Stack-chan route that can be verified before a line of firmware is burned.** The mapping from events to phases needs no machine measurement; the motion does. **This layer is built on the side of that line where the checks can ring.**

✅ **The four rulings of 2026-10-18 are the shape of this page:** the robot is a **companion**, not a mirror; **only transitions move the body**; the wire will carry **gesture commands**, not a 20 ms stream; and the **twelve RGB LEDs are a first-class channel, always on**.

## What it is joined to, and what it is not

✅ **It imports the Pet's `State`; it does not copy it.** The five expressions were drawn once (decision A, `projects/pet/expressions.py`), and a second set would be a second answer to the same question.

✅ **It is joined to a machine since 2026-10-18** — the daemon writes one line per frame to the board's console — **and it was not joined before that.** ⛔ **The join runs one way and carries one line**: this layer opens nothing itself, ⚠️ **reads back exactly one thing since 0.19.23 — the answer to `bench pos`, asked at a gesture** — and can otherwise confirm only that the host's tty took the whole line. Its consumers outside the tests are its own CLI, the daemon's log, and the port the daemon names. ⚠️ **It was not joined to Claude Code until 2026-10-18.** ✅ **Since then it is** — every one of the thirty-three events in `~/.claude/settings.json` runs `projects/stackchan/hook/`, and a launchd user agent starts the daemon at login. ⛔ **This directory is the layer, not the installation**: the plist here is a copy, and the record is `docs/stackchan-daemon.md`.

## The six phases

**The five faces are the Pet's; the six phases are this layer's.** A phase is what the robot is doing; a face is what it shows.

| phase | entered by | face | light | body |
|---|---|---|---|---|
| `present` | an expression expiring, or waking | `curious` | `breathe` | still |
| `greeting` | `SessionStart` | `greeting` | `warm` | `look_up` |
| `working` | `UserPromptSubmit` | `curious` | `dim` | **still** |
| `blocked` | `PermissionRequest` | `curious` | `alert` | `look_side` |
| `closing` | `Stop` / `StopFailure` | `happy` / `angry` | `warm` / `error` | `nod` / `recoil` |
| `resting` | no event for 90 s, or `SessionEnd` | `sleepy` | `off` | `rest` (on leaving) |

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
| the speaker | audible | `--sound off` | **one word at four of the six transitions** — `hello`, `pip`, `chime`, `fall`; the board plays it. ⚠️ **And 21:00–05:00 close it even when the switch is on** |

⛔ **There is no "silent mode" here, because the name would be false.** The servos are audible. **Motion and sound are two axes, not one enum**, and the face and the light obey neither — they make no noise.

✅ **Since 2026-10-19 the speaker has an hour as well as a switch.** `projects/stackchan/quiet.py` answers one question — **is this hour between 21:00 and 05:00?** — and the daemon reads the wall clock once per event and passes the answer down as a value (`Room.offer(..., quiet=)`). ⛔ **The core still reads no clock.** ⚠️ **Quiet closes the sound field and nothing else**: the face, the light and the neck are unchanged — **being silent is not being absent.** ⚠️ **The boundaries are whole hours and minutes are not carried**: 20:59 is day, 21:00 is quiet, 05:00 is day again. ✅ **And since 0.19.26 the installed job names `--sound on`** — the author asked — so the daytime speaks and the night does not; ⛔ **the job names no hour**, because the hour lives in `quiet.py` alone.

✅ **The light is semantic, not RGB.** `Light` is `off`, `dim`, `breathe`, `warm`, `alert` or `error`; the mapping to twelve pixels is firmware's job, and **the LED order and colour order of this unit are in no record here.** The stock firmware exposes `set_led_color`; this layer does not call it.

## Density: transitions only

⚠️ **A gesture is chosen only at a phase transition, and the rhythm is capped by the events themselves:** one `look_up` when the turn opens, one `nod` when a long turn closes — **two rhythm gestures per turn.** A `PermissionRequest` is an interrupt, not a rhythm, and is exempt from that count; **but not from the body's own floor.**

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

## The neck, moved by the engine (0.19.10)

✅ **`projects/stackchan/neck/` is the first host in this repository that writes the pose line.** `motion.py` is pure: two poses and a duration go in, and `engine/trajectory` samples come out encoded by the wire's own encoder. `__main__.py` is the edge: it follows each sample's own time with absolute deadlines and writes one line per tick through `os.open`/`os.write`/`os.close`, the same path the daemon uses.

```
python3 -m projects.stackchan.neck --dry-run --start 80 500 --end 350 500 --duration 1.3
python3 -m projects.stackchan.neck --port /dev/cu.usbmodem101 \
    --start 80 500 --end 350 500 --duration 1.3 --period 0.02 --hold 0.8
```

⛔ **The two endpoints are named on the command line, in tenths of a degree, and that is on purpose**: the measured postures are the board's (`main/main.cpp`), and the package still holds no number for machine 2. **The pose line carries numbers; the transition frame does not.** This module writes the first, and the daemon writes the second.

⚠️ **The duration is a real constraint, but the number changed on 0.19.11.** Until then this paragraph said the servo follows at about 40°/s — that was `speed=100`, **a cap the firmware was writing, not the servo's ceiling.** **Measured against the stock's own call (`time=20, speed=0`) on 2026-10-18: 112 counts (35°) in under 200 ms, about 175°/s.** ✅ **The firmware now writes the stock's call, and a reference may peak up to the servo's own limit — about `degrees / 93`.** The seven segments below were replayed at about `degrees / 60` (peak ≈112°/s). ⛔ **No test here can see any of it** — the tests have no servo.

✅ **Measured on the unit the same day: seven segments, 822 poses applied, 0 refused, 0 clamped**, a 47° move ending one count from its target. ✅ **And after the firmware's write changed, the same seven segments at one-third the length: 228 poses, 0 late, 410 applied on the board (228 plus 182 held), 0 refused, 0 clamped — and the author's judgement is 「かなり良い。これでOKだと思う。」** (`projects/stackchan-firmware/records/2026-10-18-the-neck.md`). What is tested is the mechanism: `tests/test_stackchan_neck.py`, forty tests.

### The join, since 0.19.14 — one event moves all of it

✅ **A hook transition now moves the face, the lights and the neck.** The daemon holds **one `Stream` inside its own `select` loop** — no child process, no second clock — and streams the pose line for the same event from the same `at` that the frame was stamped with. ⛔ **The frame that event emits carries `gesture: null`**: the board's `PlayGesture` blocks its main loop for seconds, and the poses written meanwhile are applied late — **one happening must not move the head twice.** ⚠️ **The log row and the client's reply still name the gesture the layer chose**; what is gone is the field on the wire.

- **The five postures are a copy of the board's table** (`neck/gestures.py`), and the copy is held by a check that reads `main/main.cpp`: a table that moves turns the test red. ⛔ **The order of the source of truth did not change** — the machine is the source, this is the copy.
- **`nod` is two segments chained on one timeline.** ⛔ **Two samples at the seam would stop the head for one tick**, and that is the shape the author called 「動きが硬い」.
- ✅ **Since 0.19.23 the host asks the board where the head is** — at each gesture, on the same fd it is about to stream on, it writes one line `bench pos` and reads the answer back under the same `PORT_WAIT = 0.5`. ⚠️ **The pose it reads is the start** — so the first transition after a start is streamed too, whenever the console answers. ⛔ **Asked at the moment of a gesture and never on a schedule**: a periodic query would cut into a `bench` line being typed on the same console — **the console is also the human's.**
- ⛔ **When the console does not answer, nothing is invented.** The start falls back to the last pose actually written, then to the end pose of the table's gesture the board would play; with neither, **the first gesture is left to the frame.**
- ⛔ **The log keeps two failures apart.** `{"position": null, "heard": false}` is a silent console; `{"position": null, "heard": true}` is a console that answered `yaw=no answer` — **the servos were silent.**
- ✅ **Measured on the unit, 2026-10-19:** the query was written and the board answered it (`{"position": null, "heard": true}`), `bench pos` printed `yaw=no answer pitch=no answer`, and `bench scan` found **0 id(s)**. ⇒ **The path is measured; a position from this machine is not.** The servo bus answered nothing, and ⛔ **no code here can supply that.**
- **Every later motion still starts from the last pose actually written**, not from the previous plan's end — an interrupted plan ends somewhere other than where it aimed.
- ⛔ **A short write stops the stream**, and the row says `sent: false`. The next gesture starts again from the last pose that was written.
- ⛔ **The stream holds the port for one gesture, not for one pose** (0.19.15). A frame is still one `os.open`/`os.write`/`os.close` with nothing held between frames; **a stream opens the port once, writes each pose under a `PORT_WAIT = 0.5` bound, and closes it at the summary.** ⚠️ **The first shape was measured to wedge the daemon**: at 50 Hz, open/write/close blocked inside `open()` at the fourth or fifth attempt, where no signal could reach it. **A port that takes nothing ends the stream; a port that cannot be opened leaves the gesture in the frame for the board.**

⚠️ **The mechanism is measured once on the unit, and then the eye arrived.** On 2026-10-19 the stream was replayed live with a reader attached to the console. The board printed `pose: stream started — goals on the present positions (yaw 504, pitch 780), torque on`, then after the silence `pose: stream lost after 500 ms — torque released` and `pose: 23 applied, 0 refused, 0 clamped`; the daemon's summary for that gesture was `{"neck": "look_side", "applied": 23, "late": 19, "held": 29}`. ⛔ **19 of the 23 were applied late** — the board's main loop still held the previous gesture. ✅ **Later the same day, with the installed daemon running, the author said 「さっき首が動いていたよ」** — the neck had moved from a hook event. **The record is `projects/stackchan-firmware/records/2026-10-19-the-join.md`**, and ⛔ **which of the two streamed gestures in those minutes the eye caught is not established by it.**

## What the hook still needs

⛔ **A Claude Code hook is one process per event. `Companion` is one object that keeps the phase, the timers and the cooldown between events.** Nothing here carries that state across processes.

⇒ **A long-lived process now exists** — `projects/stackchan/daemon/`, which holds the clock, the companion and the socket. **Its core (`room.py`) reads no clock and opens no socket; its edge (`__main__.py`) holds both alone.** ✅ **It is installed**: a launchd user agent starts it at login, and all thirty-three hook events reach it through the client. ⚠️ **A hook wired straight to this CLI would reset the phase and the idle clock on every event** — the flood it is meant to prevent, and worse: the robot would never settle or sleep.

✅ **And since the same day, the client exists** — `projects/stackchan/hook/` reads one event from standard input, sends one line, **prints nothing and exits 0 whatever happens.** ✅ **It is registered in `settings.json` for all thirty-three events.**

✅ **The client sends the event name and the window's name — and not the prompt.** The daemon stamps the time when the line arrives, so the client carries no clock and no state. The robot needs to know that a turn began, not what was said; it needs the window's name only because windows share one body. **Privacy by construction, not by policy.** ⚠️ **The start-and-stop design is `docs/stackchan-daemon.md`** — **the loop, the socket, the client, the launchd job and the registration in `settings.json` are all built and installed on this host.**

✅ **And the device path is no longer missing a part:** the LEDs have a driver, the display a renderer since 0.19.12, the speaker a voice since 0.19.13, and the transport is chosen — all beneath this package, in `projects/stackchan-firmware/`. **This layer's output is a `Decision`; its consumers are the terminal, the daemon, and — through the daemon, one line per frame — the board.**

✅ **Since 2026-10-18 the frame it would be sent in exists as source** — `engine/backend/protocol_stackchan.py` encodes and decodes one ASCII line, and `schemas/stackchan-command.schema.json` is the contract both ends read. ✅ **The transport is chosen and connected** — `--port`, one line per frame, the port named in the installed plist. ✅ **And the board acts on the gesture word**: `projects/stackchan-firmware/` carries five postures measured on the unit (`projects/stackchan-firmware/records/2026-10-18-the-gestures.md`). ✅ **Since 0.19.13 the fourth field carries a word too** — `sound`, from the closed set of four — and the board turns it into tones (`records/2026-10-18-the-voice.md`). ⛔ **The wire still carries no number from this layer** — the words go out, and the machine turns them into counts.

## What leaves the room

✅ **`projects/stackchan/outbound.py` turns a `Decision` into a `Frame`** — a face (or `null`), a light, a gesture (or `null`), and a sound (or `null`). **It is pure, it holds no clock, and it names no machine.**

- **A frame is emitted when what the machine should show changes** — a face, a light — **or a gesture was chosen, or a sound is named, or it is the process's first decision.** ⛔ **A sound is an event and not a state**: the light is remembered and re-sent, a sound is not, and `null` in that field means *this frame is silent*. ⛔ **The first decision is always emitted, because the machine's state before it is unknown**; a face the decision does not name is filled in from the frame's own state, so the machine never has to remember what it was showing.
- ⛔ **The event's reason does not partition state changes.** A `PostToolUse` inside `blocked` returns the phase to `working` with reason `OBSERVED`, and the light may not move; a concern changes the light and not the phase. **Counting frames by event kind would have emitted frames that carried no change and missed changes that carried no transition.** So the rule reads the state, not the reason.
- ⚠️ **This is not a stream.** A hundred evidence events inside one phase produce one frame.
- **The daemon writes the frame as a row** — `{"frame": "<one ASCII line>", "sent": false, "at": …, "session": …}` — and the line is produced by the same codec the wire tests hold, **so the log cannot drift from the contract.**
- ✅ **It is sent whenever the job names a port** — the same line is written to the port, and `sent` says whether the host's tty took it. ⛔ **`sent: true` is about the host's tty, not about the board receiving it**: delivery was proven once, by the board's own console printing the frame. ✅ **The display has had a renderer on the other side since 0.19.12** — the board draws the vendor's face from the frame's word — and ⛔ **what is still true is that this layer never paints it.** ✅ **On 2026-10-18 the installed daemon wrote its first frame row on a real hook event** — and ⛔ **what was observed is a line, not a movement.**

## The process that holds the room (2026-10-18)

✅ **`projects/stackchan/daemon/` is the one long-lived process.** `room.py` is the core — the request schema, the room and the next deadline — and it reads no clock, no socket and no environment. `__main__.py` is the edge, and it is the only file that opens the socket and reads `time.monotonic()`.

- **The socket is the lock.** A second instance probes it and exits with code 3 without a word to a device; a stale socket is unlinked and replaced. There is no pidfile.
- **One JSON line in, one JSON line out** — `{"session": …, "event": …}`. **An unknown key is refused**, so the prompt cannot ride along; an unknown event and a malformed line are refused with a code.
- **The daemon stamps the time.** The client sends no clock.
- **The loop waits on the socket or on the next deadline** — `min(hold_until, idle_until, quiet_until)` — and wakes to emit `settled` or `slept`. **No fixed tick.**
- **`SIGTERM` stops it**, unlinks the socket and exits 0. ⛔ **Sending nothing is not a stop command**: a frame is one `os.open`/`os.write`/`os.close`, and what releases the board's torque is 500 ms of silence, not a word from here.

**The client** is `projects/stackchan/hook/` — one process per event. It reads standard input (bounded at 1 MiB), **rebuilds exactly two fields**, sends, and closes without reading a reply. **A missing daemon is not a hook failure: exit 0, silent.** The rebuilding is `client.line_from`, which is pure and tested without a process.

✅ **Installed on 2026-10-18.** The job is `launchd/embodied-kinetic-loom.stackchan.plist` — a copy of the live one at `~/Library/LaunchAgents/` — and the client is registered for all thirty-three events. **The record, the measured behavior and the uninstall path are `docs/stackchan-daemon.md`.**

## What is checked

**`tests/test_stackchan_behaviors.py` holds thirty-five claims, `tests/test_stackchan_daemon.py` holds thirty-six, `tests/test_stackchan_hook_client.py` holds twenty-one, `tests/test_stackchan_wire.py` holds twenty-eight, `tests/test_stackchan_outbound.py` holds thirteen, `tests/test_stackchan_neck.py` holds forty, and `tests/test_stackchan_readback.py` holds ten**, and they run with the rest of the suite:

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
- sound is off by default, and carries one word on four of the six transitions — the other two are silent;
- **21:00–05:00 close the sound field even with the switch on**, and leave the face, the light and the neck untouched;
- every sound word the layer can choose is one the wire's closed set names;
- **no gesture is ever sent** — `sent` is `False` on every line;
- **with more than one window, the first to speak takes the gaze**, a person's act in another window moves it, a tool call and a background `Stop` do not, and a background `PermissionRequest` steals it;
- **the rule does not count to two**: three windows behave by the same rule;
- the gaze is freed when the holder is quiet, when it ends, and its events keep the room awake until then;
- a script can name its windows, and every row says which one it came from;
- the reason and body sets are closed, and both are reached;
- the trace is reproducible, and a script that runs backwards is refused;
- the parser builds in three languages, and the help differs;
- **no machine-1 name, number or module is in the package** — the AST is walked for `DofRealityWire`, `Envelope`, the counts 190, 512 and 833, and any import from `engine` — and there is no `motions/` directory.

**The daemon adds thirty-five more:**

- the socket answers, and the logged row is the same row the client received;
- a second instance exits with 3 and leaves the first answering;
- a stale socket is unlinked and replaced;
- an unknown key, an unknown event and a malformed line are each refused with their own code;
- **the prompt never reaches the log** — the secret is absent from everything the daemon printed;
- a client that sends nothing is closed, and the next request still gets through;
- a clean exit removes the socket;
- the next wake is the expression first, then the idle clock, and `blocked` and `resting` have no deadline;
- **a greeting logs one frame row, and `sent` is `False` in it** — the row is decoded back into `Command(face="greeting", light="warm", gesture="look_up")`;
- **an unchanged event logs no second frame**;
- **the second transition streams the pose line from the pose the first one ended at, and the frames carry `look_up` then `null`** — every written pose line decodes, and the log's `neck` row names `look_side` with at least five poses;
- **a console that does not answer is written to and not believed** — the query reaches the port, `heard` is `False`, and the first gesture is left to the frame;
- **a console that answers with a position is streamed from it** — the first transition, and the row records the measured pose;
- **a console that answers without one is still an answer** — the row says `heard: true` and `position: null`, which is not the same as silence;
- **one stream opens the port once**, not once per pose;
- **a port that takes nothing ends the stream** instead of waiting, and the row says `sent: false`;
- **a port that cannot be opened leaves the gesture in the frame**, for the board to play.

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

**The wire adds twenty-eight more** — the frame, its contract and the machine's end of it:

- 1,080 frames round-trip — **125 of them carrying no `null`** — and not one carries a number;
- a frame is one ASCII line, and a `null` field is present as a value rather than missing;
- an unknown key is refused (`prompt` cannot ride along), an unknown word is refused per field, and `light` is required and never `null`;
- **`sound` is required, may be `null`, and its values are the four words** — `null` is *this frame is silent*, not *keep the last one*;
- the encoder refuses exactly what the decoder refuses;
- the contract, the codec and the firmware literals spell the same words, and **the firmware contains no angle for either machine**;
- the wire imports only `json` and `dataclasses`, and **imports nothing from machine 1's `protocol`**;
- the mock records what would have been sent and answers nothing.

**The outbound frame adds thirteen more** — what the room decides to put in front of the machine, before there is a wire:

- the first decision always emits, and fills in a face it did not name;
- a decision that changes nothing emits no frame — **a hundred evidence events produce one**;
- a change of light alone emits a frame with `face: null`, and a gesture alone emits a frame;
- **a sound alone emits a frame, and the frame is not repeated** — `Outbound` remembers no sound, where it remembers the light;
- each transition carries its own word, and two are silent;
- every emitted frame parses against the contract and round-trips on the codec;
- **no field of a frame is a number.**

⚠️ **Not one of these claims is about the machine.** A green run says the layer computes what it was told to compute — **the same sentence `CLAUDE.md` requires for the five checks.**

## What is not here

- **No counts for machine 2.** The five gestures are words; the counts they become live with the machine (`projects/stackchan-firmware/main/main.cpp`, measured 2026-10-18), never in this package. `projects/pet/motions/greeting.json` is machine 1's counts, and borrowing it would make this layer claim motion that will not happen. ⚠️ **`neck/` receives two poses as arguments** — the caller names them, and the package stores none.
- **No frame carrying a number.** ✅ **The transport exists and the board acts on a frame**, but what crosses is words — a face, a light, a gesture. **No count from the layer above the wire reaches it.** ⚠️ **The pose line does carry numbers, and since 0.19.10 `neck/` writes it** — with both endpoints supplied by the caller, never chosen here.
- **No display renderer, and no LED driver in this package.** ✅ **The twelve LEDs have a driver, and it is the firmware's** (`projects/stackchan-firmware/main/leds.cpp`) — this layer sends the word `warm` and never a pixel. ✅ **The display has one since 0.19.12, and it is the firmware's** (`display.cpp`, `face_bitmap.cpp`): this package sends the word, and never a pixel.
- **No frequency and no tone table.** ✅ **The speaker exists since 0.19.13** — `--sound on` lets the layer name one of four words, and the firmware's `sound.cpp` turns a word into tones. ⛔ **The tones are choices, not measurements**, and the word-to-tone mapping is the board's: this package selects a word and never a waveform.
- **No head-touch input.** The sensor works on this unit (observed in AI.AGENT, 2026-10-18), but it is machine input, and a firmware would have to read it. **A hook is not a head.**
- **No live installation in this directory.** The plist here is a copy, and `settings.json` is not in the repository at all; both are recorded in `docs/stackchan-daemon.md`.
- **No record in this directory.** `projects/` holds work, and since 2026-10-18 it holds three records — all under `projects/stackchan-firmware/records/` — but **none of them is this layer observing a machine**: they record what a session saw while driving the firmware from its console.
