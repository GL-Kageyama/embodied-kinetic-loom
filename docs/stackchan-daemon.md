<!-- i18n-version: 1.23.0 | canonical: docs/stackchan-daemon.md | translated: 2026-10-19 -->

**Language:** [English](stackchan-daemon.md) | [日本語](stackchan-daemon-ja.md) | [中文](stackchan-daemon-zh.md)

# The Stack-chan daemon — start and stop

✅ **The loop, the socket and the client are built — 2026-10-18.** `projects/stackchan/daemon/` holds a pure core (`room.py`) and the edge (`__main__.py`), `projects/stackchan/hook/` holds the client a hook runs, and `tests/test_stackchan_daemon.py` holds forty-one claims about the first while `tests/test_stackchan_hook_client.py` holds twenty-one about the second. ✅ **And since the same day it is installed** — a launchd user agent starts the daemon at login, and all thirty-three hook events call the client. **The installation is a place on one host, not a property of the repository** (see [The installation, as it stands](#the-installation-as-it-stands)).

⚠️ **What it is for.** A Claude Code hook is one process per event; `Focus` and `Companion` are one object that must live between events. The daemon is that object, plus a clock, plus a socket. It is the middle of the chain — **hooks → daemon → wire → firmware** — and it is the piece that makes the robot belong to the room rather than to a terminal that is open.

✅ **It is installed on one host, and the repository holds a copy of the job, not the job itself.** `projects/stackchan/launchd/embodied-kinetic-loom.stackchan.plist` is the file, and it names this host in two absolute paths; the live copy is at `~/Library/LaunchAgents/`. ⛔ **A plist in this repository is not a running daemon** — installation is `launchctl bootstrap`, and uninstallation is the reverse. `tools/check_i18n.py` checks the mirrors, not the design; **the two processes are checked in `tests/test_stackchan_daemon.py` and `tests/test_stackchan_hook_client.py`, and nothing checks the installation.**

## Why the state lives on the host

⚠️ **The alternative was considered: put the phase, the gaze and the timers in the firmware, and let the wire carry events instead of gestures.** It was not chosen, and the reason is recorded here because **an omission is not neutral**.

⛔ **The two designs fork at the wire.** With the state on the host, the wire carries a **gesture**; with the state in the firmware, it carries an **event and a window's name**. **The wire as already settled carries gestures**, and 0.19.0's contract is written against that. ⇒ **Moving the state later is a protocol change, not a port.**

**What the device-side design would buy:** no resident process at all — no launchd, no socket, no lock; state that survives the Mac restarting; one body fed by several hosts; and **behavior that runs with this repository absent from the disk**.

**What it would cost, today:** a custom firmware — the most gated step in this workshop, where the restore path has now been written, read back and watched booting, though the NVS zero positions have already moved once; **a second implementation of the same rules in C++, which this repository's tests cannot reach** — in a repository that calls a duplicated list a defect; a reflash for every behavior change; and debugging over a wire that does not exist yet.

⚠️ **What the device-side design is often assumed to buy, and does not:** a robot that keeps working when the host disappears. **A dead daemon is already not a runaway robot** — nothing streams, and the firmware owns the idle. The robot returns to its own behavior either way. What is genuinely lost with the state on the host is narrower: **the repository must exist on disk**, and **the phase does not survive a daemon restart**.

⚠️ **This decision is reopened if one of these becomes a requirement:** behavior with this repository absent; state across a host restart; several hosts feeding one body; or no resident process at all. **None of them is a requirement today.**

## Start and stop are not the machine's start and stop

⚠️ **The firmware's idle behavior is its own.** The daemon adds decisions; it does not own the body. ⇒ **Starting the daemon does not start the robot, and stopping it does not park the robot.** This matters because machine 1's protocol has no stop command, and machine 2's has not been established here at all.

⛔ **A dead daemon is not a runaway robot**, and that is a property of the gesture-command design: nothing streams. The last thing the firmware was told was one gesture, and the firmware owns its beginning and its end. When the daemon dies, nothing keeps arriving.

## The lifecycle

| state | entered by | what is true |
|---|---|---|
| `stopped` | before login, after `bootout`, after a clean exit | no socket, no state |
| `starting` | launchd, or a manual run | the socket is bound; **nothing has been sent** |
| `ready` | the bind succeeds | the loop waits on the socket and on the next deadline |
| `stopping` | `SIGTERM` or `SIGINT` | no new events; close; exit 0 |
| `stopped` | the exit | the socket is unlinked |

⚠️ **There is no persistence.** The phase, the timers, the gaze and the failure count all begin again at `present`. **A restarted daemon does not resume**: the next transition re-establishes the phase. The cost is named: if it restarts in the middle of a turn, the robot shows `present` until the next transition, even though the turn is still running.

⚠️ **Startup sends no greeting.** The first motion comes from the first event, not from the daemon being alive. **A hello is motion for the machine's sake** — the same rule that keeps the body still during `working`.

## Who starts it — launchd, not the hook

✅ **A macOS user agent** (`LaunchAgents`) with `RunAtLoad` and `KeepAlive`. Three reasons:

- **login start**: the user opens nothing, which is the requirement that put this page here;
- **restart on crash**: a socket client cannot do that;
- **one owner**: the lifecycle lives in one place, not spread across hooks.

⛔ **The hook does not spawn the daemon.** A hook that spawns is a supervisor with no memory: two events arriving together race, and a daemon started from a hook inherits that hook's environment. **The hook is a messenger, not a supervisor.**

⚠️ **Socket activation alone is not enough**, although launchd can do it: the robot must go to sleep when events stop, and **sleeping needs a live process to notice the deadline**. The daemon stays alive and waits.

⚠️ **The label is `embodied-kinetic-loom.stackchan`** — a string, not a domain; no reverse-DNS is invented for it. The job runs with `WorkingDirectory` set to the repository root and an absolute interpreter, because launchd starts jobs with no working directory of its own.

## One instance, and the stale socket

⚠️ **The socket is the lock.** Its path is `/tmp/ekl-stackchan-<uid>.sock`, set to mode `0600` after the bind, because a socket file takes the process umask. The short path is not cosmetic: `sun_path` is 104 bytes on macOS, and `$TMPDIR` under `/var/folders/…` is close enough to that limit to break on a long user name.

⚠️ **Startup probes before it binds:** connect to the path first. If the connect succeeds, **another daemon is alive, and this process exits without a word to the device.** If it fails with `ECONNREFUSED` or `ENOENT`, the path is stale — unlink it, then bind.

⛔ **No pidfile.** A pidfile can be stale and cannot be probed; a socket can answer. **One lock, not two.**

## What the hook sends

**One JSON line per event:**

```
{"session": "<session_id>", "event": "<hook_event_name>"}
```

⛔ **The prompt is not in the message, and the schema refuses keys it does not know.** A field that is merely ignored can ride along; a field that is refused cannot. **Privacy by construction, not by policy.**

⚠️ **The client does not send a time. The daemon stamps one when the line arrives**, from a monotonic clock. Two reasons: the client is a messenger with no state, and a wall clock that steps backwards is a lie the layer refuses. **The time in a `Decision` is the daemon's, not the hook's.**

⚠️ **The client waits 100 ms and, on any failure, exits 0 silently.** A hook must not block a turn, and must not turn the robot into an error. **A missed event is dropped, not queued**: an event delivered late is a lie about when it happened, and the next event repairs the phase. The idle clock repairs the rest.

⚠️ **The cost, named:** if the daemon is down at `SessionStart`, there is no greeting, and the robot shows `present` until the next transition. If it is down at `SessionEnd`, the robot sleeps on the idle timer instead. Both are visible in the trace, and neither is an error.

✅ **The client itself now exists** — `projects/stackchan/hook/`, one process per event. It reads standard input (bounded at 1 MiB), rebuilds exactly `session` and `event` so the prompt cannot ride along, sends the line, **does not read the reply**, prints nothing and exits 0 on every failure. **A missing daemon is not a hook failure.** ✅ **Since 2026-10-18 it has a caller: every one of the thirty-three events in `~/.claude/settings.json` runs it** (see [The installation, as it stands](#the-installation-as-it-stands)).

## The wait loop

⚠️ **No polling.** The daemon waits on the listener with a timeout equal to the next deadline — `min(hold_until, idle_until, quiet_until)` — and wakes to emit the `settled` or `slept` decision exactly when it is due. **This invents no interval**: no tick constant is added to the layer.

⚠️ **One event at a time, in the order the accept loop takes them.** There is no queue and no reordering. A connection that does not deliver its line within the same 100 ms is closed; **one number, named once, used at both ends.**

⚠️ **The clock is monotonic.** The scripted times in the CLI are a different domain — seconds from a script — and the layer's contract is the same in both: `offer(session, event, at)` receives a value and never reads a clock.

## The neck, in the same loop (0.19.14)

✅ **A transition that chooses a gesture now moves the neck too, and the daemon is what writes the pose line.** It holds **one `Stream`** — the pure rule in `projects/stackchan/neck/stream.py`, the same one the CLI edge follows — and the wait is on **the earlier of the room's deadline and the neck's next sample**.

- ⛔ **No child process and no second clock.** The pose line comes out of the same loop that answers the socket, from the same monotonic time that stamped the event. **The author chose this shape on 2026-10-19** (「デーモンが自前のループで流す（推奨）」).
- ⛔ **The frame carries `gesture: null` while a gesture is streamed.** The board's `PlayGesture` blocks its main loop for seconds, and the pose lines written meanwhile are applied late — **one happening must not move the head twice.** ⚠️ **The log row and the client's reply still name the gesture**; the field that disappears is the one on the wire.
- ✅ **Since 0.19.36 a plan that asks for nothing is not streamed.** Two questions are asked of the samples, not of the endpoints: `gestures.still` — every sample equals the first — and `gestures.within_floor` — the plan's whole excursion is inside the servo's measured floor (yaw **8 counts**, pitch **4 counts upward**, ⛔ **none downward: gravity supplies that motion**). **The gesture is still consumed**, the row says `"skipped": "no motion"`, and **the frame carries `gesture: null`**, so `PlayGesture` never runs for a posture the head already holds. ⚠️ **`still` looks at the samples because the endpoints lie**: `nod` begins and ends in `look_up` and dips to pitch 30 in between. ⛔ **The floor is a measurement, not a number of the board's**: `bench set`, one goal at a time, 2026-10-19 — yaw asked 4 / 8 / 12 / 20 / 40 counts moved **0·0 / 0·2 / 6·5 / 13·13 / 34·33**, pitch up **1 / 5 / 9 / 18 / 38** and down **5 / 6 / 12 / 20 / 40**.
- ✅ **Since 0.19.23 the host asks the board where the head is** — before every gesture it writes `bench pos` on the same fd it will stream from, and reads the answer under the same `PORT_WAIT = 0.5`. ⚠️ **The pose it reads is the start**, so the first transition after a start is streamed when the console answers. ⛔ **It asks only at the gesture, never on a clock**: a query every few seconds would cut into a `bench` line being typed into the same console — **the console is the human's too.**
- ⛔ **If the console does not answer, nothing is invented.** The start falls back to the last pose actually written, then to the table's end pose of a gesture the board played; with neither, **the first gesture is left to the frame.**
- ⛔ **The log keeps two failures apart.** `{"position": null, "heard": false}` is a silent console; `{"position": null, "heard": true}` is a console that answered `yaw=no answer` — **the servos were silent.**
- ✅ **Since 0.19.33 an unanswered probe also keeps what arrived.** The row carries `"read"` — the last 160 characters the board sent in that window — because ⛔ **`heard: false` alone could not tell a silent console from a line that was merged with the one before it.** Measured the same day, the text was `console: unknown command` and `frame: refused (malformed)`: the query had gone into a line the board refused. ⇒ **The cause is on the board's side of the line** — `ConsoleTask` calls `HandleFrame`, and inside it `sound::play` and `PlayGesture` **inline**, so **while a gesture or a sound runs the console does not read STDIN**. ✅ **A swallowed query is asked once more**, inside the same `PORT_WAIT` — and in a measured run 8 of 8 probes were heard, against 7 of 13 `heard: false` before the change. ⛔ **Frames are damaged the same way**, and the host cannot see it.
- ✅ **Since 0.19.37 the re-ask knows the third spelling.** `pose: refused` — the line the board prints when it will not take a pose line, and the shape of **all three** probes that still came back empty that day (`at=22397.9`, `24989.5`, `25330.7`). ⛔ **Until then the rule matched only `console: unknown command` and `frame: refused`, so the re-ask had never fired for it.** ⚠️ **The code is not folded away**: `(malformed)`, `(too-long)`, `(no-answer)` and `(write-failed)` all stay in `read`, so a re-ask never erases which one it was.
- ✅ **Measured on the unit, 2026-10-19:** the query was written, the board answered it (`{"position": null, "heard": true}`), `bench pos` printed `yaw=no answer pitch=no answer`, and `bench scan` found **0 id(s)**. ⇒ **The path is measured; a position from this machine is not.** The servo bus answered nothing, and ⛔ **no code here can supply that.**
- ⚠️ **Every gesture still falls back to the last pose actually written** — the plan's end when the plan finished, and wherever the head had got to when it was interrupted. ⛔ **The planned end is not evidence that the head arrived there.**
- ⚠️ **A short write stops the stream** and logs `sent: false`. The next gesture starts again from the last pose that was written.
- ⚠️ **The only thing read back is the position query.** The board's other printing is not listened to — so *the poses were written to the console* is still the whole of what the log can say. ⛔ **Whether the head moved is an observation, and it has not been made through this path.**

## Stop, and what the body does

⛔ **On `SIGTERM` the daemon stops sending. It sends no park, no settle and no final gesture.** There is nothing safe to send: this machine has no stop command, and a gesture invented at shutdown is the one motion nobody chose.

⚠️ **The head may droop when the servos are left alone** — SCS servos release torque at idle. **That is the machine's idle behavior, not a fault**, and it was seen on the units in hand.

⚠️ **What the firmware does with the last face after the daemon stops is not settled here.** If the firmware holds it, the face stays; if the firmware's own idle takes over, it changes. ⛔ **The 0.19.0 contract does not settle it either** — it carries `face: null` for *do not change*, and says nothing about what a board does when no line arrives.

## The device is optional

✅ **The daemon runs without a device**, and that is still the default: with no `--port` it encodes the frame and writes it only as a line in its log. ✅ **Since 2026-10-18 it can also write that line to the board's console**, and the installed job does — see [The transport](#the-transport).

⛔ **A device error is logged and dropped, never fatal.** With `KeepAlive`, a missing device plus a fatal error would be a crash loop — **the supervisor would keep killing the thing that is supposed to be waiting.** ⚠️ **A path that does not exist is that case, and it is the common one**: the console's name changes across a replug, so the row says `sent: false` and the room answers the event anyway.

## The frame it writes, and — given a port — sends

✅ **Since 0.19.1 every decision passes through `projects/stackchan/outbound.py`**, and when the frame is not `None` the daemon writes it as a row:

```
{"frame": "{\"face\":null,\"gesture\":null,\"light\":\"breathe\",\"sound\":null}", "sent": false, "at": 6497.584270416, "session": "…"}
```

- **A frame is written when what the machine should show changes** — a face, a light — **or a gesture was chosen, or a sound is named, or it is the process's first decision.** ✅ **The fourth key arrived in 0.19.13** and is required: `null` means *this frame is silent*, ⛔ **not *keep the last one*.** **A sound is an event and a gesture is an event; the face and the light are state**, and only the state is remembered between frames.
- ⚠️ **The sound is off by default** (`--sound on|off`), the author's decision: installing this must not make a machine speak without being asked. ✅ **Since 0.19.26 the installed job names `--sound on`** — the author asked on 2026-10-19 — so the daytime speaks and the night does not; ⛔ **the job names no hour**, because the hour belongs in `quiet.py` and nowhere else. ✅ **And since 0.19.25 it has an hour as well as a switch**: `projects/stackchan/quiet.py` says whether this hour is 21:00–05:00, the edge reads the wall clock once per event, and `Room.offer(..., quiet=True)` closes the `sound` field alone — ⛔ **the face, the light and the neck are untouched, and the core still reads no clock.** ⚠️ **The boundaries are whole hours:** 20:59 is day, 21:00 is quiet, 05:00 is day again. ⛔ **With the switch off the key is still written, as `null`** — the frame is the same shape either way, and the board never has to infer why nothing played. ⛔ **The first decision is always emitted, because the state of the machine before it is unknown**; the face is filled in from the frame's own state, so the machine never has to remember what it was showing.
- ⛔ **The event's reason does not partition state changes**, and the rule reads the state rather than the reason. A `PostToolUse` inside `blocked` returns to `working` with reason `OBSERVED` while the light may not move; a concern changes the light and not the phase.
- ⚠️ **This is not a stream.** In the observed run, a `PreToolUse` that followed the first frame wrote no second row.
- **The line is the codec's** — `engine/backend/protocol_stackchan.py`, the same one `tests/test_stackchan_wire.py` holds — so **the log cannot drift from `schemas/stackchan-command.schema.json`.**
- ✅ **Since 0.19.28 the log has a reader** — `python3 -m projects.stackchan.day <path>` counts what is in it: lines, starts, decisions, frames and whether each was sent, streamed gestures with planned/applied/late/held, read-backs with **heard** and **positions** counted apart, and the words of every frame that reached the port. **The core takes lines and reads no file and no clock** (`day/summary.py`, seventeen tests); **the edge opens one path, and that path has no default** — the installed job names the log once, and a second spelling would be the one that goes stale. **Measured at 05:36 on 2026-10-19: 3,852 lines, 11 starts, 3,599 decisions, 124 frames (every one `sent: true`), 48 streams — 1,564 poses planned, 1,518 applied, 1,316 late, 1,256 held — 24 read-backs of which 12 were heard and 0 carried a position, and two sounds (`hello`, `chime`).** ⛔ **The reader counts a restart and cannot say why**: eleven starts in 113 minutes, and not one line in stderr.
- ⛔ **A line in a log is not a wire**, and ⛔ **it is not a record of motion either** — that requirement is stated in `CLAUDE.md`, and its shape was decided on the day there was something to put in it. ✅ **Since 2026-10-18 the same line is also written to a port when one is named, and one encoding feeds both** — the log row and the bytes on the wire come from a single call to the codec.

## The transport

✅ **Decided and measured on 2026-10-18.** `--port PATH` names the board's console. With it, the line of every frame row is also written to that path, so `bench` and `idf.py` still own the port whenever the room is quiet. ⚠️ **The shape of the write is two shapes, and a hang split them on 2026-10-19.** **A frame is still one `os.open`, one `os.write`, one `os.close`, and no port held between frames.** ⛔ **A pose stream cannot be written that way** — at 50 Hz a loop of open/write/close wedged the daemon inside `open()`, where a signal could not reach it — so since 0.19.15 **a stream opens the port once, holds it for the length of one gesture, and closes it at the summary.**

- ⛔ **The wedge was measured, not supposed.** On 2026-10-19 the installed daemon stopped answering: `ps` showed state `U`, and `sample` put the thread inside `open()`. It reproduced two ways — a loop of open/write/close blocked at the fourth or fifth `open()`, and a non-blocking writer that never closed pushed 68 lines (about 1 KB) through before `EAGAIN` whenever the board stopped draining. ⇒ **the host may not open this console repeatedly, and the board may stop draining; neither is announced.** ⚠️ **The board was silent until the author took the cable out and put it back**; afterwards its own console answered again.
- **Every write of a stream is bounded** — `PORT_WAIT = 0.5`. A write that cannot finish in half a second ends the stream and is logged as `{"neck": …, "sent": false, "at": …}`; a port that cannot be opened at all leaves the gesture to the board (`gesture` stays in the frame) and the room carries on. **A stream holds nothing after its summary.**
- ✅ **Delivery is the board's sentence.** On 2026-10-19 the stream was replayed on the unit with a reader attached while the daemon wrote. The board printed `pose: stream started — goals on the present positions (yaw 504, pitch 780), torque on`, then, after the silence, `pose: stream lost after 500 ms — torque released` and `pose: 23 applied, 0 refused, 0 clamped`. **The daemon's own summary for that gesture was `{"neck": "look_side", "applied": 23, "late": 19, "held": 29}`.** ⛔ **19 of the 23 were applied late** — the board's main loop was still inside the previous gesture — and **whether the head visibly moved is not yet written down.**
- **`sent` is `true` only when `os.write` returned the full length.** ⛔ **That means the host's tty accepted the bytes. It does not mean the board received them**, and on this day those two claims were apart for an hour: a row saying `sent: true` sat in the log while nothing on the machine answered.
- ⚠️ **Delivery is proven by the board, not by the row.** It was proven once, on 2026-10-18, by reading the console with `os.open` and raw `termios` while the daemon wrote:

```
frame: light=warm face=greeting (no renderer yet)
frame: gesture perk refused — no gesture -> angle table exists
```

  ⇒ **the daemon's log carried `{"face":"greeting","gesture":"perk","light":"warm"}` with `"sent": true`, and the board printed the same words.** ⛔ **The gesture was refused that day — `command_frame.cpp` refused every gesture until an angle was measured, which it was later the same day — and the refusal did not stop the light.** ⚠️ **The word in that log is the one the protocol carried then**: `perk` became `look_up` when the author renamed all five gestures later on 2026-10-18 (`projects/stackchan-firmware/records/2026-10-18-the-gestures.md`). ⚠️ **Those two lines predate the fourth key**, so neither carries `sound`; a frame written after 0.19.13 always does.
- ⚠️ **The path is not an identity.** On one board it read `/dev/cu.usbmodem1101` before a hang and `/dev/cu.usbmodem101` after one replug, sixteen minutes apart. The installed plist names the second; **a replug may name a third, and the daemon will log `sent: false` and carry on.** ⇒ **the plist's port is the one thing about this installation that a cable can invalidate.**
- ⛔ **Nothing here queues a line, and that is also the limit**: a frame written while another program holds the port is logged as unsent, and a stream that cannot write stops rather than waits. **The room answers the event either way.**
- ⚠️ **A reader that asserts DTR and RTS is a reset.** A `pyserial` open of this console reset the board mid-boot, and the ROM stopped answering until the cable went out and back in; **the daemon's own `os.open` path, run alone, did neither.** To watch this console, use `os.open` and raw `termios`.
- ⛔ **Two writers can merge, and the board sees one line.** Measured 2026-10-19 while the installed daemon was running: a `bench scan` written from a second `os.open` produced `frame: refused (malformed)` on the console and no scan at all; the same command 0.3 s later scanned normally. ⚠️ **The mechanism is not established** — neither write reported an error — **but the only line the board refuses as malformed is one that begins with `{`**, and the only writer of such a line is the daemon. ⇒ **the console is shared time, not shared safely: an out-of-band query can split a frame, and the frame is lost without either side noticing.** ⛔ **The daemon's own `bench pos` avoids this by using the fd it is about to stream on, not by taking a lock.**

⚠️ **What no check covers:** the seven port tests open a *regular file*, not a device. ⛔ **No test opens a port**, a missing path is tested as `sent: false` and not as a device error, and the measured delivery above is one observation on one host.

## Decided, and not decided

**Decided here:**

- launchd user agent, `RunAtLoad` and `KeepAlive`; label `embodied-kinetic-loom.stackchan`;
- `/tmp/ekl-stackchan-<uid>.sock`, mode `0600`, probe then bind, no pidfile;
- daemon-stamped monotonic time; no client time;
- one JSON line, unknown keys refused, the prompt structurally absent;
- 100 ms client wait, drop on failure, no queue;
- wait on the next deadline; no fixed tick;
- no hello, no park, no persistence;
- the device link is optional and never fatal.

**Not decided here:**

- ✅ **The framing is decided (0.19.0) and this page still does not own it** — one ASCII JSON line, `face` / `light` / `gesture` / `sound`, in `schemas/stackchan-command.schema.json`, encoded by `engine/backend/protocol_stackchan.py`. ✅ **Since 0.19.1 the daemon calls that codec and writes the line it would send.** ✅ **Since 0.19.8 the transport is decided as well: the daemon writes that line to the board's console, one open per frame, and the installed plist names the path** (see [The transport](#the-transport)). ✅ **And since later that same day `projects/stackchan-firmware/` plays the gesture it receives** — five postures measured on the unit — **so a frame carrying a gesture moves the head** (`projects/stackchan-firmware/records/2026-10-18-the-gestures.md`); ✅ **and since 0.19.11 the engine drives it smoothly enough that the author accepted the motion** — `projects/stackchan/neck/`, after the firmware's write was changed to the stock's own call (`records/2026-10-18-the-neck.md`);
- what the firmware does at idle and after a stop;
- whether a second body — a second daemon per unit — needs anything different.

## The installation, as it stands

**Measured on 2026-10-18, on the author's Mac (uid 501).** This is a record of what was done and what was seen — not a design, and not a test.

- **The job.** `~/Library/LaunchAgents/embodied-kinetic-loom.stackchan.plist`, bootstrapped into `gui/501/embodied-kinetic-loom.stackchan`. `RunAtLoad` and `KeepAlive` are true; the interpreter is absolute (`/opt/homebrew/bin/python3`) and `WorkingDirectory` is the repository root. **The copy in `projects/stackchan/launchd/` is the same file.**
- **The socket.** `/tmp/ekl-stackchan-501.sock`, mode `0600`, owned by the user. The daemon's first log line is `{"daemon": "listening", …}` in `/tmp/ekl-stackchan-daemon.log`.
- **The caller.** `~/.claude/settings.json` carries a `hooks` key: each of the thirty-three event names maps to one command — `cd "<repository root>" && /opt/homebrew/bin/python3 -m projects.stackchan.hook`. ⛔ **The command names this host's path**, the same limit as the plist. ⚠️ **That file also holds the user's credentials, so it is not copied here**; this page records the shape, not the file.
- **One frame row, observed (2026-10-18, after 0.19.1).** The daemon was restarted onto the new code with `launchctl kickstart -k`, a real hook event arrived, and the log gained exactly one frame row — `face: null`, `light: breathe` — carrying `"sent": false`. **The `PreToolUse` that followed wrote no second frame**, because the state had not changed. ⛔ **What was observed is a line in a log, not a movement.**
- **One end-to-end run, observed.** A nested `claude -p` session produced five rows in the daemon's log: `SessionStart` → `greeting`; `UserPromptSubmit` → `working`, the body held by the one-second floor; `MessageDisplay` → `observed`; `Stop` → `closing`; `SessionEnd` → `resting` with `settle`. **Every row read `sent: false`.** ⚠️ **That is the whole chain — a real hook, a process per event, one room — and it says nothing about a robot**, because there is no wire.
- **The port, named (2026-10-18).** The plist passes `--port /dev/cu.usbmodem101`, and the installed job writes each frame to the board's console. **The first frame of this repository's to arrive at a machine through a transport, with both ends observed, is quoted in [The transport](#the-transport).** ⛔ **The path read `/dev/cu.usbmodem1101` before a replug and `/dev/cu.usbmodem101` after it**; when the path goes missing the row says `sent: false` and nothing else changes.
- **Stopping.** `launchctl bootout gui/501/embodied-kinetic-loom.stackchan` stops the job and the socket disappears. ⚠️ **A `SIGTERM` does not**, because `KeepAlive` is true: launchd scheduled a restart (`state = spawn scheduled`, `last exit code = 0`) and the daemon was back about ten seconds later. **The stop is `bootout`; a kill is a restart.** ⚠️ **That throttle is a deaf window** — an event arriving inside it is dropped, by the client's own design.

**To remove it:**

```
launchctl bootout gui/501/embodied-kinetic-loom.stackchan
rm ~/Library/LaunchAgents/embodied-kinetic-loom.stackchan.plist
rm -f /tmp/ekl-stackchan-501.sock /tmp/ekl-stackchan-daemon.log /tmp/ekl-stackchan-daemon.err
```

and remove the `hooks` key from `~/.claude/settings.json`. ⚠️ **Nothing else is touched**: the daemon writes only the socket and those two logs, and **with no `--port` it sends nothing to a machine; with one, it writes a single line to that path and nothing else.**

## What rings, and what does not

✅ **Part of this page rings.** The pure parts are checked with no socket at all — the request schema, the refusal of an unknown key, and the decision for a given `(session, event, at)` — and the socket is checked as a real process: it answers, refuses, logs the row it returned, and exits cleanly on `SIGTERM`. **All forty-one claims are in `tests/test_stackchan_daemon.py`** — two being that a greeting writes one frame row with `sent: false`, and that an unchanged event writes none; **seven of them are about the port** — that the configured path receives the logged line, that a missing path is `sent: false` and not a refusal, that with no port nothing is written, that a write returning short is not `sent`, **that one stream opens the port once rather than once per pose, that a port which takes nothing ends the stream instead of waiting, and that a port which cannot be opened leaves the gesture in the frame for the board to play**; **and two are about the neck** — that the second transition streams poses from where the first one ended while its frame carries `gesture: null`, and that the first transition streams nothing at all; **and two since 0.19.36** — that a plan which asks for nothing is not streamed, and that neither is one inside the measured floor, both consuming the gesture with a `"skipped": "no motion"` row. ⛔ **Those seven open a regular file, not a device.** ✅ **Twenty-one more hold the client** — that a payload's prompt, cwd and tool input never reach the line, that an unknown event is dropped before the socket, that the path is spelled once, and that a listener which never answers does not delay it — **in `tests/test_stackchan_hook_client.py`.**

⛔ **No test checks the installation.** launchd's `RunAtLoad` and `KeepAlive`, login and logout, the plist, and the stale socket as it appears after a reboot are the operating system's behavior, not a function. ✅ **What exists instead is one observation, written above**: on 2026-10-18 the installed job ran a real hook chain end to end and was stopped and restarted by hand. ⚠️ **An observation on one host is not a check** — it does not run again, and it does not fail when it should. `tools/check_i18n.py` still only confirms that the three mirrors agree.

## The checklist for the day it is installed

✅ **Seven of the nine are checked by tests; two more were observed by hand on 2026-10-18.** ⚠️ **One of the seven is checked only for a missing path** — a device that exists and then fails is still unmeasured.

- [x] a second instance exits, and does not disturb the first — ✅ `test_a_second_instance_leaves_the_first_alone`; **also run by hand: exit 3**;
- [x] a stale socket is unlinked and bound; a live one is not — ✅ `test_a_stale_socket_is_unlinked_and_replaced`;
- [x] `bootout` stops the job, and it stays stopped — ✅ **observed 2026-10-18**: the socket was gone. ⚠️ **Stays stopped only until something bootstraps it again**;
- [x] a crash restarts it; the phase begins at `present`, not where it was — ⚠️ **half-measured**: the restart was observed after a clean exit, not a crash, and the ~10 s throttle is launchd's. **The phase began at `present` as designed, because there is no persistence**;
- [x] an unknown event is refused; an unknown key is refused; a client that sends a time is refused — ✅ `test_each_refusal_names_its_fault` and `test_the_prompt_cannot_ride_along`; ⚠️ **a time is not a key, so it is refused as `unknown-key`**;
- [x] the loop wakes at the deadline, not on a tick — ✅ `test_the_next_wake_is_the_expression_and_then_the_idle_clock`;
- [x] with no device, it waits; it does not crash-loop — ✅ **a missing path is a `sent: false` row and the room keeps answering** (`test_a_missing_port_is_not_a_refusal`); ⚠️ **a path that exists and then fails was not measured** — no device error has been produced on purpose;
- [x] on `SIGTERM`, nothing is sent — ✅ by construction: the stop path emits no frame, so there is nothing to write with or without a port; observed in the log;
- [x] the socket is gone after the exit — ✅ `test_the_socket_is_removed_and_the_exit_is_clean`; **also observed after `bootout`**.

⚠️ **And one that is not on the list because it needs a reboot:** the stale socket as it appears after the Mac restarts. ⛔ **No reboot was done on 2026-10-18**, so the probe-then-bind path has been tested against a hand-made stale socket and against nothing else.
