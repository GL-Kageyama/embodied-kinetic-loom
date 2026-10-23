<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-24-the-eye-that-asked-for-a-circle.md | translated: 2026-10-24 -->

**Language:** [English](2026-10-24-the-eye-that-asked-for-a-circle.md) | [日本語](2026-10-24-the-eye-that-asked-for-a-circle-ja.md) | [中文](2026-10-24-the-eye-that-asked-for-a-circle-zh.md)

# The eye that asked for a circle — 2026-10-24

⛔ **This page is a record of one author's two sentences about this body's faces — the one that judged a circle and the one that asked for a brow — and of an instrument that never fired.** 0.19.80 put three new faces on the body — `focused`, `watching`, `startled` — and no eye had judged any of them. **Both sentences came the same day, and each produced one change**: the processing face's eyes became a plain circle, and the writing face grew a brow. ⚠️ **The title keeps the first and names only it** — a record is named after the thing that made it, and the second arrived while it was being written. **What the eye saw is the spine; the daemon's rows are quoted inside it as evidence.**

**What was counted.** One unit, one Mac, one session, one pair of eyes, two faces asked about (`focused`, `watching`). **What was not counted:** whether the eye was in front of the body at any particular second — **no log holds a person**; the colour of the light as the eye saw it; and ⛔ **the number of times any face was drawn on the glass**, because the board answers a frame with one acceptance line and says nothing about the panel.

## What the author said

