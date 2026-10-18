<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-18-the-gestures.md | translated: 2026-10-18 -->

**Language:** [English](2026-10-18-the-gestures.md) | [日本語](2026-10-18-the-gestures-ja.md) | [中文](2026-10-18-the-gestures-zh.md)

# The gestures — 2026-10-18

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A table of angles with no eye behind it is a guess written in a measurement's clothes.

**What was counted.** Five gestures, one unit, one pair of eyes, one day. **What was not counted:** whether these are the *best* angles, whether a second person would name each posture the same way, and whether anything is alive behind them.

## What was seen

**Five postures were placed with a bench command and asked about, one at a time.** The author was watching the head and answered each placement. ⚠️ **No instrument recorded this. It is an eye on a desk, and it is the only thing in this file that can say a posture is what its word means.**

| # | the placement | the author's words | what was kept |
|---|---|---|---|
| 1 | `bench set 8 50 80` | 「これで perk」 | yaw **+8.0°**, pitch **50.0°** |
| 2 | `bench set 20 50 80` | 「もっと大きく」 | not enough for `turn` |
| 3 | `bench set 35 50 80` | 「これで turn」 | yaw **+35.0°**, pitch **50.0°** |
| 4 | `bench set 0 30 80` | 「もっと下げる」 | not enough for `settle` |
| 5 | `bench set 0 10 80` | 「もっと下げる」 | still not enough |
| 6 | `bench set 0 3 80` | 「これで settle」 | yaw **0.0°**, pitch **3.0°** |
| 7 | `bench set 8 10 80` | 「もっと深く」 | not deep enough for `nod` |
| 8 | `bench set 8 3 80` | 「これで nod」 | the down point: yaw **+8.0°**, pitch **3.0°** |
| 9 | `bench set -8 70 80` | 「これで flinch」 | yaw **−8.0°**, pitch **70.0°** |

⛔ **Two of the placements were the machine's limit, not the author's choice.** `settle` and the down point of `nod` both sit at **pitch 3.0°**, the vendor's minimum (`kPitchAngleMinTenths`). The author said 「もっと下げる」 twice for `settle`; the third placement was the lowest the neck can go, and it was accepted there. **A word that wants to go lower cannot on this machine** — that is a difference the machine does not cover, recorded here rather than smoothed away.

⚠️ **The bench envelope moved during the measurement.** It was ±20.0° when the first two postures were placed, and `turn` could not be shown at all: `bench set 20` is the clamp. It was raised to ±45.0° **before** placement 3 — still a bench bound and a third of the vendor's ±128.0°, and not a gesture's limit. The reason it moved is in `main/board.h`, beside the number.

## How each posture was placed

`bench set <yaw> <pitch> [speed]` is a bench command added the same day for this measurement. It reads both positions, writes both goals on the present positions, turns torque on, writes one goal to each axis with the same speed the measurement used, and **holds torque on** while it polls until the head stops moving. ⛔ **It is not a trajectory**: the servo's own speed field does the moving, and nothing interpolates upstream.

⚠️ **The command is `set`, not `pose`.** The dispatcher tests `pos` first and its test is three characters wide, so any word beginning with `pos` is read as `bench pos`. That collision is recorded at the dispatch, in the source.

## The numbers

⚠️ **The angle sent and the position the servo settled at are not the same number.** Both are here.

| gesture | yaw (0.1°) | pitch (0.1°) | raw written | raw held (bench) | raw held (a frame) |
|---|---|---|---|---|---|
| `look_up` | `+80` | `+500` | 485 / 780 | 491 / 778 | 477 / 781 |
| `look_side` | `+350` | `+500` | 572 / 780 | 566 / 778 | 564 / 781 |
| `rest` | `0` | `+30` | 460 / 629 | 466 / 630 | 467 / 629 |
| `nod` (down point) | `+80` | `+30` | 485 / 629 | 478 / 630 | not read separately |
| `recoil` | `−80` | `+700` | 435 / 844 | 442 / 842 | 442 / 842 |

