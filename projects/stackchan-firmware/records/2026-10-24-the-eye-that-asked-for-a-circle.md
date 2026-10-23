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

`main/face_bitmap.cpp` — `kWatching` went from `{88, 0, 132, 6}` to `{100, 0, 132, 6}`. **The eyes are now the same disc `curious` wears** (weight 100, the author's number of 2026-10-20), and **the only thing this face says is the width of its mouth**. ⛔ **88 was "a little narrowed", and narrowing is `focused`'s job** (weight 55) — a face that narrows a little is a face saying something between two words. ⚠️ **Amended the same day**: the parenthetical stopped being true within the hour — `focused` took the disc too, and **no face this body added narrows an eye** (see *The preview, and the second judgment*). ⛔ **The reason 88 was wrong does not depend on that clause**: a lid between two words says something between two words, whoever else is using it. **One test holds it** — `test_the_watching_face_also_wears_the_disc`, in `tests/test_stackchan_face.py`, comparing the eye fields with `curious`'s pixel for pixel.

## The brow the same session asked for

⛔ **The second sentence is a request, not a judgment** — nothing on the glass had been read as `focused` when it was made, and this page does not upgrade it into a verdict.

**It is the one shape in `face_bitmap.cpp` the vendor never drew.** The vendor's skin is two discs, two lids and a bar; every other row in `StyleFor` moves numbers the vendor wrote. A brow had to be built (`DrawBrow`), and **its four numbers are chosen, not measured**: 24 px long, 3 px thick, the outer end 6 px higher than the inner, 5 px above the eye — a slope of `atan(6/24) ≈ 14°`, **gentler than the `＼` glyph the author drew**, because a glyph is drawn at whatever slope fits a character cell and a brow is drawn at whatever reads as a brow. ⚠️ **This page cannot say which of those two slopes the author meant**, and `bench face focused` is where that is asked.

**A brow does not blink.** The lid is drawn on the eye, and the brow is drawn outside `render_blink`'s one moving integer — so a blink leaves it standing. ⇒ **a blink now shows `focused`'s brow above two shut eyes**, and no eye has seen that picture either.

**One test holds it** — `test_only_the_focused_face_wears_a_brow`: exactly one face wears it, the tilt runs outer-high to inner-low on both sides, and the two brows sit at the same height. ⚠️ **The mirror check had to grow a row** (76 → 92) to cover it, and the harness had to learn a brow box, because until then **it measured the brows as part of the mouth** — the same shape of defect as the day a whole row of lit pixels sat outside every box the check knew.

## The preview, and the second judgment

⚠️ **The glass was still unavailable when the second judgment came.** The author wrote 「さした」 — the cable was re-seated — and the Mac listed no change: `/dev/cu.*` and `/dev/tty.*` held the Bluetooth port and the debug console and nothing else, and `ioreg -p IOUSB` showed three hubs with a LAN adapter, a REALFORCE keyboard and a Bluetooth dongle under them, **no ESP32 and no serial bridge**. ⛔ **The body was alive the whole time**: the daemon's port 3333 held `ESTABLISHED` to `192.168.0.100:63327`, so the board was running, dialled in, and running the image from before this day's change.

**So the session drew the faces on the host instead.** `face_bitmap.cpp` and `command_frame.cpp` were compiled with `clang++` against a small dumper, `render()` was called for all eight words, and each 320 × 240 grey buffer was written out as a PNG; a contact sheet (four by two) was opened, with a 3× crop of `focused`'s eyes beneath it. ⛔ **This is not a photograph of the panel**: it is the same drawing function the firmware calls, printed to a file — the RGB565 conversion and the panel's coarseness are not in it, and **nothing about the glass is measured by it**.

**The author's two sentences:**

| the words | what they did |
|---|---|
| 「この見え方でOK」 | the brow, as drawn, at the slope it was drawn at — 24 px long, 3 px thick, 6 px rise, 5 px gap |
| 「眉毛ある時も丸目がいいな」 | `focused`'s eyes: weight 55 → **100**, the disc `curious` and `watching` wear |

⚠️ **The first sentence names no shape.** It followed a message whose subject was the brow's four numbers and the sentence that whether the shape reads as *writing* is the author's to decide, and the session reads it as approval of the brow as drawn — ⛔ **that reading is not in the sentence**, and this page keeps the sentence and the reading apart. ⚠️ **It also does not repeat the 2026-10-20 verdict** — 「● が見える」 closed *a circle is visible*, and this closes *this brow, drawn this way, is what was wanted*.

**What changed:** `main/face_bitmap.cpp` — `kFocused` went from `{55, 0, 60, 6, true}` to `{100, 0, 60, 6, true}`. **The brow stays and the mouth does not move**; what left the face is the narrowed lid. ⇒ **none of the three words this body added narrows an eye now**, and the sentence written on 0.19.81 — *narrowing is `focused`'s job* — is false from this hour; ⛔ **it was true when it was written, and the page it was written on says what it used to say.**

**One test holds it** — `test_the_focused_face_wears_the_disc_under_its_brow`: the eye is `curious`'s disc field for field, the brow count is still above zero, and the mouth is still 60 wide. ⛔ **A second test was rewritten rather than kept**: `test_the_watching_face_also_wears_the_disc` still holds its own row, and its docstring now carries the sentence it used to assert and the hour that undid it.

## The cable, the second time

✅ **The author wrote 「もう一回さしなおした」, and this time the Mac moved**: `/dev/cu.usbmodem1101`, `/dev/tty.usbmodem1101`, and `USB JTAG/serial debug unit@01100000` in `ioreg`. ⚠️ **The first re-seat changed nothing and this one did** — ⛔ **whether that is the cable, the port, or how the chip's USB comes back is not separated here**, and one re-seat failing is not a board that cannot come back.

**Nothing was written before the slot was known.** `otadata` at `0xd000` read **`ota_seq = 1`, `state = 0x2`** ⇒ `ota_0` at **`0x20000`**; the descriptor at `0x20020` was read **before** the write and named **`7f27191-dirty`, `Oct 24 2026 05:16:43`** — 0.19.80's image, the one the body had been running all day.

| step | the number |
|---|---|
| written | **937,712 bytes** (577,384 compressed) at `0x20000`, 5.2 s |
| esptool | **`Hash of data verified.`** |
| descriptor after | **`2a5c49e-dirty`, `Oct 24 2026 06:05:06`** |
| console | `bench: face focused drawn — the eye says whether it reads as that word` |

⛔ **`--verify` is not a boot check** — 0.19.53 wrote a verified image to a slot nothing boots and the screen did not change — and that is why the descriptor is read on both sides. ⚠️ **The boot banner was not captured**; the running image is established by the descriptor, not by a line the board printed.

⛔ **And the glass has still not answered.** `bench face focused` puts the drawing on the panel; **whether the disc with a brow above it reads as *writing* is the author's eye's question**, and silence is not acceptance.

## The first look at the glass

✅ **After `bench face focused`, the author wrote two lines:**

| the words | what they name |
|---|---|
| 「丸い目＋緩やかな斜めの眉＋短い口」 | the three parts of the drawing, one by one |
| 「それが写っている」 | that those three parts are on the panel |

⛔ **This is an observation of the drawing, not a reading of the word.** It closes *the panel carries what the host rendered*; it does not close *the face reads as **writing*** — **the author named the shapes and did not name the meaning** — and it says nothing about colour.

⚠️ **It is one more part than 2026-10-20's 「● が見える」**: three, not one, and **the brow is among them** — so the one shape the vendor never drew has been caught by an eye on the glass. ⛔ **That is a shape seen, not a word judged.**

## What this record does not say

- ⛔ **That `focused` was judged.** It was asked for, it was shown while tools ran, and **silence about it is not acceptance**. ⚠️ **Amended the same day**: its *drawing* was approved from a host preview (「この見え方でOK」) — ⛔ **and an approved drawing is not a word read off the glass.**
- ⛔ **That `startled` was judged.** It showed twice, for two seconds each, and no sentence named it.
- ⛔ **That the new disc has been seen, or the brow.** ~~No USB serial has appeared on this Mac — not `/dev/cu.usb*`, and no ESP32 or serial bridge in the USB tree — so the image that carries both **was built and not written**.~~ ⚠️ **Amended the same day, twice**: first the brow and the disc were seen **as a host rendering** (a sheet of the eight faces, no panel); then a **second** 「もう一回さしなおした」 brought `/dev/cu.usbmodem1101` back, **937,712 bytes were written at `0x20000`**, the descriptor read back **`2a5c49e-dirty`**, and `bench face focused` answered *drawn* — so **a panel is carrying them now**. ⛔ **No eye has said what it sees**, and ⚠️ **「さした」 is not one event: the first changed nothing and the second did.**
- ⛔ **That the brow reads as `focused`.** It was asked for, drawn, and checked for geometry; **whether it reads as *writing* is the author's eye's question**, and it is unanswered. ⚠️ **Amended the same day**: the shape was approved as a drawing, and then **three parts were named on the glass** (「丸い目＋緩やかな斜めの眉＋短い口」「それが写っている」) — ⛔ **the question above is about a brow on a face while something is being written; that face is now on the glass, its parts are confirmed, and the word is still unread.**
- ⛔ **Anything about colour.** The light's hue was never put to the eye in this judging; the faces were asked about as shapes.
