<!-- i18n-version: 1.0.0 | canonical: references/README.md | translated: 2026-09-28 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# references/ — the motion vocabulary

**The vocabulary is where a word becomes numbers. This directory holds the mapping, and nothing else.**

⛔ **It holds one row today** — **the row that was used.** ⚠️ **Not the rows that could be written**: the vocabulary starts from five verbs, and four of them have never been sent to this machine.

## ⛔ What this file is not

**This is not the answer to D-02.** The question that gated `skills/` is whether the vocabulary is a fixed table or a catalogue that can be drawn from — **and on 2026-09-28 the author left it open, deciding the order instead: use the vocabulary once, then decide.**

⇒ **What decided the shape of this file is that a motion was built. It is not that the question was answered.** ⚠️ **When the question is answered, this file is rewritten — and the rewrite is expected, not a defect.** **Read this row as a record of one conversion, never as the vocabulary's design.**

## The one row that was used

| the words | degree of freedom | the amount | the time | ⛔ the difference this machine cannot cover | where it was used |
|---|---|---|---|---|---|
| `small forward tilt` → `return` | `pitch` | `+40` counts | `600` ms each way | **none** — this word names a freedom the machine has | `projects/pet/motions/greeting.json` |

### What the row says, column by column

- **The words are the concept document's §5, verbatim.** `greeting` is paired there with *small forward tilt → return*, and the Pet's five faces were already copied the same way — one character unchanged.
- **The words sit outside the type, on purpose.** The `Motion Intent` schema sets `additionalProperties: false`, so there is no field to put them in; they live in `projects/pet/motion.py` instead. ⛔ **That is not an inconvenience. An `Intent` is already counts, and it cannot say why the number is that number.**
- ⛔ **The amount is not a measurement.** `+40` counts is `552 − 512`, and both of those are choices — `demo_rig()` lists every number it supplies and what each one is not. **The words came from the concept document. The numbers did not come from anywhere.**
- ⛔ **The column carrying the warning is the decision of 2026-09-28 (D-12).** Of the five verbs the vocabulary starts from — 傾く / 倒れる / 沈む / 跳ねる / 後退 — **three name a translation this machine does not have. The verbs stay in the vocabulary, and this column carries the difference.**
- **`none` in that column is a result, not a blank.** `pitch` is one of the three degrees of freedom the machine has; there is nothing to cover.

## What is not here

- ⛔ **Four rows.** The vocabulary starts from five verbs and this table has one. **The missing four are the ones that were not used** — and writing them now would be writing down what has never run.
- ⛔ **Three of those four would carry a difference.** 沈む / 跳ねる / 後退 name a translation, and the machine has no such freedom. **The column exists for them; not one of them has crossed it yet.**
- ⛔ **The adverbs.** 前に / 少し / ゆっくり are the other half of the mapping — and the design notes record that no dictionary or study they found has reached the meaning of adverbs.
- ⛔ **Any claim that a mapping is correct.** **There is no measurement behind this table.** It records what one word was turned into, once.
