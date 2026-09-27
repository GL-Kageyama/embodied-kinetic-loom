<!-- i18n-version: 1.0.0 | canonical: tests/README.md | translated: 2026-09-27 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# tests/

**Eighteen files, two hundred and thirteen tests, all green — measured 2026-09-28.**

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

## The checks that came with `projects/`

**Three files arrived on 2026-09-28**, when the Pet's screen became the first thing to live in `projects/` — a decision that put code inside this repository but **outside the scan `test_purity.py` performs**.

| # | the check | where it lives |
|---|---|---|
| **6** | the five faces are the ones the concept document draws, and no line is wider than its box | `test_pet_expressions.py` |
| **7** | one frame is one write; the frame's shape does not change with the state; no character is wider than one column | `test_pet_screen.py` |
| **8** | `projects/` imports nothing that varies — with `__main__.py` named in the exclusion, **and the exclusion itself asserted** | `test_pet_purity.py` |

⚠️ **Numbering these 6, 7 and 8 is not a claim that there are eight checks of one kind.** The five above are checks on a trajectory. These are checks on a drawing and on a directory.

### A defect the check agreed with

**Running the entry point found it, not the suite.** `--state sleepy` printed `CSI ? 2026 l` although synchronised output had never been turned on — **`close()` was closing a borrow the screen had not taken.** ⚠️ **And `test_close_returns_the_terminal` asserted that exact string**, so the suite was green *and* agreed with the defect.

⇒ **The check now names both directions.** No `SYNC_END` when the update was never opened; **and a second one, deliberately, when it was** — each frame closes its own pair, so the `l` emitted by `close()` is a rescue for a write torn in transit, and it is idempotent.

## Why determinism is checked statically

**`test_purity.py` reads the imports of every file under `engine/` and fails if any is `random`, `time`, `os`, `socket`, or an LLM client.** ⚠️ **The list itself now lives in `tools/purity.py`, because a second scan reads it too** — **two copies of a rule means one of them gets updated.**

**Running the same input twice and comparing is not proof.** The two runs might simply have agreed. **The imports are the thing to look at**, and an AST finds them where a grep would find the word inside a docstring instead.

## A limit that was recorded, and then fixed

**When the gate refuses a frame it holds the last set that was allowed — because *not sending* is not *stopping*. That alone let a single late tick freeze an axis.** The gate's baseline is *the last value it allowed*, while the transmitter proposes *the wall clock's value*; the proposal keeps moving ahead, so the gap never closes. ⛔ **And because the gate's clock advanced on every refusal, the time it had accumulated was thrown away each time — so once an axis was refused, it was refused forever.**

**The machine was held, which is the safe direction, and it never arrived, which is not the mechanism's purpose.**

**`test_a_refused_axis_creeps_toward_the_target_instead_of_freezing` records the fix.** A refused axis now moves toward its target at the speed the gate itself allows — `velocity × elapsed`, the very size the gate would otherwise admit — so ⛔ **no new assumption was added to the safety argument.** **`test_the_gate_never_lets_an_axis_move_faster_than_its_limit` is the same claim measured over a whole run.**

⚠️ **An out-of-envelope target is still held rather than approached: outside the envelope is not a place to move toward.**

⚠️ **And the fix does not repair a plan that exceeds the gate's limit.** In the end-to-end test the gate's ceiling is half the plan's speed and the axis still does not arrive. **Finding that mismatch is `admit`'s job, not the gate's.**

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
