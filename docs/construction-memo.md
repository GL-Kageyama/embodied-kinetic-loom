<!-- i18n-version: 1.7.0 | canonical: docs/construction-memo.md | translated: 2026-10-18 -->

**Language:** [English](construction-memo.md) | [日本語](construction-memo-ja.md) | [中文](construction-memo-zh.md)

# Construction memo — how this repository was built, and where it stands

⛔ **This is the only page in this repository that duplicates other pages on purpose.** A memo is a summary, and a summary is a second copy — **and a second copy is a shape this repository already calls a defect**: *write a list twice and only one of them gets fixed* (`tools/purity.py`, and the same sentence sits under the vocabulary rule).

⚠️ **So the duplication is not hidden. It is declared, and it comes with its own rule.**

- ⛔ **Every line below is derivable from somewhere else. Nothing here is a source.**
- ⚠️ **Which means: when a source changes, this page is the one that goes wrong.** **Read it as a map, never as a record.**
- ⛔ **And nothing rings on it.** This is the third page here with no checker — **and the cost is highest of the three, because a check written for this page would be checking the copy rather than the source, which is a check that rings on the wrong thing.**

## The two machines

| | **machine 1** — the DOF Reality control box | **machine 2** — Stack-chan |
|---|---|---|
| what it moves | a platform a person sits on | a head on a desk |
| the freedoms | **three** — `pitch` / `roll` / `yaw` | **two** — yaw and pitch. ⛔ **no roll** |
| the numbers | **10-bit counts** — neutral `512`, envelope `190–833` | ⛔ **degrees in, the servo's own counts out.** ⚠️ **the conversion between them is in no record** |
| host → machine | the vendor's protocol, over serial or HID | ⛔ **none on the unit in hand** |
| where its numbers live in code | `engine/backend/protocol.py` — `DofRealityWire`, `DOF_REALITY_ENVELOPE` | ⛔ **nowhere. No module exists.** |
| what this repository holds for it | the wire and the mock | the layer above the wire — events to faces. ⛔ **no numbers, no motion** |
| its checklist | `docs/first-contact.md` | `docs/first-contact-stackchan.md` |
| has a value from this repository ever reached it | ⛔ **no** | ⛔ **no** |
| has it ever moved | not known here | ✅ **yes** — the vendor's SETUP wizard drove it home and the owner watched, 2026-10-15 |

⚠️ **And machine 2 is two units, which is a trap of its own.** On 2026-10-04 a borrowed unit **was** driven from a host — a text shell over `/dev/cu.usbmodem1101`, `head <pan> <tilt>`. ⛔ **The unit in hand is not that unit.** It has no such path at all: the UART console is off, every port 1–65535 was scanned and is closed, and the device is a **client** of the vendor's cloud rather than a server on the LAN. ⇒ **Every "it works" dated 2026-10-04 belongs to a different, absent machine.**

## The ladder — what has landed, and what remains

**Six rungs. One rung = one commit = one version.** Each is justified by the one before it, and **the ladder may be stopped at any rung** — that is the point of cutting it this way.

| version | theme | state |
|---|---|---|
| **0.15.0** | 継ぎ目を掘る — **the seam** | ✅ landed. `wire.py` with `Command(axis, value)` and the three-method `Wire`; the gate's currency changed; `Envelope`'s default deleted (1 definition + 3 distributions); the silent-axis defect fixed |
| **0.16.0** | 語彙が機体を名乗る — **the seventh column** | ✅ landed. `references/` ×3; `COLUMNS` 6→7; V4 and V5 extended; self-test 14→16 |
| **0.17.0** | 空である理由 — **why the vessel is empty** | ✅ landed, **as a requirement only.** ⛔ The file, its name, its format and its location are still open |
| **0.18.0** | 機体2の最初の1時間 — **the second checklist** | ✅ landed. `docs/first-contact-stackchan.md` ×3 |
| **0.19.0** | 2台目の電線 — **the second wire** | ✅ **landed, as source only.** `protocol_stackchan.py`, `mock_stackchan.py`, `schemas/stackchan-command.schema.json`, `tests/test_stackchan_wire.py` (25), and `projects/stackchan-firmware/` — ⛔ **never built, never flashed; no transport is chosen, and the daemon does not open it** |
| **0.20.0** | ポートを開く — **the serial layer** | ⛔ **not started.** `engine/backend/serial.py` — the first port-opening code in this workshop — plus one named exemption in `tests/test_purity.py` |

⛔ **And the honest summary of where the route stands: it is not open.** ⚠️ **Four rungs built the socket, not the second plug.** `engine/backend/` holds `axis_map.py`, `cycle.py`, `gate.py`, `mock.py`, `protocol.py`, `transmit.py`, `wire.py` — **machine 1's wire** — **and since 0.19.0 `protocol_stackchan.py` and `mock_stackchan.py`, which frame one line for machine 2 and send it nowhere.** ⛔ **This repository cannot move a Stack-chan by one millimetre today.**

⚠️ **And the ladder is now longer than the plan says.** 0.17.0 decided a requirement and not a shape, so **the rung that decides the record's shape has no place on this ladder yet** — **it comes after 0.20.0, and it is not in the plan.** ⛔ **A summary that showed six clean rungs would be lying by omission.**

