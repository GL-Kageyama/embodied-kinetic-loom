<!-- i18n-version: 1.0.0 | canonical: engine/README.md | translated: 2026-09-27 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# engine/

**The deterministic core** — interpolation, easing, smoothing, limiting. The four things that are functions, and therefore the four things this workshop can check exactly.

## What is here

```
intent.py           the Motion Intent, loaded and checked against schemas/
trajectory/
  profile.py        the machine family — the curves whose end velocity is zero
  easing.py         the expression family — CSS cubic-bezier. ⛔ never handed to the machine
  smooth.py         smoothing that does not move the ends
  limits.py         per-axis limits, and the combined one
  plan.py           a trajectory, and its samples
  admit.py          pass or refuse — the plan-time side only
```

## Why the two families live in two modules

**Because a screen and a machine want opposite things from a curve.**

`Back`, `Elastic` and `Bounce` accelerate backwards before they move forwards. On a screen that reads as anticipation. On a machine it is an acceleration in the wrong direction. The expression family therefore stays in `easing.py`, and only the machine family — `min-jerk` and `trapezoid` — can be handed to `plan`.

⛔ **The mapping from one family to the other does not exist, and this engine does not invent it.** The design notes say of that mapping, in their own words, that it is a proposal and not a design. Writing it here would make it this repository's invention. `easing.MAPPING_TO_MACHINE` is therefore `None`, and a test asserts that it still is — so that the day someone writes it, the change is deliberate and visible.

## What makes this deterministic

**The same input produces the same output, bit for bit, and that claim is enforced two ways.**

- **`tests/test_purity.py` reads the imports of every file under `engine/` and fails if any of them is `random`, `time`, `os`, `socket`, or an LLM client.** Comparing two runs is not enough on its own — the two runs might simply have agreed by luck. The imports are the thing to look at.
- **Sample times are counted, not accumulated** — `duration * k / (count - 1)`, never `t += step`.
- **The bisection in `easing.py` runs a fixed number of steps.** Solving to a tolerance would make the result a function of the input in name only.

⚠️ **The ends of a trajectory are placed exactly.** The first sample is the start and the last is the end, as given — `start + (end - start)` is not always `end` in floating point, and a command that misses its target by one unit in the last place is a command that did not arrive.

## The gate, and the seat that is not decided

**`admit.py` is a decision, not a placement.** Whether Safety is a layer or a gate is undecided; this function is called either way, which is why the file is not named `safety.py`. Naming it that would settle a question that is still open.

⛔ **And it is the plan-time side only.** The design notes are unambiguous that plan-time assurance alone is insufficient. **The run-time gate does not exist yet** — it needs the machine and a backend.

## The one thing the fallback costs

**`trapezoid` fails two of the five checks by construction: its acceleration is not zero at the ends, and its jerk is undefined at the corners.**

That is not a defect in the code. It is what a trapezoid profile is. **But it means that choosing the fallback means turning a check off**, and this repository records that in a test rather than leaving it to be discovered. With a jerk limit set, `admit` refuses every trapezoid; without one, it passes.

## What is not here

**No backend, no mock, no Pet screen, no sound.** Those need the machine's response, and nothing here has driven a physical machine. **No word-to-value mapping** — the vocabulary that would fill the `quality` field of the type is gated. **No run-time monitoring.**

## Running the tests

```
python3 -m pytest tests/
```

⚠️ **A green run here means the mechanism computes what it was told to compute.** It means nothing about whether anything is *there* — see `docs/verification-boundary.md`.
