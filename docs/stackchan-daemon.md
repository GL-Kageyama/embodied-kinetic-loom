<!-- i18n-version: 1.2.0 | canonical: docs/stackchan-daemon.md | translated: 2026-10-18 -->

**Language:** [English](stackchan-daemon.md) | [日本語](stackchan-daemon-ja.md) | [中文](stackchan-daemon-zh.md)

# The Stack-chan daemon — start and stop

✅ **The loop and the socket are built — 2026-10-18.** `projects/stackchan/daemon/` holds a pure core (`room.py`) and the edge (`__main__.py`), and `tests/test_stackchan_daemon.py` holds twenty-four claims about them. ⛔ **Nothing is installed**: what exists is the process; what does not is anything that starts it or calls it. This page remains the design for the installation, and the lifecycle below remains a checklist.

⚠️ **What it is for.** A Claude Code hook is one process per event; `Focus` and `Companion` are one object that must live between events. The daemon is that object, plus a clock, plus a socket. It is the middle of the chain — **hooks → daemon → wire → firmware** — and it is the piece that makes the robot belong to the room rather than to a terminal that is open.

⛔ **Nothing here is installed.** No launchd job, no plist, no hook. `tools/check_i18n.py` checks the mirrors, not the design; **the process is checked in `tests/test_stackchan_daemon.py`.**

## Why the state lives on the host

⚠️ **The alternative was considered: put the phase, the gaze and the timers in the firmware, and let the wire carry events instead of gestures.** It was not chosen, and the reason is recorded here because **an omission is not neutral**.

⛔ **The two designs fork at the wire.** With the state on the host, the wire carries a **gesture**; with the state in the firmware, it carries an **event and a window's name**. **The wire as already settled carries gestures**, and 0.19.0's contract is written against that. ⇒ **Moving the state later is a protocol change, not a port.**

**What the device-side design would buy:** no resident process at all — no launchd, no socket, no lock; state that survives the Mac restarting; one body fed by several hosts; and **behavior that runs with this repository absent from the disk**.

**What it would cost, today:** a custom firmware — the most gated step in this workshop, where the restore path is unproven and the NVS zero positions have already moved once; **a second implementation of the same rules in C++, which this repository's tests cannot reach** — in a repository that calls a duplicated list a defect; a reflash for every behavior change; and debugging over a wire that does not exist yet.

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

## The wait loop

⚠️ **No polling.** The daemon waits on the listener with a timeout equal to the next deadline — `min(hold_until, idle_until, quiet_until)` — and wakes to emit the `settled` or `slept` decision exactly when it is due. **This invents no interval**: no tick constant is added to the layer.

⚠️ **One event at a time, in the order the accept loop takes them.** There is no queue and no reordering. A connection that does not deliver its line within the same 100 ms is closed; **one number, named once, used at both ends.**

⚠️ **The clock is monotonic.** The scripted times in the CLI are a different domain — seconds from a script — and the layer's contract is the same in both: `offer(session, event, at)` receives a value and never reads a clock.

## Stop, and what the body does

⛔ **On `SIGTERM` the daemon stops sending. It sends no park, no settle and no final gesture.** There is nothing safe to send: this machine has no stop command, and a gesture invented at shutdown is the one motion nobody chose.

⚠️ **The head may droop when the servos are left alone** — SCS servos release torque at idle. **That is the machine's idle behavior, not a fault**, and it was seen on the units in hand.

⚠️ **What the firmware does with the last face after the daemon stops is not settled here.** If the firmware holds it, the face stays; if the firmware's own idle takes over, it changes. That is a 0.19.0 contract, and this page does not pretend to have it.

## The device is optional

✅ **The daemon runs without a device**, and that is how it is built and tested first. The wire is opened lazily, on the first decision that would need it.

⛔ **A device error is logged and dropped, never fatal.** With `KeepAlive`, a missing device plus a fatal error would be a crash loop — **the supervisor would keep killing the thing that is supposed to be waiting.**

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

- the wire and its framing (0.19.0);
- the gesture grammar that crosses it;
- what the firmware does at idle and after a stop;
- whether a second body — a second daemon per unit — needs anything different.

## What rings, and what does not

✅ **Part of this page rings.** The pure parts are checked with no socket at all — the request schema, the refusal of an unknown key, and the decision for a given `(session, event, at)` — and the socket is checked as a real process: it answers, refuses, logs the row it returned, and exits cleanly on `SIGTERM`. **All twenty-four claims are in `tests/test_stackchan_daemon.py`.**

⛔ **What is not checked is the installation.** launchd's `RunAtLoad` and `KeepAlive`, login and logout, the plist, and the stale socket as it appears after a reboot. **That part stays a checklist**, because it is the operating system's behavior and not a function. `tools/check_i18n.py` still only confirms that the three mirrors agree.

## The checklist for the day it is installed

✅ **Six of the nine can be run without launchd, and all six are checked** — five by the test named beside them, and the eighth trivially, because nothing is ever sent.

- [ ] a second instance exits, and does not disturb the first — ✅ `test_a_second_instance_leaves_the_first_alone`;
- [ ] a stale socket is unlinked and bound; a live one is not — ✅ `test_a_stale_socket_is_unlinked_and_replaced`;
- [ ] `bootout` stops the job, and it stays stopped — ⛔ needs launchd;
- [ ] a crash restarts it; the phase begins at `present`, not where it was — ⛔ needs launchd;
- [ ] an unknown event is refused; an unknown key is refused; a client that sends a time is refused — ✅ `test_each_refusal_names_its_fault` and `test_the_prompt_cannot_ride_along`; ⚠️ **a time is not a key, so it is refused as `unknown-key`**;
- [ ] the loop wakes at the deadline, not on a tick — ✅ `test_the_next_wake_is_the_expression_and_then_the_idle_clock`;
- [ ] with no device, it waits; it does not crash-loop — ⛔ **there is no device path yet**, so there is nothing to crash on;
- [ ] on `SIGTERM`, nothing is sent — ✅ by construction: `sent` is `False` and no wire exists;
- [ ] the socket is gone after the exit — ✅ `test_the_socket_is_removed_and_the_exit_is_clean`.