⚠️ **The zeroes are this unit's, from NVS: yaw 460, pitch 620.** The conversion is the vendor's: `raw = zero + tenths × 16 / 50`, truncated.

**The shortfall is real and it is not constant.** `look_up` settled **6 counts above** its written yaw, `look_side` **8 below**, `recoil` **7 above**, and the pitch axis settled 2–5 counts off in both directions across the placements. ⛔ **No correction is applied.** A fixed offset was not separated from backlash, from the read-back, and from the servo's own settling — so none is assumed.

## A frame moves the word

✅ **After the table was written into the firmware, the five gestures were played from the wire**, one frame at a time, by writing a JSON line to the board's console. Each one moved the head to its measured posture, and the board printed where it ended. ⛔ **This is still not the engine**: nothing read a `Motion Intent`, nothing interpolated, and the daemon did not send these lines — a session did, by hand.

`nod` is the one gesture that is not a single posture. It was measured as **a down point and a place to come back to**, and the place it comes back to is the posture it was measured from — `look_up`'s. ⇒ **A `nod` moves down to pitch 3.0° and returns to pitch 50.0°.**

## The names, and the stiffness

⛔ **The author rejected the five words the protocol had carried since 0.19.0**: 「そもそも、英語の動作名前が、わかりづらい」. The candidates were `perk`, `nod`, `turn`, `settle`, `flinch` — chosen in the session, borrowed from nowhere, and `perk` in particular could not be read as *raise the face*. **The author chose readable English, and the words became:**

| the old word | the new word | what it says |
|---|---|---|
| `perk` | `look_up` | the face goes up |
| `turn` | `look_side` | the face goes to one side |
| `nod` | `nod` | unchanged |
| `settle` | `rest` | the face comes down and stays |
| `flinch` | `recoil` | the face pulls back and up |

⚠️ **The angles did not move with the names.** The rename touched the schema, the codec, the daemon's layer, the parser, the firmware's table and the tests; what the head does is the table above.

⛔ **And the author's second judgement was not about the name**: after the renamed gestures were played from frames, 「動きが硬い」. **The motion is stiff** — each gesture is one move at one speed, followed by a stop. That is not a defect in the table; it is what the wire cannot do yet: the servo's speed field is linear, and **nothing interpolates** between the posture it leaves and the posture it takes. ⚠️ **The engine that would interpolate has never run on this machine.** That is the next decision, and this record does not settle it.

## What this record does not say

- **that the motion is good.** The author said it is stiff, and that is the last word in this file.
- **that these angles are right for anyone else.** One eye, one unit, one day. A second person would place `look_side` somewhere else.
- **that the engine ran.** No `Motion Intent`, no trajectory, no gate, no pose stream. The board played a table of five postures.
- **that `rest` is restful or `recoil` is a flinch.** The words were chosen to be readable; whether the postures carry them is the author's judgement, quoted above.
- **that the Pet is there.** ⛔ **That is the goal, and it cannot be verified in this workshop.** A head that follows a word is a mechanism.

## The numbers, in one place

| what | value | where it came from |
|---|---|---|
| the postures | yaw/pitch tenths, table above | nine placements, judged one at a time |
| the zeros | yaw **460**, pitch **620** | this unit's NVS, read at boot |
| the scale | `raw = zero + tenths × 16 / 50` | the vendor's source, not measured here |
| the bench envelope | ±20.0° → **±45.0°** during the measurement | `main/board.h` |
| the speed | **80**, the one the postures were measured at | `bench set <yaw> <pitch> 80` |
| the pitch floor | **3.0°** — `rest` and `nod`'s down point sit on it | the vendor's limit, `kPitchAngleMinTenths` |
| the frames | five JSON lines, one per gesture | written to the console by a session |
| what the motion is | one move and a stop, per gesture | the author: 「動きが硬い」 |
| the engine | has never run on this machine | 678 poses once came from a tool outside this repository |
