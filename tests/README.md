<!-- i18n-version: 1.4.0 | canonical: tests/README.md | translated: 2026-09-28 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# tests/

**Twenty-one files, two hundred and forty-six tests, all green — measured 2026-09-28.**

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

**Three files arrived on 2026-09-28**, when the Pet's screen became the first thing to live in `projects/` — a decision that put code inside this repository but **outside the scan `test_purity.py` performs**. **A fourth arrived the same day**, when one motion was carried end to end.

| # | the check | where it lives |
|---|---|---|
| **6** | the five faces are the ones the concept document draws, and no line is wider than its box | `test_pet_expressions.py` |
| **7** | one frame is one write; the frame's shape does not change with the state; no character is wider than one column | `test_pet_screen.py` |
| **8** | `projects/` imports nothing that varies — with `__main__.py` named in the exclusion, **and the exclusion itself asserted** | `test_pet_purity.py` |
| **9** | the face and the body come from the same tick, the second group starts where the first ended, and nothing jumps at the boundary | `test_pet_motion.py` |

⚠️ **Numbering these 6 to 9 is not a claim that there are nine checks of one kind.** The five above are checks on a trajectory. **These are checks on a drawing, on a directory, and on the join between a trajectory and a drawing.**

### Two defects that hid each other

**Neither was found by reading the code. Both were found by running it and disbelieving the number that came back.**

⛔ **The first is in `admit.py`, and it is safety-relevant.** Every group of an intent was planned from `starts_by_dof` — the machine's position before the *motion*, not before *that group*. So when one degree of freedom appears in two groups — tilt forward, come back — the second group was planned from where the first one started, and the machine, which is by then at the peak, was handed a trajectory whose first sample is somewhere else. **At the boundary the machine jumps to that sample. That is a step, and the upstream firmware has no soft start.**

**It stayed green because the only two-group test in the suite used a different degree of freedom per group.** The suite was not wrong; it was blind.

⚠️ **The fix was three lines — carry a running position across the groups — and the same error was found a second time in `trapezoid_reachability`, which measured the second group's distance from the wrong end as well.** ⛔ **A move that cannot be reached can pass that check when the error points the wrong way.**

⚠️ **And the second defect was hiding behind the first.** `motion.py` chose the group by accumulating an offset, and clamped the group index back to the last one when the performance ended — **without clamping the offset.** So the ticks after the end re-sent the *first* sample of the last group instead of its last. **The machine, halfway back to where it started, was commanded away from it.** ⚠️ **Under the first defect the second group was a flat line beginning at the start position, so its first sample was that position too — and the arrival test passed because two errors cancelled.** **Repairing one exposed the other.**

⇒ **Each fix was then reverted once, and the suite watched**: three tests fail for each. ⚠️ **A test that has never been seen to fail is not yet a check.**

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

## A rule that had no check, until now

**`CLAUDE.md` says the version is one value in three places**: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and the newest `## <version>` in `HISTORY.md`.

⚠️ **Two of the three were already watched.** `claude plugin validate --strict .` compares the two manifests. ⛔ **The third was read by nobody.**

**Why that one matters more than it looks.** The two manifests are only read by tooling. **`HISTORY.md` is the file a person opens to find out what this version contains** — so a `HISTORY.md` left one version behind is not a bookkeeping slip. **It is the record disagreeing with the thing it records.** And it fails silently, in the direction that reads as correct: `validate` stays green, the suite stays green, and the only symptom is a reader who trusts the wrong paragraph.

**`tests/test_versions.py` is check 10, and it is of a third kind.** Checks 1–5 are checks on a trajectory; checks 6–9 are checks on a drawing, on a directory, and on the joint between a trajectory and a drawing. **This one is a check on this repository's own bookkeeping** — it reads no engine code and no output, only three version strings.

**It was reverted once, and the suite watched**: changing the `HISTORY.md` heading to `0.6.9` fails `test_history_agrees_with_the_manifests` and nothing else. ⚠️ **A test that has never been seen to fail is not yet a check.**

⚠️ **What it does not see.** It asserts the three agree; it says nothing about whether the version is *earned*. It reads **the first heading only** — a skipped or duplicated version further down does not ring. And it does not touch `i18n-version`, which is a different number about a different thing, checked by `tools/check_i18n.py`.

