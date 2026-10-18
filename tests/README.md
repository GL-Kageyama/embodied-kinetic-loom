<!-- i18n-version: 1.23.0 | canonical: tests/README.md | translated: 2026-10-19 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# tests/

**Thirty-one files, five hundred and twenty-nine tests, all green — measured 2026-10-19.**

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

## The check that arrived with `--lang`

**The rule was already written down.** `CLAUDE.md`'s Language section fixed the default at `en` and said a `--lang` argument and an environment variable may lower it — **and then said, in the same list, that the runtime string tables were not built yet.** ⛔ **The first stage with runtime strings was 0.5.0, when the Pet began printing a report.** By 0.10.0 the entry point held seventeen Japanese constants and there was no way to change them.

**`test_strings.py` is check 12, and it is of a fifth kind**: not a trajectory, not a drawing or a directory or a joint, not bookkeeping, not what may cross the boundary — **it is a check on whether the words a person reads exist in the language they asked for.**

### ⛔ The core had to change, and that is the point

**`Rejection.reason` was a Japanese sentence, built inside `engine/trajectory/admit.py`.** `report()` printed it. **So `--lang en` would have produced English help text with a Japanese refusal on the next line** — a surface that is half translated, and visibly so.

⇒ **The core now emits a code and the values to fill in; the edge turns that into a sentence.** Five codes, in `locales/`.

⚠️ **That was not a translation chore.** A sentence is not a value — **nothing can branch on it and no table can reach it.** This repository's thesis is that the boundary is drawn at a typed value; **`Rejection` was on the wrong side of it.**

### ⛔ `resolve()` does not read the environment

**`os` is on the forbidden list in `tools/purity.py`, and the reason written beside it is `environ`.** So the language cannot be settled inside the core.

**`strings.resolve(cli, env)` takes both as arguments.** `projects/pet/__main__.py` — the one file that scan excludes — reads `os.environ` and passes the value down. ⚠️ **That is the shape the clock already has**: `engine/` may not import `time`, so the loop takes its clock from the caller. **The edge reads the world; the core receives values.**

⇒ **The priority order is therefore testable without touching the environment**, and one test asserts the boundary itself: with `EMBODIED_KINETIC_LOOM_LANG` set in the process, `strings.resolve()` still returns `en`, while `language_of()` returns the variable. **The day that line fails is the day the environment leaked into the core.**

### What it sees, and what it cannot

**Two of the checks are static.** `Rejection("…")` literals are walked with an AST across `engine/` — **the codes are built deep in the core, and the entry point cannot reach all five** — and each must be in all three tables. **`strings.text("section", "key")` literals are walked across `projects/`** for the same reason.

⛔ **The entry point's own help strings are invisible to that walk.** `build_parser` reaches them through a local function, so the keys are not string arguments at any call site. **A static check that cannot see them is not a check on them** — so those six are checked instead **by building the parser in all three languages**: the three help texts must differ from one another, no brace may survive, and `--lang`, `--motion`, `--state` and the five state names must read the same in every language. **Spellings are not language.**

⚠️ **And the tables are not documents.** `tools/check_i18n.py` reads mirrors of Markdown — headings, the `Language:` line, fences containing `←`. **A JSON table is a different medium**, so the mirror rule is asserted again here: the three files carry the same keys, and every template uses the same holes. **A rule living in two media needs two checks, and neither covers the other.**

⛔ **What it does not see.** It cannot tell whether a translation is any good, or that the Japanese is Japanese. It cannot see a key that sits in the table and is reached by nothing — **the direction it checks is the one that breaks at run time.** **And it says nothing about the exception messages that remain Japanese throughout `engine/`**: those are written to the workshop, and **whether they should move is a decision not yet taken.**

### Reverted five times, and the suite watched

| what was broken | what rang |
|---|---|
| `help_lang` deleted from `locales/ja.json` | three tests — the parser cannot be built in `ja` |
| `{frames}` → `{frame}` in `locales/zh.json` | `test_every_translation_fills_the_same_holes` |
| a code added in `admit.py`, absent from the tables | `test_every_code_the_core_can_emit_is_in_the_table` |
| one entry deleted from `locales/ja.json` | four tests, including the reached-key walk |
| `cli` and `env` swapped in `resolve()` | the two priority tests |

⚠️ **A test that has never been seen to fail is not yet a check.**

### ⛔ A trap met while putting the files back

**The same size, in the same second.** Two of the breaks changed a file without changing its length — `cli or env` becomes `env or cli`, and a restored file is byte-identical to the file it replaces. **Python decides a `.pyc` is still valid from the source's mtime in whole seconds and its size.** Restore a same-length file within the same second and the stale bytecode runs.

