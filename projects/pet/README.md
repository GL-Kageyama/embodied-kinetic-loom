<!-- i18n-version: 1.0.0 | canonical: projects/pet/README.md | translated: 2026-09-28 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/pet/ — the screen

**The first thing to live in `projects/`, and the only part of the Pet that exists.**

⛔ **It is a face and nothing else.** No motion reaches it: the deterministic core computes trajectories, and nothing yet connects that computation to this screen. **The Pet's body is in `engine/`. Its face is here. They do not yet share a clock** — and *one clock for the face and the body* is the rule the design notes state, and the reason the decision below put this directory inside the repository.

## Two decisions are recorded here

- **A — keep the face, and call it a cat** (2026-09-28, the author). The five faces in `expressions.py` are copied **verbatim** from the concept document's §5 — not one character changed, including the indent. What changed is the record, not the drawing. See `expressions.py` for why writing the name down *is* the decision: the principle that argued against an animal shape rested on the premise that this ASCII is abstract, and `/\_/\` is a cat's ears.
- **C — the Pet lives inside this repository, under `projects/`** (2026-09-28, the author). ⚠️ **This one was decided against the recommendation.** Its stated price was a caveat to a fixed policy in `CLAUDE.md`, and **that caveat has not been paid yet**: it arrives in the same commit as the first file under `projects/` that calls an LLM. **This directory contains no such file.** The face is deterministic.

## The five faces

| state | the face | the motion the concept document pairs it with |
|---|---|---|
| `happy` | `( ^.^ )` | small bounce → small bounce → settle |
| `sleepy` | `( -.- )` + a fourth line, `z` | slow downward movement → small sway → still |
| `angry` | `( >.< )` | quick tilt → hold → small corrective movement |
| `curious` | `( o.o )` | small left tilt → center → small right tilt |
| `greeting` | `( ^.^ )` | small forward tilt → return |

⚠️ **The last row is not a typo: `happy` and `greeting` are the same face.** They are not the same expression — they are separated by the *motion*, and by nothing else. **That is measured, not asserted** (`tests/test_pet_expressions.py`). ⇒ **Drop the body and those two states become one state.** *One clock for the face and the body* is not a style preference; it follows from these five drawings.

## Running it

From the repository root:

```
python3 -m projects.pet                # cycles the five, until Ctrl-C
python3 -m projects.pet --state sleepy # one, and exits
python3 -m projects.pet --sync         # with synchronised output
```

⚠️ **`--sync` is off by default, and that is deliberate.** Whether the terminal in front of you implements `CSI ? 2026 h`/`l` **has not been measured from this workshop's side.** An assumption that was never measured does not get to be the default in the one place that touches your terminal.

## What is checked

**`tests/` holds four claims about this directory** — three files, and they run with the rest of the suite:

- **one frame is one write** — and that is a safety property, not a speed one. `frame()` returns the opening and the closing of the synchronised update **in the same string**, so the pair cannot be left open by a caller that writes once. **The second `SYNC_END` that `close()` emits is a rescue for a torn write, and it is idempotent.**
- **the frame's shape does not change with the state** — the box is 8 columns by 4 rows for every one of the five, so no line from a previous frame survives a redraw.
- **no character is wider than one column** — the documents in this workshop are CJK, and a single full-width character in a face would move the drawing on screen while `len()` said nothing.
- **`projects/` imports nothing that varies** — the same forbidden list `engine/` is held to, from `tools/purity.py`. ⛔ **`__main__.py` is named in the exclusion list, and the exclusion is itself asserted**: the entry point is the one place this repository may import `time`, because the loop takes its clock from its caller.

⚠️ **That last one does not make this directory as safe as `engine/`.** It checks imports and nothing else.

## What is not here

- **No motion.** `engine/` computes it; nothing connects the two.
- **No clock shared with the body.** The screen draws a state; it does not animate one.
- **No LLM.** See decision C above for when and where that changes.