| the words | what they named |
|---|---|
| 「人間の判定を始めよう」 | that the judgment should begin |
| 「OK」 | ⛔ **nothing** — no face, no word, no complaint |
| (a question with three checkboxes, all three selected) | all three read as their word |
| 「書く時と処理中の顔を見たい、もう一度」 | `focused` and `watching` |
| 「処理中も目は丸がいい」 | `watching`'s **eyes** |
| 「書いている時は、目の上に眉毛（緩やか斜め）をつけよう」 | `focused`'s **brow** |
| `＼　／` (the author's drawing) | the direction of that brow — outer end high, inner end low |

⚠️ **The bare 「OK」 is kept here because this repository has already written down what it is worth**: on 2026-10-23 the author said 「全部OK」 to three questions — head, sound, light — and the record says it named none of them. ⇒ **The third row is a claim, and this page treats it as a claim.**

## The instrument, and the two sends that changed nothing

⛔ **The USB console was gone** — `/dev/cu.usb*` did not exist — so `bench face <word> [light]` could not be typed. ⇒ a throwaway script outside the repository, `/tmp/eye_face.py`, sent a layer event into `/tmp/ekl-stackchan-next-501.sock` and read the daemon's answer.

✅ **It works when a chapter is open.** The smoke test printed `focused: face=focused light=writing`, and the daemon wrote `{"face":"focused","gesture":null,"light":"writing","sound":null}` with `sent: true, accepted: true` at `at 3727.0`.

⛔ **The author never ran it.** The log holds no row from it — not one `PostToolUseFailure`, and no `PreToolUse` carrying `write` or `run` outside this session's own tool calls. **The instrument was offered and not used**, and the page says so rather than writing a run that did not happen.

⛔ **And then the instrument was driven from here, and the driving failed.** Two sends were queued behind the end of a turn — `focused` at +7 s, `watching` at +32 s — and the daemon logged both as **`reason: "observed", face: null, light: "breathe"`**, and wrote **no frame**. The rows are `PreToolUse work=write` at `at 3988.5` and `PreToolUse work=run` at `at 4013.6`, immediately after `Stop` (acted, `happy`/`warm`) and one `settled` row (`curious`/`breathe`). ⇒ **after a chapter has closed, a `PreToolUse` carried in by hand moves nothing** — ⚠️ **why that is so is not established here**, and the sentence that told the author to expect `focused` in seven seconds was **wrong when it was written**.

## What the board actually showed

| face and light | `at` | what put it there |
|---|---|---|
| `startled` / `alert` | 2948.8, 3241.1 | this session's own hand-sent sequence — **2 s each** |
| `watching` / `busy` | 3703.2, 3732.4, 4054.8, 4060.4 … | `run` tools, live |
| `focused` / `writing` | 3727.0, 4072.7 | the smoke test, and `write` tools, live |

⚠️ **Every row above says the frame was written and the board accepted it** (`sent: true, accepted: true`). ⛔ **Not one of them says an eye was on the screen**, and the board's acceptance is its own line, not a person's.

## The one judgment tied to a face

At `at 4051.5` the author spoke — `UserPromptSubmit`, `curious`/`dim` — the chapter opened, and from `at 4054.8` this session's tools held `watching`/`busy` on the board. **The sentence that followed was 「処理中も目は丸がいい」.** ⇒ **that judgment has a face under it**: `watching` was showing when it was made.

⛔ **The all-three answer does not have one**, and this page does not pretend otherwise: the instrument had not run, and the board at that moment was showing the settled face.

## What changed

`main/face_bitmap.cpp` — `kWatching` went from `{88, 0, 132, 6}` to `{100, 0, 132, 6}`. **The eyes are now the same disc `curious` wears** (weight 100, the author's number of 2026-10-20), and **the only thing this face says is the width of its mouth**. ⛔ **88 was "a little narrowed", and narrowing is `focused`'s job** (weight 55) — a face that narrows a little is a face saying something between two words. **One test holds it** — `test_the_watching_face_also_wears_the_disc`, in `tests/test_stackchan_face.py`, comparing the eye fields with `curious`'s pixel for pixel.

## The brow the same session asked for

⛔ **The second sentence is a request, not a judgment** — nothing on the glass had been read as `focused` when it was made, and this page does not upgrade it into a verdict.

**It is the one shape in `face_bitmap.cpp` the vendor never drew.** The vendor's skin is two discs, two lids and a bar; every other row in `StyleFor` moves numbers the vendor wrote. A brow had to be built (`DrawBrow`), and **its four numbers are chosen, not measured**: 24 px long, 3 px thick, the outer end 6 px higher than the inner, 5 px above the eye — a slope of `atan(6/24) ≈ 14°`, **gentler than the `＼` glyph the author drew**, because a glyph is drawn at whatever slope fits a character cell and a brow is drawn at whatever reads as a brow. ⚠️ **This page cannot say which of those two slopes the author meant**, and `bench face focused` is where that is asked.

**A brow does not blink.** The lid is drawn on the eye, and the brow is drawn outside `render_blink`'s one moving integer — so a blink leaves it standing. ⇒ **a blink now shows `focused`'s brow above two shut eyes**, and no eye has seen that picture either.

**One test holds it** — `test_only_the_focused_face_wears_a_brow`: exactly one face wears it, the tilt runs outer-high to inner-low on both sides, and the two brows sit at the same height. ⚠️ **The mirror check had to grow a row** (76 → 92) to cover it, and the harness had to learn a brow box, because until then **it measured the brows as part of the mouth** — the same shape of defect as the day a whole row of lit pixels sat outside every box the check knew.

## What this record does not say

- ⛔ **That `focused` was judged.** It was asked for, it was shown while tools ran, and **silence about it is not acceptance**.
- ⛔ **That `startled` was judged.** It showed twice, for two seconds each, and no sentence named it.
- ⛔ **That the new disc has been seen, or the brow.** No USB serial has appeared on this Mac — not `/dev/cu.usb*`, and no ESP32 or serial bridge in the USB tree — so the image that carries both **was built and not written** — ⚠️ **the change is source and two host tests, and the glass has not been asked**.
- ⛔ **That the brow reads as `focused`.** It was asked for, drawn, and checked for geometry; **whether it reads as *writing* is the author's eye's question**, and it is unanswered.
- ⛔ **Anything about colour.** The light's hue was never put to the eye in this judging; the faces were asked about as shapes.
