<!-- i18n-version: 1.1.0 | canonical: projects/stackchan-firmware/records/2026-10-19-the-sounds.md | translated: 2026-10-19 -->

**Language:** [English](2026-10-19-the-sounds.md) | [日本語](2026-10-19-the-sounds-ja.md) | [中文](2026-10-19-the-sounds-zh.md)

# The sounds — 2026-10-19

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A count with no ear behind it is a log in a record's clothes.

**What was counted.** One unit, one pair of ears, one room, and the installed daemon's own log from `03:48:43` to `17:10:45` JST — the cut the author chose when they asked for the day. **What was not counted:** how many of the sounds the ear caught, which ones, at what hour, whether the author was in the room for any particular one, and whether anything is there behind them.

## What was heard

**The author was asked what happened today, and answered in one line:**

> たまに音が鳴っていた

— occasionally, a sound was playing. ⚠️ **That is the whole observation**: it names no word, no hour, and no count.

## The numbers, as evidence

| what | value | where it came from |
|---|---|---|
| the day's window | 03:48:43–17:10:45, about 13.4 h | the daemon's log |
| lines / unreadable | 8,034 / 0 | the day reader |
| daemon starts | 25 — all of them before 11:51:30 | the daemon's log |
| decisions | 7,149 | the day reader |
| frames sent | 379 — `accepted` 60, refused 0, unheard 319 | the day reader |
| sounds sent in frames | **97** — `chime` 38, `hello` 32, `pip` 18, `fall` 9 | the daemon's log |
| first / last sound | 05:31:43 / 17:09:32 | the daemon's log |
| sounds before 05:00 | **0** | the daemon's log |
| neck streams | 145 — 3,999 poses planned, 3,953 written | the day reader |
| read-backs | 146 — heard 118, carrying a position **100** | the day reader |

⚠️ **`unheard 319` is not a failure.** The daemon began reading the board's own acceptance at 11:51:30 (0.19.41); every frame written before that carries no `accepted` field, and the reader counts a missing field as unheard — **the instrument was not looking, the board was not refusing.** From 11:51:30: **60 frames, 60 accepted, 0 refused, 0 unheard.**

⚠️ **The first sound at 05:31:43 is the installed job's doing**: it was switched to `--sound on` at 05:27 that morning, and 21:00–05:00 stays silent — **0 sounds before 05:00 is that rule, seen from the log's side.**

## The ear and the log are two instruments, and they do not say the same thing

⚠️ **The log attributes every afternoon chime to this session.** The `chime` rows from 11:54:58 to 16:48:33 carry session `abf64e50…` — **the session that was watching this daemon** — and they arrive about **30 minutes and 10 seconds apart**, the interval at which that session re-armed its watch. ⇒ **the body was answering the observer's own work**, not the author's.

⛔ **Which of the 97 the ear caught is not established by this file.** The ear said 「たまに」; the log says 97 across twelve hours; **neither is a count of the other.**

## What this day adds

- **The first day is written down.** Row 8 of `docs/stackchan-progress.md` had no day; it has one now — **and ⛔ one day is not "day after day".**
- **The day's body**: 8,034 lines, 0 unreadable, 145 streams, 3,999 poses planned and 3,953 written, **1,367 board-applied poses across 26 verdicts, 0 refused, 0 clamped**.
- **The bus's bad half**: 46 read-backs carried no position, **all of them between 04:56:13 and 10:46:25, and none after**. Since the 0.19.41 start at 11:51:30: **19 probes, 19 with a position, 0 unheard.** ⛔ **Why the failures stop at 10:46 is still unnamed** — and that is what keeps rung 7 at ⚠️.

## What this does not say

- ⛔ **It is not the goal.** A sound playing is the body; whether anything is there is a different file (`2026-10-19-something-is-there.md`).
- ⛔ **It does not say the sounds were pleasant, well timed, or wanted.** The ear named their existence and nothing else.
- ⛔ **It does not connect 「たまに」 to any particular chime.** The session was moving the machine's state all afternoon; **the log cannot place the ear in the room.**
- ⚠️ **It does not close row 8.** The question is day after day; this file is one day, and its end was chosen at 17:10:45 — **the evening after that cut is not in it.**