**So the suite failed after the file had been put back, and `diff` said the file was right.** ⚠️ **"It still fails after I put it back" is not evidence that the check is missing.** Clear the bytecode caches and run it again — **and disbelieve the number in both directions.**

## The seam, and the defect it uncovered (2026-10-15)

**`engine/backend/wire.py` arrived, and with it the machine's name left the gate and the transmitter.** Fourteen tests were added; the count moved from 267 to 281. What they hold:

| the check | where | what it is for |
|---|---|---|
| the gate cannot be built without an `envelope` or a `wire` | `test_gate.py` | ⛔ **a default cannot say whose number it is.** A gate that fills either in silently becomes machine 1's gate, and does it without raising |
| the gate refuses more axes than its wire can carry | `test_gate.py` | ⚠️ **the other direction is allowed** — machine 1's frames are per-axis, so commanding one axis alone is legitimately expressible |
| the gate can refuse in exactly four ways | `test_gate.py` | ⛔ `unknown-command` was **removed**: with `Command` (axis is a plain `int`) that branch is unreachable, and an unreachable branch silently widens what a docstring may claim |
| the payload is the bytes the wire would write — **even on a refused tick** | `test_transmit.py` | ⛔ **a refusal is not a silence** (`gate.py`'s own rule) |
| `transmit.py` does not name machine 1 | `test_transmit.py` | over **AST identifiers, not text** — the docstring truthfully says it once called `encode_target`, and a grep would ring on that correct sentence |
| the envelope's numbers are built in exactly one file | `test_limits.py` | scans `engine/**` for an `Envelope(...)` call given a numeric literal |
| no string table names a machine's count | `test_strings.py` | ⛔ **a shared table cannot say whose number it is** — `pet_report.caveat` used to read *190–833, measured* |

⛔ **And one defect was found by asking what a second machine would need, not by reading the code.** The gate's loop wrote only the axes that were *proposed*; its own docstring claimed no axis goes silent. ⚠️ **Machine 1 never showed it, because `Transmitter` proposes every axis on every tick.** ⇒ **A machine that carries two axes in one line would have had an axis drop out of the set, with `encode` holding nothing to write for it.** `test_an_axis_missing_from_the_proposal_is_still_filled_in` is the regression, and ⚠️ **filling is not refusing** — `held` stays false, so the record can still tell *refused* from *nothing was asked*.

⚠️ **What none of this tests is machine 2.** There is still one wire in this repository. **`DofRealityWire` is the only implementation, so *the wire is swappable* is a claim about the design and not yet a measurement** — `test_transmit.py`'s stand-in wire is labelled as a stand-in, not as an implementation.

## The check that arrived before the second wire (2026-10-18)

**`projects/stackchan/` arrived, and with it the layer above the wire — events to phases, faces and lights, with no numbers for machine 2.** Thirty-four tests were added; the count moved from 281 to 315 — **then twenty-four more with the daemon, twenty-one with its client, and twenty-five with the wire to machine 2, moving it to 385** — **then ten more with the outbound frame and two more with the daemon that logs it, moving it to 397.** ⚠️ **The three tables below carry today's counts, not that day's** — the voice added one to the first, three to the third and three to the fourth — **and the chain above stays the arrival's, because a chain rewritten at its tail stops being a record.** **They are check 13, and it is of a sixth kind**: not a trajectory, not a drawing or a directory or a joint, not bookkeeping, not the boundary, not the words — **it is a check on a decision that is upstream of the `Motion Intent` and therefore has no trajectory to check.**

**What it holds:**

| the check | where | what it is for |
|---|---|---|
| the event list is 33, and each one is a transition, evidence or ignored | `test_stackchan_behaviors.py` | ⛔ **the names come from the hooks reference; a name that is not in the list raises `UnknownEvent`** rather than falling into a default |
| six phases, five faces and six lights are all reached; every reason is from a closed set | `test_stackchan_behaviors.py` | the mapping is checked by properties, not by a second copy of the table |
| **no gesture is ever sent** — `sent` is `False` on every line | `test_stackchan_behaviors.py` | ⛔ **the honest answer for machine 2 today.** A gesture is a candidate word, not a row in the vocabulary |
| three failures in a row raise the light and not the face; `angry` is only `StopFailure` | `test_stackchan_behaviors.py` | the product decision that a failing test is not an occasion for anger |
| **the gaze is single and sticky over two and three windows** — a person's act moves it, a tool call and a background `Stop` do not, a background `PermissionRequest` steals it | `test_stackchan_behaviors.py` | ⚠️ **windows share one neck**; alternating would land inside the one-second floor |
| a gesture inside the cooldown is dropped, and the light still changes | `test_stackchan_behaviors.py` | ⚠️ **1.0 s is borrowed from the 10/04 unit**, not measured on this one |
| sound is off by default, and carries one word on four of the six transitions | `test_stackchan_behaviors.py` | ✅ **since 2026-10-18 the speaker has been played on this unit, and the author heard all four words** |
| every sound word the layer can choose is one the wire's closed set names | `test_stackchan_behaviors.py` | ⛔ **two tables of the same four words would drift**, and the wire's is the one the board reads |
| no machine-1 name or number is in the package | `test_stackchan_behaviors.py` | over **AST identifiers and numeric constants**, not text — and it also asserts that no `motions/` directory exists |
| the parser builds in three languages, and the help differs | `test_stackchan_behaviors.py` | the same assertion `test_strings.py` makes for the Pet's entry point |

**Thirty-five more hold the daemon — the process that keeps the phase between hook processes:**

| the check | where | what it is for |
|---|---|---|
| the socket answers, and the row it logs is the row the client received | `test_stackchan_daemon.py` | ⚠️ **one row is written once** — `Decision.as_row` is shared by the CLI and the daemon |
| a second instance exits 3 and the first still answers; a stale socket is unlinked | `test_stackchan_daemon.py` | the socket is the lock; there is no pidfile |
| an unknown key, an unknown event and a malformed line are each refused with a code | `test_stackchan_daemon.py` | ⛔ **unknown is refused, not ignored** — otherwise `prompt` could ride along |
| a prompt in the line never reaches the log | `test_stackchan_daemon.py` | privacy by construction, asserted end to end |
| the next wake is the expression, then the idle clock; a silent client does not block the room | `test_stackchan_daemon.py` | no fixed tick; the deadline is a value |
| **a greeting logs one frame row, and with no port `sent` is `False`** | `test_stackchan_daemon.py` | ⛔ **with no `--port` the line says *would have sent*; nothing leaves the process** |
| **an unchanged event logs no second frame** | `test_stackchan_daemon.py` | ⚠️ **the frame is not a stream** — the same state is one line, not one per event |
| **the configured port receives the logged line** | `test_stackchan_daemon.py` | ⚠️ **the log row and the bytes come from one call to the codec**, so they cannot drift |
| a missing port is `sent: false`, not a refusal | `test_stackchan_daemon.py` | ⛔ **a replug can rename the console**; a missing path must not be fatal under `KeepAlive` |
| without a port, nothing is written anywhere | `test_stackchan_daemon.py` | the device is optional, and that is still the default |
| a write that returns short is not `sent` | `test_stackchan_daemon.py` | ⛔ **`sent` is the host's tty taking the whole line — not the board receiving it** |
| **the second transition streams the pose line, and its frame carries `gesture: null`** | `test_stackchan_daemon.py` | ⛔ **`PlayGesture` blocks the main loop for seconds, and the poses written meanwhile are applied late** — one happening must not move the head twice |
| **the first transition after a start is not streamed** | `test_stackchan_daemon.py` | ⚠️ **this host does not read the head's position**; a first line naming an unknown start is a flight to that position |
| **one stream opens the port once, not once per pose** (0.19.15) | `test_stackchan_daemon.py` | ⛔ **the open/write/close loop was measured to wedge the daemon inside `open()`** — where no signal reaches it |
| **a port that takes nothing ends the stream** (0.19.15) | `test_stackchan_daemon.py` | each write is bounded by `PORT_WAIT = 0.5`; ⛔ **waiting with no upper limit is what stopped the daemon on 2026-10-19** |
| **a port that cannot be opened leaves the gesture in the frame** (0.19.15) | `test_stackchan_daemon.py` | the board plays it instead, and the room carries on |

**Twenty-one more hold the client — the process a hook would run:**

| the check | where | what it is for |
|---|---|---|
| a full hook payload yields exactly `session` and `event` | `test_stackchan_hook_client.py` | ⛔ **the prompt, the cwd and the tool input never reach the line** — privacy by construction, not by policy |
| a payload without the two fields, or with an unknown event, is dropped | `test_stackchan_hook_client.py` | ⚠️ **two gates, not one** — the daemon refuses the same cases, so a silent loosening on one side still rings on the other |
| the line parses against the daemon's schema, and the socket path is spelled once | `test_stackchan_hook_client.py` | the client and the daemon share `parse_request` and `socket_path` rather than a copied contract |
| a real payload reaches the room, and its prompt is absent from the daemon's log | `test_stackchan_hook_client.py` | the same claim as above, asserted end to end |
| no daemon, malformed input and an over-long input are silent with exit 0 | `test_stackchan_hook_client.py` | **a hook must never fail the turn it is reporting** |
| the client does not wait for a reply | `test_stackchan_hook_client.py` | ⛔ **reading the answer would make the turn wait on the daemon** |
| **one daemon carries the phase across two separate hook processes** | `test_stackchan_hook_client.py` | ⛔ **this is why the bridge exists** — `Companion` holds state, and a hook does not |
| **two windows through two clients keep one gaze, and a background `Stop` is `distant`** | `test_stackchan_hook_client.py` | the focus rule, asserted across processes rather than inside one |

**Twenty-eight more hold the wire to machine 2 — the frame a gesture would cross on:**

| the check | where | what it is for |
|---|---|---|
| every symbol round-trips — the six face values (five and `null`) × six lights × the six gesture values × the five sound values (four and `null`) | `test_stackchan_wire.py` | ⚠️ **1,080 frames counted, 125 of them carrying no `null`**, and not one carries a number |
| a frame is one ASCII line, and the two nullable fields are present as `null` | `test_stackchan_wire.py` | ⛔ **a missing field is filled by the receiver's memory**; `null` is a value |
| an unknown key is refused — a `prompt` cannot ride along | `test_stackchan_wire.py` | the same rule the socket holds, asserted on the wire |
| an unknown value is refused in each field | `test_stackchan_wire.py` | ⛔ **a word outside the table is outside the vocabulary** |
| `light` is required and never `null`; malformed, two-line and over-long input are refused | `test_stackchan_wire.py` | the light is the one channel that is always on |
| **`sound` is required, may be `null`, and its values are four words** | `test_stackchan_wire.py` | ⛔ **`null` is *this frame is silent*, not *keep the last one*** — a sound is an event, and the receiver must not remember it |
| **a sound is a word and not a number** | `test_stackchan_wire.py` | ⛔ **`1000` would be a frequency**, and a frequency has no place on this wire |
| the encoder refuses what the decoder refuses | `test_stackchan_wire.py` | ⛔ **two rules would let one side be fixed alone** |
| the schema, the codec and the firmware's literals name the same words | `test_stackchan_wire.py` | the contract is a copy in three places, and this is where it rings |
| the firmware source has no angle for either machine | `test_stackchan_wire.py` | ⛔ **a guessed angle is indistinguishable from a measured one in the source** |
| the wire imports nothing but `json` and `dataclasses` | `test_stackchan_wire.py` | no clock, no socket, no environment — and ⛔ **no import of machine 1's protocol** |
| the mock records and answers nothing; `send` returns `None` | `test_stackchan_wire.py` | ⚠️ **green means the protocol computes, not that anything moved** |

**Thirteen more hold the frame the room would send — the last seam before a wire that does not exist:**

| the check | where | what it is for |
|---|---|---|
| the first decision always emits, and it fills in a face the decision did not name | `test_stackchan_outbound.py` | ⚠️ **the machine's state before the first decision is unknown**, so the first frame establishes it |
| a decision that changes nothing emits no frame | `test_stackchan_outbound.py` | ⛔ **a hundred evidence events produce one frame** — this is not a stream |
| a change of light alone emits a frame carrying no face | `test_stackchan_outbound.py` | ⛔ **the reason does not partition state changes** — `PostToolUse` returns `blocked` to `working` with reason `OBSERVED` |
| a gesture alone emits a frame | `test_stackchan_outbound.py` | the neck is the one channel that is not part of the state |
| **a sound alone emits a frame, and the frame is not repeated** | `test_stackchan_outbound.py` | ⛔ **a sound is an event and not part of the state** — `Outbound` remembers no sound, where it remembers the light |
| **each transition carries its own word, and two are silent** | `test_stackchan_outbound.py` | ⚠️ **`UserPromptSubmit` and `SessionEnd` say nothing** — *a transition makes a sound* is not the rule |
| every emitted frame parses against the contract, and round-trips on the wire | `test_stackchan_outbound.py` | the frame is a `Frame`, not a sentence, and the codec is the only spelling of it |
| **no number crosses** | `test_stackchan_outbound.py` | ⛔ **every field is a word from a closed table or `null`** |

✅ **And since 0.19.8 a transport exists** — `--port PATH`, one open per frame — so *the daemon opens no transport* is no longer true. ⛔ **What is still true is that no test opens a device**: the four port tests open a regular file, and the delivery to the board was observed by hand, once. **These forty-seven tests** (twenty-eight on the wire, thirteen on the frame, six on the daemon's frame row and its port) **hold a frame, a contract and a way out of the process; they hold no machine.**

⚠️ **What none of this tests is machine 2.** **Not one claim is about a machine** — the mapping needs no measurement, the motion does. **The layer has been registered as a hook since 2026-10-18**, and the phase, the timers and the gaze live inside one process, so that registration is a client and a daemon rather than the CLI. **Both ends of that bridge exist, and both are installed** — a launchd user agent starts the daemon at login, and all thirty-three hook events call the client — **but this directory tests the two processes, not the installation.** ⛔ **Nothing here rings on the launchd job or on `settings.json`:** an installation is a place on one host, and it is recorded on `docs/stackchan-daemon.md`, not checked. ✅ **And since 2026-10-18 the installed daemon writes the frame both ways** — as a log row and, because the plist names a port, to the board's console — **with `sent: true` when the host's tty took the whole line.** ✅ **The board printed the same frame from its own console**, which is what makes it delivery rather than a write; ⛔ **and the board refused the gesture, exactly as its source says it must.**

## A second line type, and what it does not cover (0.19.6, read by the board since 0.19.7)

**`engine/backend/protocol_stackchan_pose.py` arrived — the line a host would write every tick.** Forty-two tests were added; the count moved from 397 to 439. ⛔ **It is not the transition frame, and the two are kept apart on their first word** (`pose` against `{`): that one is written when the visible state changes and carries symbols; this one is written every tick and carries numbers — **mix them and the frequent line buries the rare one.**

| the check | where | what it is for |
|---|---|---|
| 7 × 7 poses round-trip, both bounds included | `test_stackchan_pose_wire.py` | ⚠️ **the endpoints are in the grid, not only the middle** |
| the checksum is hand-computable — `pose 50 894` is `*01` | `test_stackchan_pose_wire.py` | ⛔ **the same three lines can be written in C++ on the board**; a check nobody can recompute is a number a reader has to trust |
| a corrupted byte is refused as `bad-checksum` | `test_stackchan_pose_wire.py` | ⛔ **12.5° of error would otherwise move** — the machine's own envelope does not catch it, because the corruption stays inside the range |
| `50` → `05` is refused by the canonical-spelling rule, not by the sum | `test_stackchan_pose_wire.py` | ⚠️ **a sum does not catch a transposition**; pinning one spelling closes the part of it that can be closed |
| `123` → `321` is accepted | `test_stackchan_pose_wire.py` | ⛔ **a named limit, asserted so that no one later mistakes it for a property** |
| a line of the other kind is refused as `not-pose` | `test_stackchan_pose_wire.py` | the two line types cannot be read as each other |
| both fields are always present; half a pose and a spare field are refused | `test_stackchan_pose_wire.py` | ⛔ **a missing field is filled by the receiver's last value** |
| the contract's pattern accepts every line the codec writes, and refuses the rest | `test_stackchan_pose_wire.py` | ⚠️ **the contract sees shape and the codec sees the sum; neither covers the other** |
| the module imports only `dataclasses`, `typing` and two files of its own layer | `test_stackchan_pose_wire.py` | no clock, no socket, no environment — and ⛔ **no import of machine 1's protocol** |
| neither machine 1's numbers nor this unit's zero points are in the source | `test_stackchan_pose_wire.py` | ⛔ **the zero points are the machine's and live in its NVS**; here they would be a copy, and a copy is this repository's own definition of a defect |
| the mock records and answers nothing | `test_stackchan_pose_wire.py` | ⚠️ **green is the protocol's, not the machine's** |

⛔ **What it does not cover.** ✅ **The board reads this line since 0.19.7** — `projects/stackchan-firmware/main/main.cpp` carries its own sum, its own spelling rules and its own limits — **and no test here reads that C++**: `idf.py build` is run by hand, and the only thing checking the two ends agree is the literal comparison in `test_stackchan_wire.py` for the *other* line. ⚠️ **20 ms has survived this unit once** — 678 poses over six round trips of ±5°, 0 refused, 0 clamped — **and that is one amplitude, not the failure mode**: the datapoint on record, `MOVE_SETTLE = 1.0`, is that a command arriving mid-move took both axes down, and six round trips did not reproduce it. **The order of the two fields is invisible to the checksum**: a line with yaw and pitch swapped is well-formed, and the head moves wrongly. ✅ **Since 0.19.10 a host in this repository writes these lines** — `projects/stackchan/neck/` — **and pose lines from here have crossed the wire**: 822 applied, 0 refused, 0 clamped, in seven segments on 2026-10-18. ⚠️ **A later run the same day replayed the same seven segments at one-third the length, after the firmware's write changed**: 410 applied (228 poses plus 182 held), 0 refused, 0 clamped.

## The machine's own parser, compiled and run (0.19.8)

✅ **`tests/test_stackchan_frame_parser.py` compiles `projects/stackchan-firmware/command_frame.cpp` with `clang++` or `g++` and runs it** — seventeen claims about which lines the parser accepts and which it refuses.

| the check | where | what it is for |
|---|---|---|
| a well-formed frame is accepted, and its fields come back | `test_stackchan_frame_parser.py` | ⛔ **until 0.19.8 the parser refused every well-formed frame** — it failed to step over the closing brace — **and the literal comparison in `test_stackchan_wire.py` passed it** |
| an unknown key, an unknown word and an over-long line are each refused | `test_stackchan_frame_parser.py` | the board refuses what the host's decoder refuses |
| every gesture word the contract names parses — and none of them is played here | `test_stackchan_frame_parser.py` | ⛔ **`apply_command` is a stub and `main.cpp` is never compiled by this test**, so the measured posture table that plays a gesture is checked by no check at all |
| the enum still matches the words the schema names | `test_stackchan_frame_parser.py` | the contract is a copy in three places, and this is the second place it rings |

⛔ **It does not build the firmware.** `main.cpp`, `leds.cpp`, `servo.cpp`, `display.cpp` and `sound.cpp` are never compiled here; `idf.py build` was run by hand on 2026-10-18 and no check repeats it. **What this test is for is the gap it was written into**: a copy checked against a copy had passed while the parser refused every frame in the only place that mattered.

## The engine's trajectory, streamed to the machine (0.19.10)

✅ **`projects/stackchan/neck/` arrived** — the first host in this repository that writes the pose line. **`motion.py` is the pure half**: two poses and a duration go in, and the samples `engine/trajectory/plan.py` produces come out, encoded by `protocol_stackchan_pose.encode` so there is one spelling of a line and not two. **`__main__.py` is the edge**: it follows each sample's own time with absolute deadlines and writes one line per tick with `os.open`/`os.write`/`os.close`, the daemon's path. **Forty tests now hold it: 0.19.11 added ten — seven in `test_profile.py` for the spring family, three here — and the count moved from 483 to 493; 0.19.14 added eleven here, when the gesture table and the stream rule arrived.**

| the check | where | what it is for |
|---|---|---|
| both ends are exactly the poses named, for all five measured postures | `test_stackchan_neck.py` | ⛔ **rounding through tenths closes the gap** — `plan` puts the ends exactly, and the round trip through integers cannot move them |
| every emitted line decodes back to its pose | `test_stackchan_neck.py` | the column is built with the wire's encoder, and this asserts the wire agrees |
| the step count follows `duration / period`, and the times are the engine's | `test_stackchan_neck.py` | ⚠️ **the sender follows `Step.t`, not `period`** — otherwise a duration that does not divide evenly drifts, silently |
| the same input gives the same bytes | `test_stackchan_neck.py` | no clock, no random, no environment — the purity scan sees imports, this sees the output |
| no sample leaves the interval, and a moving axis never turns back | `test_stackchan_neck.py` | interpolation fills between two ends; it does not overshoot them |
| the step sizes rise and fall, with the peak in the middle third | `test_stackchan_neck.py` | ⚠️ **this is the mechanical meaning of "not stiff"**: velocity starts and ends at zero. ⛔ **It is not a claim about how the motion looks** |
| a channel that does not move stays exactly there | `test_stackchan_neck.py` | ⛔ **`0.0 * inf` is `nan`, and `nan > limit` is `False`** — the trapezoid's jerk is infinite, and this is the trap `plan._scale` documents |
| the pure half holds no machine number | `test_stackchan_neck.py` | over **AST constants**: only `0`, `1`, `2` and `10.0` may remain — **the zeros, the envelope and the floor are the board's** |
| a dry run writes every line and nothing else | `test_stackchan_neck.py` | the lines can be inspected without a machine |
| waiting returns the overshoot, not a verdict | `test_stackchan_neck.py` | ⛔ **the first version could only say "late", and it said it 31 times out of 31** — a check that always answers the same thing is not a check |
| the edge names exactly one destination, and refuses a pose the line cannot carry | `test_stackchan_neck.py` | `--port` or `--dry-run`, never both, never neither; beyond 1800 is a refusal |
| **the five postures here are the five in `main/main.cpp`** | `test_stackchan_neck.py` | ⛔ **the table is a copy, and the board's is the source** — the check reads the C++ and compares tenths of a degree, so a table that moves turns this red |
| a plan starts where it was told and ends where the table says | `test_stackchan_neck.py` | the caller's start is the head's last pose, not the table's idea of where it should be |
| `nod` passes through its down posture and comes back | `test_stackchan_neck.py` | it is two segments, chained |
| `chain` keeps one timeline and one seam | `test_stackchan_neck.py` | ⛔ **two samples at the seam would stop the head for one tick**, and that is what the author called 「動きが硬い」 |
| every posture the layer can choose can be carried by the line | `test_stackchan_neck.py` | the table and the protocol's bounds agree |
| the duration grows with distance and has a floor | `test_stackchan_neck.py` | ⚠️ **a number chosen here, not measured**; below the floor a short move becomes a snap |
| a stream starts at the event's own time | `test_stackchan_neck.py` | no warm-up, no first tick at `period` |
| a stream writes every step once, then holds | `test_stackchan_neck.py` | ✅ **the board releases torque after 500 ms of silence**, so the last pose is repeated |
| a line is late only past half a period | `test_stackchan_neck.py` | ⚠️ **a fixed tick would call every line late or none** — the rule is a value, not a verdict |
| a new motion starts from the line that was actually sent | `test_stackchan_neck.py` | ⚠️ **an interrupted plan's end is not where the head is** |

⛔ **What it does not cover, and what only the machine could say.** The stream is only as good as its timing: **min-jerk's peak is 1.875× its average**, so a duration too short for the servo runs ahead of the head — a 0.6 s move over 47° did exactly that, applied every line (73, 0 refused, 0 clamped) and was still travelling when the torque released. ⚠️ **The first reading of that was wrong**: the 40°/s it was blamed on was `kPoseSpeed = 100`, a cap this repository's own firmware was writing, not the servo's ceiling; the stock's call (about 175°/s measured) is what the firmware writes now, and the plan's durations are about `degrees / 60`. **No test here can see any of it**, because no test here has a servo. **The author's judgement of the motion is the next word, and it is not in this file.**

✅ **Since 0.19.14 the same rule follows the plan inside the daemon** — `stream.py` — so the CLI edge and the daemon cannot drift apart: one implementation of *which line is due, which one is late, and how long the last one is held*. ⛔ **That is a claim about one implementation, not about a motion.**

## The face, drawn and checked — and the defect no check here could see (0.19.12)

✅ **`tests/test_stackchan_face.py` arrived with the screen.** Nine tests; the count moved from 493 to 502. Like the parser test, it compiles a C++ file on the host — `face_bitmap.cpp`, which carries no IDF — and runs it.

| the check | where | what it is for |
|---|---|---|
| none of the five faces is blank, and `kNone` draws nothing | `test_stackchan_face.py` | ⚠️ **a blank screen is not one of the five faces**; `none` is what the wire calls *no expression* |
| the mouth is 90 × 6, in the same place for every emotion | `test_stackchan_face.py` | ⛔ **the vendor's `DefaultMouth` has no `setEmotion`** — a mouth that moved per emotion would be an invention, not a copy |
| the two eyes are mirror images about `x = 160` | `test_stackchan_face.py` | the vendor negates the right eye's rotation; and ⚠️ **the mirror of pixel `x` is `319 - x`, not `320 - x`** — the off-by-one that put the eyes half a pixel off the mouth |
| nothing is lit outside the eyes and the mouth | `test_stackchan_face.py` | the background is the vendor's `secondaryColor` |
| **the edges carry intermediate values** | `test_stackchan_face.py` | ⛔ **this is the anti-aliasing, asserted**, because a 1-bit circle is a staircase and the author saw it |
| the sleepy eyes are the most closed, and the lid follows the vendor's integer weights | `test_stackchan_face.py` | `-map_range(weight, 0, 100, 0, 20)` in `int` arithmetic: weight 72 lifts the lid by 14, not 14.4 |
| `happy` and `greeting` are one drawing, and the other four are distinct | `test_stackchan_face.py` | the host decided two words share a face; the screen does not quietly disagree |

⛔ **What it cannot see is where the defect was.** `display.cpp` — the SPI driver, the panel's init sequence, the two I2C rails, and the DMA — **is compiled by no check.** `idf.py build` is run by hand, and on 2026-10-18 a tear lived in it for four rounds of reporting while this directory stayed green: the eight-row chunk buffer was refilled before the DMA had finished reading it, so *every shape on the screen had a thinner copy of itself below it*, and the copy sat further below the lower the shape was. **The drawing was right the whole time; what was wrong was the wire underneath it.** ⇒ **A `-2` row shift was briefly written into `face_bitmap.cpp` on the strength of the symptom, and removed again** — the comment where it stood records why it must not come back. ⛔ **And these tests did not catch it, because they were moved with it**: the row boxes were re-pinned to the shifted drawing and the suite stayed green. **A test written from the same belief as the code cannot be the check on that belief** — what caught it was one photograph, on the glass.

## The voice — a word that leaves the board (0.19.13)

✅ **The fourth field arrived, and the board plays it.** Eleven tests were added — **three on the wire, three on the frame, one on the layer, and four rows in the parser's table** — and the count moved from **502 to 513**.

| the check | where | what it is for |
|---|---|---|
| `sound` is a required key, may be `null`, and its values are the four words | `test_stackchan_wire.py` | ⛔ **a missing key is refused like the other three** — a field the receiver fills in is a field that can be wrong silently |
| a sound is a word, not a number | `test_stackchan_wire.py` | ⛔ **a frequency has no place on this wire** — the word-to-tone table is the board's |
| a sound alone is a frame, and the sound is not remembered | `test_stackchan_outbound.py` | ⛔ **`Outbound` remembers the face and the light; it must not remember the sound**, because a sound is an event |
| each transition carries its own word, and two transitions are silent | `test_stackchan_outbound.py` | ⚠️ **`UserPromptSubmit` and `SessionEnd` say nothing** |
| the sound switch is off by default, and the words it lets through are the wire's four | `test_stackchan_behaviors.py` | ⛔ **two lists of four words would drift**; the wire's is the one the board reads |
| a frame without `sound` is refused by the board's own parser, and `"horn"` is an unknown value | `test_stackchan_frame_parser.py` | the board refuses what the host's decoder refuses, spoken by the other end |

⛔ **What none of them can see is the amplifier.** `sound.cpp` — the AW88298's register table, its reset line on the display's expander, the I2S channel and the four tones — **is compiled by no check**, and no test here opens a device. ⚠️ **The tones are choices, not measurements**, and the only thing that has judged them is one pair of ears: **on 2026-10-18 the board played all four from `bench sound`, and the author heard all four** (`projects/stackchan-firmware/records/2026-10-18-the-voice.md`). ⛔ **That says a sound was made. It says nothing about pitch, loudness, or whether a word suits its transition.**

## The rule that holds this directory — applied to us

**`CLAUDE.md`'s Tests section must not say "nothing yet" while test files sit on disk.**

That state is not hypothetical — **a sister repository is in it right now**: seven test files and fifty-four tests on disk, and its `CLAUDE.md` still reads "not yet built". **So when the first test landed here, that section changed in the same commit.** A section that describes a directory rather than reading it is how that happens.

## What is checked today, and where

**The three checks that are not tests do not live here.**

- **`claude plugin validate --strict .`** — the manifest fields and the two versions against each other.
- **`python3 tools/check_i18n.py`** — the document mirrors. It has its own `--self-test`.
- **`python3 tools/check_vocabulary.py`** — the vocabulary table. It has its own `--self-test`.

⚠️ **The first two see five of the fifteen conventions this repository follows. Nothing checks the other ten.**

⛔ **The third guards a rule that is not one of the fifteen.** It arrived on 2026-09-28 with the mapping, for a rule this repository wrote for itself that day — *do not invent a word* — **and the fifteen predate it.** ⇒ **Counting it against the fifteen would be counting a different thing**; what it reads is the table's shape (columns, degrees of freedom, the two path columns, and that the two mirrors agree), **and never whether the mapping is right.**

⚠️ **Its seventh column arrived on 2026-10-15** — the machine a row was written on. **The column is a place, not content: not one word was added to the vocabulary.** ⛔ **And the checker asks only that the path exists.** Whether `engine/backend/protocol.py` is *machine 1's* is not something a path can say, and the checker's own list of what it cannot catch says as much.

⚠️ **And it found its own author's mistake first.** Its V5 compared the mirror's header row too, where the column *names* are translated — so three correct mappings rang as four violations. **A check that has just been written is the first thing to disbelieve.**

## Running this directory

```
python3 -m pytest tests/
```

⚠️ **Green means the mechanism computes what it was told to compute.** It means nothing about whether anything is *there* — see `docs/verification-boundary.md`. **What is alive is not a thing a test can be written for.**
