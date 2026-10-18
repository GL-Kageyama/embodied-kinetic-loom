<!-- i18n-version: 1.0.0 | canonical: docs/stackchan-progress.md | translated: 2026-10-19 -->

**Language:** [English](stackchan-progress.md) | [日本語](stackchan-progress-ja.md) | [中文](stackchan-progress-zh.md)

# The climb — a progress table toward a coding agent's body

⛔ **This page is a map, not a record.** Every line of it is derivable from a source elsewhere in the repository; when a source changes, this page is the one that is wrong. **Read it to find where the climb stands, never to learn what happened.**

**What is being built — and what is not.** ⛔ **The agent is not built here.** The agent is Claude Code, running in a session; **this repository builds the body it wears** — a face, a voice, twelve lights and a neck. ⛔ **No code here calls an LLM**, and the `Motion Intent` is written in the session, by Claude, guided by the skill. ⇒ **What can be checked here is the body's mechanism, not the agent's judgement.**

⚠️ **Two words, never mixed.** **The mechanism is verified** — trajectories, limits, protocols, deadlines. **The goal is not verified** — for it, only records of observation remain (`docs/verification-boundary.md`). ⇒ **A ✅ in this table says a mechanism runs. It says nothing about whether anything is there.**

## How to read a row

| mark | meaning |
|---|---|
| ✅ | built, and a named instrument measured it |
| ⚠️ | built, and not judged — the mechanism runs, and nobody has said it is right |
| ⛔ | not built |

⚠️ **Each row names what was counted and what was not.** **A row whose state moves depending on where you cut it does not belong in this table.**

## The eight questions

| # | the question | state | what was measured | what would close it |
|---|---|---|---|---|
| **1** | **Does it hear the agent?** | ✅ | **thirty-three hook events** registered in `~/.claude/settings.json`; the client rebuilds exactly `session` and `event`, prints nothing and exits 0; the daemon stamps the time and holds the room between processes. **21 + 35 tests** | — |
| **2** | **Does it know what it is doing?** | ✅ | **six phases**; transitions against evidence and ignored; a background window is `distant`; the gaze is single and sticky over **two and three windows**; a **one-second** body floor; resting after **90 s**; the **twenty-five** unexpressed events still reset the idle clock | — |
| **3** | **Does it have a face?** | ✅ | **five faces** from the Pet's own drawing; **twelve LEDs**, always on; **nine pixel tests** on the vendor's skin; a frame whose four fields carry words and no numbers | — |
| **4** | **Does it move?** | ✅ | the pose line at about **50 poses a second**; **five postures** placed by the author's eye; **822 poses applied** in the engine-driven run; the firmware writes the stock's call (`kPoseTimeMs = 20`, `kPoseSpeed = 0`). ⚠️ **The landing is six to eight counts short on yaw and one to three on pitch — not a constant** | — |
| **5** | **Does it sound?** | ⚠️ | **four words**, a closed set; the board played all four, and the author heard all four. ⛔ **Not one was compared** — the tones are choices, not measurements | **the author's ear**, one word at a time |
| **6** | **Does it move with the event, not after it?** | ✅ | **one `at`** for the frame and the pose line; a streamed frame carries `gesture: null`; seen moving from a hook event, and judged 「滑らかだった」. **19 of 23, 17 of 23, 16 of 23 and 68 of 79** poses were applied late — **lateness is the schedule's, smoothness is the eye's** | — |
| **7** | **Can the host know where the head is?** | ⛔ | **nothing.** The daemon reads nothing back; **the first transition after a start is not streamed**; every motion starts from the last pose actually written, not from a measurement; `sent: true` means the host's tty took the line | **a bounded, non-blocking read** of the port the stream already holds — then the first transition can be streamed and a start can be measured |
| **8** | **Can it be lived with, day after day?** | ⛔ | **nothing.** Sound is off by default; no hour is named in the code; and no one has written down a day — **how often the body is right, wrong, or unnoticed** | **a day, written down** |

## Where the climb stands

**Five of the eight are ✅, one is ⚠️, and two are ⛔ — measured 2026-10-19.** ⛔ **That is not "five-eighths of a coding agent":** the rows are questions, not weights, and the question below the table has no instrument at all.

**The next rung is 7**, and it is the only missing one that code alone can close. It is also a named defect, not a wish: **the first transition after a daemon start is left to the board because the host does not know where the head is** (`projects/stackchan-firmware/records/2026-10-19-the-join.md`). ✅ **The board already prints the number** — `pose: stream started — goals on the present positions (yaw 504, pitch 780), torque on`. ⚠️ **The risk is the port**: a stream holds it for one gesture, each write is bounded by `PORT_WAIT = 0.5`, and an open/write/close loop was measured wedging the daemon inside `open()` on 2026-10-19. **A read must be bounded and non-blocking, or it repeats that day.**

**Row 8 needs time, not code.** ⛔ **No table writes it; only days do** — and a day is not something this repository can run on its own.

## What is not on this climb

⏸ **Machine 1, the DOF Reality box, is not a rung of this climb.** The owner parked it on 2026-10-19 — 「DOFは忘れて。もう、かなりしばらく繋がない」 — and **a coding agent's body does not need a three-axis rig.** The serial layer waits in `docs/construction-memo.md`, row 1, **and it waits without blocking anything here.**

⛔ **The agent itself is not on this climb either.** Its judgement, its memory and its choices are the session's; **this page measures only the body that session wears.**

## What this table cannot say

- ⛔ **It cannot say the body is good** — only that the mechanism computes what it was told to compute.
- ⛔ **It cannot say anything is there.** The goal's one record (`projects/stackchan-firmware/records/2026-10-19-something-is-there.md`) is one sentence, at N=1, and ⚠️ **the sentence had been offered a moment before.**
- ⛔ **It cannot be turned into a percentage**, and it must not be read as one.
- ⚠️ **It cannot say the eight questions are the right eight.** They are the ones the work has actually asked so far — **a ninth is added when something needs it, not before.**

**What was counted for this page:** the states of eight rows, the tests and records cited in them, and one source per row. **What was not counted:** anything in the room while the body is working — **that is row 8, and it is empty.**
