<!-- i18n-version: 1.18.3 | canonical: docs/stackchan-progress.md | translated: 2026-10-21 -->

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
| **1** | **Does it hear the agent?** | ✅ | **thirty-three hook events** registered in `~/.claude/settings.json`; the client rebuilds exactly `session` and `event`, prints nothing and exits 0; the daemon stamps the time and holds the room between processes. **21 + 49 tests** | — |
| **2** | **Does it know what it is doing?** | ✅ | **six phases**; transitions against evidence and ignored; a background window is `distant`; the gaze is single and sticky over **two and three windows**; a **one-second** body floor; resting after **90 s**; the **twenty-five** unexpressed events still reset the idle clock | — |
| **3** | **Does it have a face?** | ✅ | **five faces** from the Pet's own drawing; **twelve LEDs**, always on; **thirteen pixel tests** on the vendor's skin; ⚠️ **an eye was shown the two work lights on 2026-10-20 and named two colours — 「青、紫」**; a frame whose four fields carry words and no numbers | — |
| **4** | **Does it move?** | ✅ | the pose line at about **50 poses a second**; **five postures** placed by the author's eye; **822 poses applied** in the engine-driven run; the firmware writes the stock's call (`kPoseTimeMs = 20`, `kPoseSpeed = 0`). ⚠️ **The landing is six to eight counts short on yaw and one to three on pitch — not a constant.** ✅ **And since 0.19.36 the floor is measured, one goal at a time** (`bench set`, torque on, the board printing `held at`): yaw asked **4 / 8 / 12 / 20 / 40** counts moved **0·0 / 0·2 / 6·5 / 13·13 / 34·33** (+ and −); pitch up **1 / 5 / 9 / 18 / 38** and down **5 / 6 / 12 / 20 / 40** — ⛔ **downward there is no floor: gravity supplies the motion** | — |
| **5** | **Does it sound?** | ✅ | **four words**, a closed set, and the author heard all four; on 2026-10-19 the ear judged the set quiet and **`fall` smaller than the other three** — the boot volume moved from −18 dB to −10 dB, and `fall`'s amplitude alone from 0.22 to 0.34; the author heard it again and said 「OK」. ⛔ **The tones are still choices, not measurements** | — |
| **6** | **Does it move with the event, not after it?** | ✅ | **one `at`** for the frame and the pose line; a streamed frame carries `gesture: null`; seen moving from a hook event, and judged 「滑らかだった」. **19 of 23, 17 of 23, 16 of 23 and 68 of 79** poses were applied late — **lateness is the schedule's, smoothness is the eye's** | — |
| **7** | **Can the host know where the head is?** | ⚠️ | **The query is built and bounded** — `bench pos` at each gesture, on the fd it is about to stream on, read under `PORT_WAIT = 0.5`; **nineteen tests** hold the parser (`projects/stackchan/neck/readback.py`). **Measured on the unit on 2026-10-19: the console answers, and sometimes answers with no position.** It answered `{"position": null, "heard": true}` while `bench scan` found **0 id(s)**, and ⛔ **the board's own boot log dates the silence before the query** (`servo: ping yaw=0/3 pitch=0/3`). ✅ **Then the rail answered**: `bench power off`, three seconds, `bench power on` brought both ids back, and the servos read **5.1 V, 31–32 °C, load 0** — ⇒ **the silence is a state the servos hold, and the rail is the switch that clears it**; since 0.19.31 boot throws it itself, for the measured **3,000 ms**, and since 0.19.34 a watchdog pings both ids every **5 s** and cycles the rail on three silences in a row — told when the console is using the bus (0.19.35). ✅ **A position was read** (`[28, 487]`), and a later run had **17 of 17** probes answered. ⛔ **Answering is not guaranteed**: the bus silences itself with nothing being asked, one bounded move returned it to silence, and the board's `ConsoleTask` does not read STDIN while a gesture or a sound plays — a line written then is merged or lost. ✅ **Since 0.19.33 a swallowed query is asked once more and the text the board sent is kept**; 0.19.37 added the third spelling `pose: refused`; 0.19.38 reads the board's own verdict (`pose: N applied, M refused, K clamped`); 0.19.39 puts a blank line before every frame; and 0.19.41 reads a frame's acceptance from the board's own line, on the fd that wrote it (`accepted: true`, `false`, or `null` — ⛔ **not a refusal**). ✅ **The read-back measured gestures end to end** — `look_up` moved 0 / 43 / 228 counts from three different starts, `look_side` 71 and 228 — ⚠️ **the postures are absolute, so a gesture does different things from different places** — and since 0.19.36 a plan that asks for nothing or falls inside the servo's measured floor is not streamed. ⛔ **`applied` is lines taken, not a posture reached**, and **a recovery is not a diagnosis** — the trigger is still unnamed. **The dated chain is `HISTORY.md`, 0.19.23–0.19.41.** | **an answer that keeps coming back** — the rail cycle returns the bus, the board now throws it by itself within seconds of a silence, and the reading has to survive a move; ⛔ **answering once is not the rung** |
| **8** | **Can it be lived with, day after day?** | ⛔ | **the hour is in the code since 0.19.25** — 21:00–06:00 closes the sound field and nothing else, **thirty-three tests** — and ✅ **since 0.19.26 the installed job names `--sound on`**, so the day has a voice; ✅ **and since 0.19.28 the log has an instrument** — `projects/stackchan/day/`, **twenty-five tests**, whose first reading counted **3,852 lines, 11 starts, 3,599 decisions, 124 frames and 24 read-backs**; ⛔ **that is what the body did, not how it was lived**; ✅ **and on 2026-10-19 the first day is written down** — `2026-10-19-the-sounds.md`: the author's one line 「たまに音が鳴っていた」, and the day's numbers quoted inside it as evidence — ⛔ **one day is not "day after day"** | **a day, written down** |

