<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-24-the-face-that-moved-with-the-light.md | translated: 2026-10-24 -->

**Language:** [English](2026-10-24-the-face-that-moved-with-the-light.md) | [日本語](2026-10-24-the-face-that-moved-with-the-light-ja.md) | [中文](2026-10-24-the-face-that-moved-with-the-light-zh.md)

# The face that moved with the light — 2026-10-24

✅ **One person in one room said 「書いている（紫）も顔が連動して動いていたよ」** — *the writing one, the purple one, its face was moving in step with it too.* ⛔ **This page is that sentence, the frames the body was sent while it could have been said, and the line between them.** The umbrella this repository has been climbing toward since 0.19.80 is 「光の変化と表情が連動」 — **the face follows the light** — and until this sentence **no eye had said the two move together on the glass**.

**What was counted.** One unit, one Mac, one session, one pair of eyes, and the daemon's own log over the **900 s** ending at `at` 6068.0 — **the cut is stated where the frames are** — because the log was still growing while it was counted. **What was not counted:** whether the eye was in front of the panel at any particular second — **no log holds a person**; which of the day's transitions it caught; how many times the face blinked (the firmware's own clock, unlogged); and **the colour as the eye sees it** — ⛔ **the panel is not measured by the word 「紫」.**

## What the author said

| the words | what they name |
|---|---|
| 「書いている（紫）」 | **the light word `writing`**, identified by the colour it shows |
| 「も」 | that this is one more thing, after the face judged the day before |
| 「顔が連動して動いていた」 | ⚠️ **that the face and the light moved together** — ⛔ **which of the two "moved" carries the sentence is the session's reading, not the sentence's** |

⚠️ **The parenthetical is the first time a word and a colour were tied together by name.** On 2026-10-20 the author was shown the two work lights and said 「青、紫」 — **two colours, and which was which was never established** (the sequence was sent without saying what was coming). ⇒ **`writing` is now named as the purple one**; ⛔ **`busy` has no name yet.**

## What the body was sent in those 900 s

**The cut is written down, because the log was still growing while it was counted**: every frame whose `at` — the daemon's own monotonic seconds — lies in **5168.0–6068.0**, and the daemon's `at` 0 is about **04:38:26** on the wall clock. There are **38**, and **every one is `sent: true, accepted: true`**, read from the board's own line:

| the light | the face | frames |
|---|---|---|
| `busy` | `watching` | **14** |
| `writing` | `focused` | **6** |
| `dim` | `curious` | **4** |
| `dim` | `null` (the face is left alone) | **2** |
| `alert` | `startled` | **4** |
| `breathe` | `curious` | **4** |
| `warm` | `happy` / `greeting` | **2** / **2** |

**And the pair repeated.** `writing`+`focused` arrives **six times** inside that window — `06:04:47`, `06:06:35`, `06:07:41`, `06:14:47`, `06:18:16`, `06:18:45` — and each time `busy`+`watching` comes back after it. ⚠️ **The wall clock is derived, not logged**: `at` is monotonic, and it was anchored by putting the last row's `at` on the log file's last write, so ⛔ **±2 s, and the anchor is the last row rather than the row quoted.**

⚠️ **The instrument is the session it is measuring.** **34 of the 38 frames carry this session's own id** — the one writing this page — and the `writing`+`focused` frames are that session editing documents, **this record among them**. The four `breathe`+`curious` frames carry no `session` at all. ⇒ **counting the alternation is itself part of the alternation**, and ⛔ **nothing here separates the author's turn from the tool calls behind this page.**

⚠️ **Those are the frames the host wrote and the board accepted.** ⛔ **Not one row says a pixel changed on the glass** — the board answers a frame with one acceptance line and says nothing about the panel.

## What the eye could have been seeing

**The two fields move in one decision** (0.19.80): `write` → `focused` and `writing`, `run` → `watching` and `busy`. ⇒ **a face that changes when the light changes is exactly what the layer was built to produce**, and the alternation above is that rule running. ⚠️ **The face also blinks on its own** — both lids close for 80 ms every 3.2–6.8 s, from the firmware's clock, **and nothing logs it** — so 「動いていた」 has two candidate subjects and **this page does not choose between them**.

## What this sentence closes

✅ **「光の変化と表情が連動」 has been said by an eye, on the glass, for the first time.** ⛔ **It is not a judgment of any face's word** — `focused` and `startled` are still unread (the record of the day before says why), and **nothing here says the body is alive.**

⚠️ **It is also not a measurement of the colour**: the author named 紫 to identify the state, ⛔ **not to judge the hue**, and **no one has compared the panel's purple with `{104, 40, 76}`** — the table's three numbers are choices, and the screen's are the same numbers scaled so the largest lands on the peak.

## What this record does not say

- ⛔ **Which transition the eye caught**, or whether it saw one at all — **it may have watched a face that was only blinking.**
- ⛔ **That `busy` is teal to anyone's eye**, or that the two work colours can be told apart by a person who is not told which is coming.
- ⛔ **That the goal is verified.** One person in one room said a thing about a face; `docs/verification-boundary.md` is the page that says what that is worth.
