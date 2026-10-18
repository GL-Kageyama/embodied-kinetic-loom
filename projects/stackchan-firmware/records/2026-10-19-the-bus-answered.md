<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-19-the-bus-answered.md | translated: 2026-10-19 -->

**Language:** [English](2026-10-19-the-bus-answered.md) | [日本語](2026-10-19-the-bus-answered-ja.md) | [中文](2026-10-19-the-bus-answered-zh.md)

# The bus answered — 2026-10-19

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A stream with no eye behind it is a guess in a measurement's clothes.

**What was counted.** One unit, one pair of eyes, one pair of ears, and two deliberate events sent by the session into the installed daemon's own socket — sent to be watched, not because the room asked. **What was not counted:** which of the two moves the eye caught, how far the head travelled as seen, how loud the sound was, and whether anything is alive behind it.

## What was seen and heard

**The first report came as answers, not as a sentence.** The session had asked two questions — did the neck move, was there a sound — and the author replied:

> 1:動いた
> 2:鳴った

— it moved, and it sounded. ⚠️ **Two numbers, two answers**: the author counted the questions and answered them in order.

**Then the author asked for the check again:**

> もう一回動作確認したい

The session sent one `PermissionRequest` and, 3.0 seconds later, one `SessionStart` into the daemon's socket, and asked the same two questions of that pair. The answer was:

> ok

⚠️ **One word for two questions.** The word confirms the pair; ⛔ **it does not separate the move from the sound, and it does not say which of two opposite moves the eye caught** — the first was 27° to one side in 0.45 s, the second 27° back 3.0 s later.

## The numbers, as evidence

⚠️ **`at` is the daemon's own monotonic clock in seconds, not a wall time**; the wall times below are approximate, read against the log's file time.

| what | value | where it came from |
|---|---|---|
| the first move of the second check | yaw 80 → 350 tenths (27.0°), 0.45 s, 23 poses | the daemon's log, about 08:34 JST |
| its summary | `applied 23, late 22, held 25` | the daemon's log |
| the read-back before the second move | `{"position": [328, 487]}` — heard, with a position | the daemon's log |
| the second move | from the measured `[328, 487]` to `[80, 500]`, 0.413 s, 22 poses | the daemon's log |
| its summary | `applied 22, late 20, held 28` | the daemon's log |
| the frame of the first | `{"face":null,"gesture":null,"light":"alert","sound":"pip"}`, `sent: true` | the daemon's log |
| the frame of the second | `{"face":"greeting","gesture":null,"light":"warm","sound":"hello"}`, `sent: true` | the daemon's log |
| the landing, read by the host | target 350, read 328 — 2.2° short, about seven counts | the daemon's log |

⛔ **`sent: true` is the host's tty taking the whole line, not the board receiving it.** Delivery is evidenced here by the eye and the ear, and by nothing else in this file.

## What the read-back adds

**Before this morning, the read-back had never carried a position.** The log read at 05:36 held **24 read-backs, 12 heard, 0 with a position** — a path that answered and a position that did not come.

**Since the rail's power cycle (0.19.31) the log holds eight read-backs, and four carry a position**: `[28, 487]`, `[53, 487]`, `[328, 487]`, and the one quoted above. ⇒ **The path is not dead; its answer is intermittent.**

✅ **And the one number it brought agrees with another instrument.** The target was 350 tenths and the host read 328 — 2.2° short, about seven counts. **The board's own printing measured six to eight counts short of every goal the day before**, through a different route: the firmware reading the servo itself. **Two instruments, one number** — and ⛔ **neither is calibrated**, so agreement here is agreement in size, not accuracy.

## What this does not say

- ⛔ **It is not the goal.** A head moving and a sound playing are the body; they are not evidence that anything is there. **The goal's record is a different file**, `projects/stackchan-firmware/records/2026-10-19-something-is-there.md`.
- ⛔ **It does not say answering is now guaranteed.** Four of eight read-backs answered. **The other four were `heard: false`** — nothing that parsed as an answer arrived within `PORT_WAIT = 0.5` — and **the reason has not been separated**. ⚠️ **The glued-line mechanism found on the shared console the same day (`frame: refused (malformed)`) is the same console and may not be the same cause.**
- ⚠️ **It does not describe the motion.** Nobody has said whether 22 of 23 poses applied late read as smooth this time; that question was asked of a different gesture, in a different file.
- ⚠️ **It does not connect the two answers to the two moves.** The first report and the second check were minutes apart; the words the author gave cannot be matched to a particular frame by this file.

## Where the silence went

**The silence that lasted from boot was a state the servos held, and the rail's own switch is what cleared it** — `bench power off`, three seconds, `bench power on`, two ids answering, 5.1 V at the servo, written down in `0.19.31`.

⛔ **What this file adds is that the clearing is not permanent.** The bus answered, then did not, then did; **the trigger is still unnamed**, and since 0.19.31 a boot throws the rail switch itself — **which is a recovery, not a diagnosis.** ⇒ **The seventh rung stays ⚠️: it answers now, and answering is not yet guaranteed.**
