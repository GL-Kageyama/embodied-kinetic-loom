<!-- i18n-version: 1.2.0 | canonical: docs/stackchan-progress.md | translated: 2026-10-19 -->

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
| **5** | **Does it sound?** | ✅ | **four words**, a closed set, and the author heard all four; on 2026-10-19 the ear judged the set quiet and **`fall` smaller than the other three** — the boot volume moved from −18 dB to −10 dB, and `fall`'s amplitude alone from 0.22 to 0.34; the author heard it again and said 「OK」. ⛔ **The tones are still choices, not measurements** | — |
| **6** | **Does it move with the event, not after it?** | ✅ | **one `at`** for the frame and the pose line; a streamed frame carries `gesture: null`; seen moving from a hook event, and judged 「滑らかだった」. **19 of 23, 17 of 23, 16 of 23 and 68 of 79** poses were applied late — **lateness is the schedule's, smoothness is the eye's** | — |
| **7** | **Can the host know where the head is?** | ⚠️ | **the query is built and bounded** — `bench pos` at each gesture on the streaming fd, read under `PORT_WAIT = 0.5`, ten tests; measured on the unit on 2026-10-19: **the console answered** (`{"position": null, "heard": true}`), and `bench pos` printed `yaw=no answer` while `bench scan` found **0 id(s)**. ⛔ **No position has been read from this machine** — the servo bus is silent. Every motion still starts from the last pose actually written when the answer carries no position | **one answer from the servo bus** — a power switch, a cable, or an id; then the same path returns a pose, and ⛔ **nothing in the code needs to change for it** |
| **8** | **Can it be lived with, day after day?** | ⛔ | **nothing.** Sound is off by default; no hour is named in the code; and no one has written down a day — **how often the body is right, wrong, or unnoticed** | **a day, written down** |

## Where the climb stands

**Six of the eight are ✅, one is ⚠️, and one is ⛔ — measured 2026-10-19.** ⛔ **That is not "six-eighths of a coding agent":** the rows are questions, not weights, and the question below the table has no instrument at all.

**Rung 5 closed on 2026-10-19, and the instrument was an ear.** ✅ **What the ear did was compare one word against the others**, not a tone against anything: the author heard all four at the vendor's −18 dB and said 「少し小さい」; at `bench volume 90` — −10 dB — the author said that one of the four was small, and named it: **`fall`, the only word that ends on 440 Hz**, the lowest note of the set. ⇒ **The boot volume is now −10 dB and `fall`'s amplitude alone is 0.34 (the other three stay at 0.22)**, and the author heard it again and said 「OK」. ⚠️ **That is a judgement of loudness balance, and it is the judgement this row was waiting for** — ⛔ **the four shapes remain choices, and no measurement stands behind a single one of them.**

**Rung 7 is built, and it stopped at the machine.** ✅ **The code side is closed**: the daemon asks the board for the position at each gesture, on the fd it is about to stream on, and reads the answer under `PORT_WAIT = 0.5` — the bounded read this table asked for (`projects/stackchan/neck/readback.py`, ten tests). ✅ **Measured on the unit on 2026-10-19**: the query was written and the console answered — but the answer was `yaw=no answer pitch=no answer`, and `bench scan` found **0 id(s)**, before and after `bench power on`. ⇒ **The path is measured; the position is not, and no code here can produce it.** ⛔ **The row stays ⚠️ until one pose comes back from the servo bus.**

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
