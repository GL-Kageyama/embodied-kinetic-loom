<!-- i18n-version: 1.0.0 | canonical: schemas/README.md | translated: 2026-09-27 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# schemas/

**The boundary type lives here.** One file so far.

```
motion-intent.schema.json     the Motion Intent — D-06
```

## The type is the boundary

**Everything upstream of it may vary; everything downstream of it must be a function.** A session with a person in it writes the intent, in natural language, guided by a skill. The code reads it and computes. That is what makes a trajectory testable.

**Draft 2020-12, closed by default.** `additionalProperties: false` on both objects — an unknown key is an error rather than a silent no-op. That is the practice the design notes record, and it is the safer of the two defaults: a typo in a field name fails loudly instead of being ignored.

## The one field that is left open

⛔ **`moves[].quality` is open on purpose, and it is the only one.**

**Closing a field whose value type is not yet decided makes it impossible to write.** But leaving a field open while pretending it is settled is worse — a value goes in, nothing reads it, and everyone assumes it did something.

**So the boundary is held from both sides, and both sides are tested:**

| side | what it does | which test holds it |
|---|---|---|
| the schema | **accepts** the field, and any object as its value | `test_the_open_field_accepts_any_object` |
| the code | **does not carry it** — `engine/intent.py` builds its `Move` without it | `test_the_open_field_is_accepted_and_ignored` |

**This is where the collision between the type and the vocabulary has been given an address.** It has not been erased: the field exists because the vocabulary that would fill it does not. It is gated on a decision that needs the machine's response, and on a question about the Pet's life when no session is running — both still open.

**The day the word-to-value mapping lands, the second row changes.** The schema keeps the field; the code starts reading it. The test that currently asserts the code ignores it is written so that it must be rewritten — not deleted — on that day.

## What is deliberately NOT in the type

- ⛔ **The admissible range of `target`.** It is feedback-driven, not a constant that can be read off the protocol, and it belongs to the safety envelope the host supplies at run time. **Holding the same number in two places is how the two come to disagree.**
- ⛔ **Any limit on velocity, acceleration or jerk.** Same reason, and one more: the only jerk figure the research turned up could not be attributed to the standard it was quoted from. **This repository puts no invented constant into a schema.**
- **The axis-to-motor correspondence.** The three degree-of-freedom names are ours. The control box documents no canonical correspondence, and the sign of every axis depends on the wiring. A name in this file is a label.
- **Anything about time.** How long the host waits, what the period is, whether a loop is on a deadline — none of it is in the type. Two of those are measured properties of the host, not of the intent.

## Validating by hand

```python
import json, jsonschema
jsonschema.validate(json.load(open("intent.json")),
                    json.load(open("schemas/motion-intent.schema.json")))
```

⚠️ **`jsonschema` is needed to load a type and not to compute a trajectory.** The core in `engine/trajectory/` is arithmetic and nothing else.