**And the parser is tested against itself.** `test_the_parser_finds_nothing_when_there_is_no_heading` feeds it a history with no version heading, a level-1 heading, a level-3 heading, and `0.6.0.1` — **because if `newest_version()` ever returns `""` instead of `None`, all three of the other assertions go green together.**

## The check that `08 §4` said could not be written

**The design notes listed one row as *does not ring* — and named what would make it ring: *"does the CSS family's name appear in the backend's input? — that is writable with a `grep`."***

⛔ **Written the way `08` imagined it, it would have been green for the wrong reason.** `08` proposed this question: *does any file under `engine/backend/` import `engine/trajectory/easing`?* ⚠️ **`engine/backend/transmit.py` imports `..trajectory.plan`, and that one line runs `engine/trajectory/__init__.py` — which re-exports `easing`.** **The module is loaded; the answer is `yes` before anything is asked.** A check asking that question cannot tell *not used* from *loaded by the package's own `__init__`*.

**`test_expression_boundary.py` is check 11, and it asks about names instead of modules.** Three claims: `engine/backend/` does not name the expression module or any of its exports; it does not hold an expression word as a **value**; and the `Motion Intent` type names none of them. ⚠️ **The vocabulary is read from `CURVES`, so the list has one home** — plus the three families the survey names as the reason for the rule. ⛔ **Those three are in no source file here; the check is their only address.** **Check 11 is of a fourth kind**: not a trajectory, not a drawing or a directory or a joint, not bookkeeping — **it is a check on what may cross the boundary.**

⚠️ **Prose does not ring.** The words are read from string constants that are *values*, not from docstrings — otherwise the check would fire on the schema's own `quality` description, **which names the very words it warns against.** **A check that rings on correct documentation is a check that gets deleted.**

⚠️ **And green here means *not yet broken*, not *protected*.** The backend names none of these today because nothing has ever needed to name one.

**It was reverted once, and the suite watched**: an expression import in `transmit.py`, an expression word as a value in `gate.py`, and a word added to the `dof` enum **each failed exactly one test, and the other five stayed green.** ⚠️ **A test that has never been seen to fail is not yet a check.**

⚠️ **One measurement is kept here as a test rather than as a sentence**: `test_loading_a_backend_module_also_loads_the_expression_module` runs a subprocess and asserts that importing the backend **does** put `engine.trajectory.easing` into `sys.modules`. **That is not a defect** — it is the fact that makes *"does it import easing"* the wrong question. ⛔ **If it ever fails, the fact changed, not the code** — rewrite the note; do not delete the test.

## The rule that holds this directory — applied to us

**`CLAUDE.md`'s Tests section must not say "nothing yet" while test files sit on disk.**

That state is not hypothetical — **a sister repository is in it right now**: seven test files and fifty-four tests on disk, and its `CLAUDE.md` still reads "not yet built". **So when the first test landed here, that section changed in the same commit.** A section that describes a directory rather than reading it is how that happens.

## What is checked today, and where

**The three checks that are not tests do not live here.**

- **`claude plugin validate --strict .`** — the manifest fields and the two versions against each other.
- **`python3 tools/check_i18n.py`** — the document mirrors. It has its own `--self-test`.
- **`python3 tools/check_vocabulary.py`** — the vocabulary table. It has its own `--self-test`.

⚠️ **The first two see five of the fifteen conventions this repository follows. Nothing checks the other ten.**

⛔ **The third guards a rule that is not one of the fifteen.** It arrived on 2026-09-28 with the mapping, for a rule this repository wrote for itself that day — *do not invent a word* — **and the fifteen predate it.** ⇒ **Counting it against the fifteen would be counting a different thing**; what it reads is the table's shape (columns, degrees of freedom, paths, and that the two mirrors agree), **and never whether the mapping is right.**

⚠️ **And it found its own author's mistake first.** Its V5 compared the mirror's header row too, where the column *names* are translated — so three correct mappings rang as four violations. **A check that has just been written is the first thing to disbelieve.**

## Running this directory

```
python3 -m pytest tests/
```

⚠️ **Green means the mechanism computes what it was told to compute.** It means nothing about whether anything is *there* — see `docs/verification-boundary.md`. **What is alive is not a thing a test can be written for.**
