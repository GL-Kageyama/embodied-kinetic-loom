<!-- i18n-version: 1.0.0 | canonical: projects/pet/README.md | translated: 2026-09-28 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/pet/ — the screen and the motion

**The first thing to live in `projects/`, and the only part of the Pet that exists.**

**The core and the screen are joined, for one state.** `motions/greeting.json` is a `Motion Intent` written in a session; `motion.py` admits it, computes the trajectory, passes it through the gate to the mock — **and draws the face inside the first tick of the same loop.** That is *one clock for the face and the body*, and it is asserted rather than described.

⛔ **The body is the mock's, not the machine's.** Nothing here opens a port; the serial layer is still the one part the machine gates.

## Two decisions are recorded here

- **A — keep the face, and call it a cat** (2026-09-28, the author). The five faces in `expressions.py` are copied **verbatim** from the concept document's §5 — not one character changed, including the indent. What changed is the record, not the drawing. See `expressions.py` for why writing the name down *is* the decision: the principle that argued against an animal shape rested on the premise that this ASCII is abstract, and `/\_/\` is a cat's ears.
- **C — the Pet lives inside this repository, under `projects/`** (2026-09-28, the author). ⚠️ **This one was decided against the recommendation.** Its stated price was a caveat to a fixed policy in `CLAUDE.md`, and **that caveat has not been paid yet**: it arrives in the same commit as the first file under `projects/` that calls an LLM. **This directory contains no such file.**

## The five faces

| state | the face | the motion the concept document pairs it with |
|---|---|---|
| `happy` | `( ^.^ )` | small bounce → small bounce → settle |
| `sleepy` | `( -.- )` + a fourth line, `z` | slow downward movement → small sway → still |
| `angry` | `( >.< )` | quick tilt → hold → small corrective movement |
| `curious` | `( o.o )` | small left tilt → center → small right tilt |
| `greeting` | `( ^.^ )` | small forward tilt → return |

⚠️ **The last row is not a typo: `happy` and `greeting` are the same face.** They are not the same expression — they are separated by the *motion*, and by nothing else. **That is measured, not asserted** (`tests/test_pet_expressions.py`). ⇒ **Drop the body and those two states become one state.** *One clock for the face and the body* is not a style preference; it follows from these five drawings — and it is why `greeting` was the first motion built.

## The one motion

`motions/greeting.json` — the intent, and the only one that exists:

| the words | degree of freedom | the amount | the time | group |
|---|---|---|---|---|
| `small forward tilt` | `pitch` | `+40` counts (512 → 552) | 600 ms | 0 |
| `return` | `pitch` | 512 | 600 ms | 1 |

⚠️ **The words are not in the file.** `schemas/motion-intent.schema.json` sets `additionalProperties: false`, so there is no field to put them in — they live in `motion.py` instead. ⛔ **That is not an inconvenience: an `Intent` is already counts, and it cannot say why the number is that number.** The row that pairs each word with its number is in `references/README.md`.

⛔ **The words came from the concept document's §5. The numbers did not come from anywhere** — `demo_rig()` lists every number it supplies and what each one is not. ⚠️ **In particular it supplies no velocity limit at all**, so the step check does not fire: what is actually being enforced in this run is the envelope (190–833), which is the one measured number. **Do not read a green run as "safe".**

## Running it

From the repository root:

```
python3 -m projects.pet                    # cycles the five, until Ctrl-C
python3 -m projects.pet --state sleepy     # one, and exits
python3 -m projects.pet --sync             # with synchronised output
python3 -m projects.pet --motion greeting  # the motion, and the face from the same clock
```

⚠️ **`--sync` is off by default, and that is deliberate.** Whether the terminal in front of you implements `CSI ? 2026 h`/`l` **has not been measured from this workshop's side.** An assumption that was never measured does not get to be the default in the one place that touches your terminal.

⚠️ **`--motion` sends to a mock, and its last line says so** — together with which checks therefore did not fire. **A run that prints four zeros is a run in which nothing was refused; it is not a run in which anything was verified about a machine.**

## What is checked

**`tests/` holds seven claims about this directory** — four files, and they run with the rest of the suite:

- **one frame is one write** — and that is a safety property, not a speed one. `frame()` returns the opening and the closing of the synchronised update **in the same string**, so the pair cannot be left open by a caller that writes once. **The second `SYNC_END` that `close()` emits is a rescue for a torn write, and it is idempotent.**
- **the frame's shape does not change with the state** — the box is 8 columns by 4 rows for every one of the five, so no line from a previous frame survives a redraw.
- **no character is wider than one column** — the documents in this workshop are CJK, and a single full-width character in a face would move the drawing on screen while `len()` said nothing.
- **`projects/` imports nothing that varies** — the same forbidden list `engine/` is held to, from `tools/purity.py`. ⛔ **`__main__.py` is named in the exclusion list, and the exclusion is itself asserted**: the entry point is the one place this repository may import `time`, because the loop takes its clock from its caller.
- **the face and the body come from the same tick** — `Take.drawn_at` equals `ticks[0].started`. ⛔ **The face is drawn inside the first tick, never before the loop** — drawn outside it, *one clock* would be a description rather than a claim, and there would be nothing to assert.
- **the Pet arrives back where the intent's second group says** — and **nothing jumps at the boundary between the two groups.** ⚠️ **That second half was added on 2026-09-28, after a defect it would have caught**: the group was clamped back to the last one when the performance ended, but the *offset* was not, so the ticks after the end re-sent the **first** sample of the last group rather than its last. **See `HISTORY.md` 0.5.0.**
- ⛔ **a start position the intent was not written for moves the Pet away.** **This one records a limit of the type, not a defect.** A `target` is absolute counts, so the intent does not know where the machine is; running an intent written for 512 from 400 leaves the Pet at 512 and not where it started — **and no gate refuses anything, because every single frame is legal.** Only the meaning is wrong. **The deterministic core does not know whether the numbers mean anything.**

⚠️ **That last one does not make this directory as safe as `engine/`.** It checks imports and nothing else — and the claims above are about a mock.

## What is not here

- **No serial layer.** The mock is a Python object pretending to be the control box; the frames go no further. ⛔ **This is the one part the machine gates**, and where a mock and the machine diverge most.
- **One motion, and one of five verbs.** ⚠️ **Three of the vocabulary's five verbs name a translation this machine does not have**, so not one of them has exercised the column that D-12 added to `references/`.
- **No LLM.** See decision C above for when and where that changes.
- **No feedback.** The start position is supplied by hand — `demo_rig()` says which number that is and that it is not a measurement. **The machine does not report back what it did.**