## Where the climb stands

**Six of the eight are ✅, one is ⚠️, and one is ⛔ — measured 2026-10-19.** ⛔ **That is not "six-eighths of a coding agent":** the rows are questions, not weights, and the question below the table has no instrument at all.

**Rung 5 closed on 2026-10-19, and the instrument was an ear.** ✅ **The ear compared one word against the others**, not a tone against anything: at the vendor's −18 dB the author said 「少し小さい」, and at −10 dB named the small one — **`fall`, the only word that ends on 440 Hz**. ⇒ **The boot volume is −10 dB, `fall`'s amplitude alone is 0.34 (the other three stay at 0.22), and the author said 「OK」.** ⚠️ **That is a judgement of loudness balance** — ⛔ **the four shapes remain choices, with no measurement behind any of them.**

**Rung 7 is built, and it stopped at the machine.** ✅ **The code side is closed**: the daemon asks the board for the position at each gesture, on the fd it is about to stream on, and reads under `PORT_WAIT = 0.5`. ✅ **The rail answered** — `bench power off`, three seconds, `bench power on` — and **one position came back** (`[28, 487]`). ⛔ **The row stays ⚠️ because an answer is not the rung**: the bus silences itself with nothing asked, `heard: false` is explained by `ConsoleTask` not reading while a gesture or a sound runs, and a frame's delivery is the board's line to give. ✅ **A silence is now noticed, cleared and printed by the firmware** — ⛔ **and that is not the same as one not happening.**

**Row 8 needs time, not code — and the one code-shaped part of it landed on 2026-10-19.** ⚠️ **Until 0.19.25 the only way to keep the night quiet was `--sound off`**, which keeps the day quiet too; ⇒ **the hour is now a rule** (`projects/stackchan/quiet.py`, thirty-three tests). ✅ **At 05:27 that morning the installed job was switched to `--sound on`**, and ✅ **the first day was written down** — one sentence from the author, the day's numbers quoted inside it. ⛔ **The row stays ⛔: one day is not "day after day", and the ear did not say which of the 97 sounds it caught.** ⚠️ **Not one restart in that day's log says why it happened.**

## What is not on this climb

⏸ **Machine 1, the DOF Reality box, is not a rung of this climb.** The owner parked it on 2026-10-19 — 「DOFは忘れて。もう、かなりしばらく繋がない」 — and **a coding agent's body does not need a three-axis rig.** The serial layer waits in `docs/construction-memo.md`, row 1, **and it waits without blocking anything here.**

⛔ **The agent itself is not on this climb either.** Its judgement, its memory and its choices are the session's; **this page measures only the body that session wears.**

## What this table cannot say

- ⛔ **It cannot say the body is good** — only that the mechanism computes what it was told to compute.
- ⛔ **It cannot say anything is there.** The goal's one record (`projects/stackchan-firmware/records/2026-10-19-something-is-there.md`) is one sentence, at N=1, and ⚠️ **the sentence had been offered a moment before.**
- ⛔ **It cannot be turned into a percentage**, and it must not be read as one.
- ⚠️ **It cannot say the eight questions are the right eight.** They are the ones the work has actually asked so far — **a ninth is added when something needs it, not before.**

**What was counted for this page:** the states of eight rows, the tests and records cited in them, and one source per row. **What was not counted:** anything in the room while the body is working — **that is row 8, and it now holds one sentence from the author and one day's numbers.**