⚠️ **2026-10-18: a layer that is not on this ladder.** `projects/stackchan/` maps Claude Code's hook events onto six phases, the Pet's five faces, six lights and five candidate gestures — ⛔ **with no numbers for machine 2, so nothing is sent (`sent` is `False`), and one neck stays on one window when two or more run at once.** It arrived before 0.19.0 **and it is not a rung**: the ladder's order is unchanged, and **the row above changed instead — the repository now holds something for machine 2, and it is not a wire.** ⚠️ **It is wired to a hook as of 2026-10-18, and both ends of the bridge exist:** `projects/stackchan/daemon/` is the process that holds the state — a pure core (`room.py`) and a socket edge (`__main__.py`), twenty-four tests — and `projects/stackchan/hook/` is the client a hook runs, one process per event, silent and exit 0, twenty-one tests. ✅ **A launchd user agent starts the daemon at login and all thirty-three events call the client**, so a hook reaches the room. ⛔ **It reaches no machine.** **The installation is a place on one host, not a property of the repository** — the plist copy is `projects/stackchan/launchd/`, and the record, with the uninstall path, is `docs/stackchan-daemon.md`. ✅ **And since 0.19.0 the repository holds a wire for that layer too** — the frame, its contract, and the machine's end as source — ⛔ **so *it is not a wire* was true of that day and is not true now; what is still true is that no transport is chosen and nothing is flashed.**

## The traps

⚠️ **Ordered by how much time each one costs.** Every one of these was paid for once already.

| the trap | what it looks like | what it is |
|---|---|---|
| ⛔ **A Fresco Logic USB hub** | the device enumerates, the strings and the MAC read back correctly — and serial is dead | esptool reports `No serial data received` in every reset mode; pyserial reads **0 bytes at every baud rate**; some rates raise `OSError: [Errno 83]`. **It is diagnosed as a dead board.** Plug directly into the Mac — `Mac14,10` has no USB-A, so it takes a USB-C ↔ USB-C **data** cable |
| ⛔ **The port name is not an identity** | `/dev/cu.usbmodem1401` became `1101` when a hub was removed | ⚠️ **And the 10/04 records disagree with each other about which of `101` and `1101` was the Stack-chan.** **Identify by MAC** |
| ⛔ **`MOVE_SETTLE = 1.0`** | a command sent before the servo finishes moving stalls it, drops the power rail, and **takes both axes down** | **This engine sends a target every 15–20 ms.** ⚠️ **Whether that is survivable here is unmeasured** — and the one datapoint points the other way (`head 90 135` ended at `yaw=-1 pitch=-1`) |
| ⛔ **`flush()` (`tcdrain`)** | it does not return | **Measured blocking forever on a macOS pty.** ⇒ **The reason must stay in the docstring**, or the next reader adds it back "just in case" |
| ⛔ **pyserial on a macOS CDC device** | `TIOCSDTR` / `TIOCSRTS` raise **ENOTTY** | ⇒ **The host cannot use DTR/RTS to reset the board**, and the serial layer uses `termios` directly instead |
| ⛔ **A partial write** | `vmen on` arrives as `vmen o` and the shell answers nothing | **The single most likely cause of what the 10/04 record had been calling "the servo is unresponsive".** ⇒ **partial writes must be completed behind a `select` wait** |
| ⚠️ **The repository's own record can be wrong** | `HISTORY.md` 0.15.0 opened with *"nothing a user sees changes"* | ⛔ **The same entry documents that `pet_report.caveat` — a user-visible string in all three languages — changed.** **The entry was false on the day it was written.** ✅ **Corrected on 2026-10-15, under the heading it belongs to, with the old sentence left standing** — **a correction that erases its own subject is not a correction** (the shape 0.14.1 set) |

## The conventions — and where each one actually lives

⚠️ **Not restated here.** **`CLAUDE.md` is the canonical statement of every rule**, and a second copy would be the defect this page opened by naming. What is below is only **the part that is scattered** or **written nowhere**.

**The five checks, in the order they are run at each rung** — ⚠️ **the order is written nowhere else in this repository**:

```
python3 -m pytest tests/
python3 tools/check_vocabulary.py --self-test
python3 tools/check_vocabulary.py
python3 tools/check_i18n.py
claude plugin validate --strict .
```

⚠️ **`tests/README.md` lists the checks but not in this order, and it does not say to run them together.**

| what | where it is stated |
|---|---|
| the document rules, the vocabulary rule, the records rule, the safety section, the git rules | `CLAUDE.md` |
| the five checks and what each one sees | `tests/README.md` |
| the dated chronology, and every measurement | `HISTORY.md` |
| the version ledger — two manifests and the newest `HISTORY.md` heading | `.claude-plugin/*.json`, checked by `tests/test_versions.py` |
| ⛔ **the forbidden-import list** | `tools/purity.py` — **one list, two scanners** (`tests/test_purity.py`, `tests/test_pet_purity.py`) |

⚠️ **And two numbers that are measured, not fixed** — **every document that carries them must be re-counted at every rung**: the test count and the file count (`CLAUDE.md` Tests, `README.md`, `tests/README.md`), and the canonical-document count (`tools/check_i18n.py` prints it). **A count that is copied forward is a count that is wrong.**

## What this page does not do

- ⛔ **It is not a source.** **If this page and a source disagree, the source is right** — **and finding that out is the whole reason the first section is about how this page can be wrong.**
- ⛔ **It does not restate the rules.** **The one thing it does restate is the run order**, and it says why: nothing else holds it.
- ⛔ **Nothing rings on it.** ⚠️ **And unlike the two checklists, a checker here would be worse than none** — it would certify the copy.
- ⚠️ **It is not the record vessel, and it is not `HISTORY.md`.** **This page says where things stand now; `HISTORY.md` says what happened on a day.** ⛔ **Writing one and calling it the other is the mistake both pages warn about.**
