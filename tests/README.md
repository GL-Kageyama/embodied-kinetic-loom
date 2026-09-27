<!-- i18n-version: 1.0.0 | canonical: tests/README.md | translated: 2026-09-27 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# tests/

**Fifteen files, one hundred and sixty tests, all green — measured 2026-09-27.**

**This file used to say there were none.** It changed in the same commit as the first test, which is the rule that section of `CLAUDE.md` states and this directory exists to hold.

## The five checks, and where each one lives

| # | the check | where it lives | ⚠️ what it also records |
|---|---|---|---|
| **1** | the ends: position, velocity and acceleration are zero at both ends | `test_profile.py`, `test_plan.py` | ⛔ **the trapezoid fails this** — its acceleration is not zero at the ends |
| **2** | limits are not exceeded, per axis **and combined** | `test_limits.py`, `test_gate.py` | ⛔ **the trapezoid fails this too** — its jerk is undefined at the corners. **And the check runs twice, at two different times** — see below |
| **3** | reachability — the segments that vanish | `test_profile.py`, `test_admit.py` | **the odd one out: it handles the case where no correct trajectory exists** |
| **4** | determinism | `test_plan.py`, `test_purity.py` | comparing two runs is not enough — see below |
| **5** | Safety refuses what it should | `test_admit.py`, `test_gate.py` | ⚠️ **the plan-time side and the run-time side are different checks, not two copies of one** |

**Two of the five are negative claims, and they are the point.** The fallback profile is documented as a fallback; these tests record that **choosing it means turning a check off.** Without them that one check would go missing quietly.

## The same check at two times

**Limits are checked at plan time (`admit.py`) and again as each frame leaves (`backend/gate.py`). The second is not a repeat of the first.**

Plan time holds the whole trajectory and no clock. The gate holds one frame and an elapsed time measured in the loop. **Three things exist only at the second:** the interval between two consecutive frames — which is what decides whether a command is a step, given that the firmware has no soft start — the moment of sending, and the motor each degree of freedom maps to.

⚠️ **And the two can disagree in the direction that matters.** A trajectory that passed `admit` can still produce a step at the gate, because one late tick makes the transmitter skip samples. **That case is asserted in `test_backend.py`, and it names its own limit rather than hiding it** — see below.

## The check that `05 §2.2` said could not be written

**The design notes listed the cycle as checkable in two ways, both of them shapes rather than properties: *"written in deadline style"*, and *"doesn't call `sleep(period)`"*.** ⛔ **Neither had been written, because there was no loop to write them against.**

**`test_cycle.py` writes them as properties.** The loop takes its clock from the caller — `engine/` may not import `time` — so a fake clock runs it and counts what it was asked to sleep. The two shape-checks become: **the deadline of tick `n` is `start + n * period` even when every sleep overshoots**, and **no single sleep request exceeds `period × sleep_fraction`**.

⚠️ **A grep can see that a line is in the source. It cannot see that the line holds when it runs** — a loop that sleeps `deadline - now` every time never contains the string `sleep(period)` and behaves exactly as if it did.

## The check that is not one of the five

**`test_intent.py` holds the boundary from both sides.** The `quality` field of the type is accepted by the schema and ignored by the code — and both halves are asserted, because either half alone would let the boundary collapse. **On the day the vocabulary lands, the second half is rewritten, not deleted.**

## Why determinism is checked statically

**`test_purity.py` reads the imports of every file under `engine/` and fails if any is `random`, `time`, `os`, `socket`, or an LLM client.**

**Running the same input twice and comparing is not proof.** The two runs might simply have agreed. **The imports are the thing to look at**, and an AST finds them where a grep would find the word inside a docstring instead.

## A limit that is recorded rather than fixed

**When the gate refuses a frame, it holds the last set that was allowed — because *not sending* is not *stopping*. So a single late tick can freeze an axis, and nothing in the gate brings it back.**

The reason is that the gate's baseline is *the last value it allowed*, while the transmitter proposes *the wall clock's value*. The proposal keeps moving ahead, so the gap never closes. **The machine is held, which is the safe direction, and it does not arrive, which is not the mechanism's purpose.**

**`test_a_late_tick_freezes_the_axis_and_the_gate_does_not_recover` records this and lists the three options.** It is written as a limit, not as a design — **the choice is the author's**, and until it is made the behaviour is asserted so that changing it cannot be silent.

## The rule that holds this directory — applied to us

**`CLAUDE.md`'s Tests section must not say "nothing yet" while test files sit on disk.**

That state is not hypothetical — **a sister repository is in it right now**: seven test files and fifty-four tests on disk, and its `CLAUDE.md` still reads "not yet built". **So when the first test landed here, that section changed in the same commit.** A section that describes a directory rather than reading it is how that happens.

## What is checked today, and where

**The two checks that are not tests do not live here.**

- **`claude plugin validate --strict .`** — the manifest fields and the two versions against each other.
- **`python3 tools/check_i18n.py`** — the document mirrors. It has its own `--self-test`.

⚠️ **Together they see five of the fifteen conventions this repository follows. Nothing checks the other ten.**

## Running this directory

```
python3 -m pytest tests/
```

⚠️ **Green means the mechanism computes what it was told to compute.** It means nothing about whether anything is *there* — see `docs/verification-boundary.md`. **What is alive is not a thing a test can be written for.**
