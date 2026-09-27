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
backend/
  protocol.py       5-byte frames. ⛔ the three hazards, and the one thing deliberately unwritten
  cycle.py          the periodic loop — absolute deadlines, and a clock that is passed in
  gate.py           the gate on what actually leaves. ⛔ a refusal is not a silence
  axis_map.py       degree of freedom → motor. ⛔ no defaults: the correspondence has no canonical form
  transmit.py       the trajectory at the wall clock — the nearest sample, not the next one
  mock.py           the box that pretends. ⚠️ a test of the protocol, not of the machine's safety
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

## The two gates, and the seat that is not decided

**`admit.py` is a decision, not a placement.** Whether Safety is a layer or a gate is undecided; this function is called either way, which is why the file is not named `safety.py`. Naming it that would settle a question that is still open.

⛔ **And it is the plan-time side only.** It checks a trajectory against the limits, knowing nothing about the clock. **`backend/gate.py` is the other side** — it sees one frame as it leaves, with the elapsed time measured rather than assumed.

**What only the run-time gate can see**, and why:

| what | why plan time cannot see it |
|---|---|
| the step between two consecutive frames | ⛔ **the upstream firmware has no soft start and no soft stop.** Whether a command is a step depends on the interval it is sent at, and a plan has no clock |
| the moment of sending | a plan is a function of `t`; it does not know `now` |
| which motor a degree of freedom maps to | ⛔ there is no canonical correspondence, so the gate does not decide it — the caller passes it in |

⛔ **And the gate's heaviest decision is the shape of a refusal: it does not return nothing.**

> **If you stop sending, torque falls to roughly a quarter within 15 seconds — and the motors do not stop.**

So a refusal returns **the last set that was allowed**, and keeps sending it. **That is the closest thing to standing still this machine has.** ⚠️ **It is not "stopping" either** — there is no stop command in the protocol. **The gate cannot fix that. All it can do is not send the bad frame.**

⚠️ **The gate judges a set as a unit.** Passing one motor at a time would put a combination on the machine that nobody planned.

## The clock is not imported

**`engine/` must not import `time`** — the purity test enforces it, because a trajectory that reads the clock is not a function. **The periodic loop therefore takes `now()` and `sleep()` from its caller.**

⚠️ **That is not only a purity accommodation.** It is what makes the cycle testable: with a clock passed in, two things the design notes could only state as *"written in deadline style"* and *"doesn't call `sleep(period)`"* become runnable assertions. A grep can see that a line is in the source; it cannot see that the line holds when it runs.

⛔ **And `period` has no default.** The notes measured the same machine taking two states, 5 ms and 10 ms. **Choosing one of them as a default would turn a measurement into a constant.**

## What is not here

**No serial layer, no Pet screen, no sound, no word-to-value mapping, no run-time monitoring.**

⚠️ **The serial layer is the one part the machine gates** — the control box has two generations, and the protocol differs between them, and **the place where a Mock and the machine diverge most is exactly there**: `flush()` was measured blocking forever on a macOS pty. **The Mock sits above the serial layer, so a green Mock says nothing about it.**

## The one thing the fallback costs

**`trapezoid` fails two of the five checks by construction: its acceleration is not zero at the ends, and its jerk is undefined at the corners.**

That is not a defect in the code. It is what a trapezoid profile is. **But it means that choosing the fallback means turning a check off**, and this repository records that in a test rather than leaving it to be discovered. With a jerk limit set, `admit` refuses every trapezoid; without one, it passes.

## Running the tests

```
python3 -m pytest tests/
```

⚠️ **A green run here means the mechanism computes what it was told to compute.** It means nothing about whether anything is *there* — see `docs/verification-boundary.md`.
