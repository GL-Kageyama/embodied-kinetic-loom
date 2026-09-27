<!-- i18n-version: 2.0.0 | canonical: references/README.md | translated: 2026-09-28 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# references/ — the motion vocabulary

**The vocabulary is where a word becomes numbers. This directory holds the mapping, and nothing else.**

**It is a catalogue: written as rows, drawn from by name, and grown by use.** ⛔ **It holds one entry today — the one that was used.** The vocabulary starts from five verbs, and four of them have never been sent to this machine.

## ✅ The decision this file is

**D-02 — is the vocabulary a fixed table, or a catalogue that can be drawn from?** ⚠️ **The author left it open on 2026-09-28, deciding the order instead: *use the vocabulary once, then decide*.** **The vocabulary has now been used once, and the question was answered on the same day under the delegation the author had already given.** ⛔ **This file is the answer — it is the rewrite the previous version said would come.**

**The answer follows from two decisions that were already made, rather than from a preference:**

- ⛔ **Decision C answered *who draws when no session is running* — the application's AI does.** The design notes had already written what that answer does to this question: **it tilts it toward a catalogue, because the drawer is at run time.**
- **D-03 put the writer in the session, guided by a skill, and kept this repository's code away from the LLM.** ⇒ **The drawer is Claude, not a program** — **so the canonical form is a table that Claude reads, not a data file that code loads.** ⛔ **A second, machine-only copy is not built, because nothing would read it.** What is wrong is not holding a thing twice; **it is holding a copy that nothing reads.**

**The other two options, and why not:**

| the option | why not |
|---|---|
| **(a) the fixed table** | ⛔ **Nothing would read it, and a table nothing reads cannot be checked.** The design notes put it in one line: *a fixed enumeration cannot be checked.* **And the one time a row was needed, it had to be written — there was nothing to draw from.** |
| **(c) generation rules only** (Laban's shape) | ⛔ **Three catalogues of motion words already exist outside this workshop** — Kindaichi's classes, IPAL's verb descriptions, Shimizu et al.'s 43 scales. **A fourth is not what is missing; the mapping is.** **And the survey that proposed this shape wrote, in its own closing line, that a catalogue does not imply automatic generation.** |

⚠️ **What this answer costs.** **The vocabulary now has a rule a writer can break** — *do not invent a word* — **and a rule needs a check.** `tools/check_vocabulary.py` is that check, and it arrived in the same commit as this sentence.

## How it is drawn from

1. ⛔ **A word that is not in the table is not in the vocabulary.** **The writer does not invent a word at the point of writing an intent.** If the motion needs a word the table does not have, **the row is written first** — deliberately, with its difference column filled in — **and the intent is written second.** **That is what *grown by use* means here, and it is the only way this table grows.**
2. **A row names a degree of freedom the machine has**, never the freedom the word implies. ⛔ **When the two differ, the difference column carries the gap** — and **`none` in that column is a result, not a blank.**
3. **The words are not written into a `Motion Intent`.** The schema sets `additionalProperties: false`, and the one field it leaves open is not a home for them. ⛔ **An `Intent` is already counts, and it cannot say why the number is that number.** **This table is the only place the two are held together.**
4. **`tools/check_vocabulary.py` reads the tables, not this prose**: the header row and every row must have the same number of columns, every row's degree of freedom must be one the type can name, every path in the last column must exist, **and the tables in the two mirrors must say the same three things** — ⚠️ **the column names are translated, and the degrees of freedom and the paths are not.** ⛔ **What it does not check is whether the mapping is right** — and it never can. **The round trip through the writer's judgement is the one step that has no check.**

## The one entry that was used

| the words | degree of freedom | the amount | the time | ⛔ the difference this machine cannot cover | where it was used |
|---|---|---|---|---|---|
| `small forward tilt` → `return` | `pitch` | `+40` counts | `600` ms each way | **none** — this word names a freedom the machine has | `projects/pet/motions/greeting.json` |

### What the row says, column by column

- **The words are the concept document's §5, verbatim.** `greeting` is paired there with *small forward tilt → return*, and the Pet's five faces were already copied the same way — one character unchanged.
- **The degree of freedom is the machine's, not the word's.** `tilt` is a rotation and `pitch` is one of the three the machine has; **this row is the case where the two agree, which is why the difference column says `none`.**
- ⛔ **The amount is not a measurement.** `+40` counts is `552 − 512`, and both of those are choices — `demo_rig()` lists every number it supplies and what each one is not. **The words came from the concept document. The numbers did not come from anywhere.**
- ⛔ **The warning column is the decision of 2026-09-28 (D-12).** Of the five verbs the vocabulary starts from — 傾く / 倒れる / 沈む / 跳ねる / 後退 — **three name a translation this machine does not have. The verbs stay in the vocabulary, and this column carries the difference.**

## What is not here

- ⛔ **Four rows.** The vocabulary starts from five verbs and this table has one. **The missing four are the ones that were not used** — and writing them now would be writing down what has never run.
- ⛔ **Three of those four would carry a difference.** 沈む / 跳ねる / 後退 name a translation, and the machine has no such freedom. **The column exists for them; not one of them has crossed it yet.**
- ⛔ **The adverbs.** 前に / 少し / ゆっくり are the other half of the mapping — and the design notes record that no dictionary or study they found has reached the meaning of adverbs.
- ⛔ **Any claim that a mapping is correct.** **There is no measurement behind this table.** It records what one word was turned into, once.
