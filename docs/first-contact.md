<!-- i18n-version: 1.0.0 | canonical: docs/first-contact.md | translated: 2026-09-28 -->

**Language:** [English](first-contact.md) | [日本語](first-contact-ja.md) | [中文](first-contact-zh.md)

# First Contact — the first hour at the machine

⚠️ **This page is a checklist. It is not the safety argument** — that argument is `CLAUDE.md` § Safety, and it is where the reasoning for these items lives. What is here is only what you would otherwise have to reconstruct from a design note while standing in front of the box.

⛔ **Not one item on this page has been done.** There is no machine, so none of these checks has been run. **Every line is either quoted from a document or an inference, and each one says which.**

⛔ **And the risk this page carries is its own tidiness.** A list of questions arranged this neatly can read as though the questions have been answered. **Not one of them has. What is arranged here is the asking.**

## Before you plug anything in

- ⛔ **No serial layer exists in this repository.** Nothing here opens a port. Any code you run at the machine is code written on that day.
- ⛔ **Decide now how you will cut the power.** Nothing in the protocol stops a motor — the details are under *What "stop" is, here* below.
- ⛔ **Emergency stop is not standard equipment.** The eBreak is a separate purchase, and the vendor's own CE declaration cites EN 60204-1:2018 — the standard that requires one.

⚠️ **And one inference, which is the reason this section comes first.** On an Arduino UNO, opening a serial port asserts DTR and resets the board. The upstream firmware boots with `Disable1..3 = 0` — **all three axes enabled, target 512.** ⇒ **Opening the port can itself move the machine.** ⚠️ **This is an inference from the general behaviour of an Arduino UNO plus a reading of the upstream `.ino`. It has not been checked on a DOF Reality box, and CH340 clones may behave differently.** Treat it as a reason to have the platform clear before you open anything, not as a measured fact.

## The first hour — four questions

⚠️ **These four were written down as the things to settle before trusting any protocol document, including this repository's.** They are quoted from the design survey, which is not distributed with this repository.

| | question | what is already known |
|---|---|---|
| **(a)** | **Which generation is the box?** | The earlier generation is serial (Arduino UNO). The current one is an STM32 reached over HID. The vendor's own firmware tool says it works only with controllers produced since November 2021. |
| **(b)** | **Does it appear as a serial port?** | If it does not, everything the protocol documents describe is unavailable and the backend design changes. ⚠️ **The current manual still says to start `SMC3Utils`**, which suggests the serial path survives — **that is an inference and nothing backs it.** |
| **(c)** | **What does `[ver]` return?** | **The upstream firmware returns 70.** ⚠️ **One H3 on the public record returned `v33.07`.** A different value does not mean the box is broken; it means the firmware is not the upstream firmware. |
| **(d)** | **10-bit or 12-bit?** | The vendor's firmware page says the mode can be changed. ⛔ **This one is not a detail — see below.** |

### (d) decides what every number in this repository means

The vendor's tool page says: *"You can change your control box mode: 10 bit or 12 bit."* A secondary source gives **10-bit = 0–1023** and **12-bit = 0–4095**.

**Every count in this repository is in 10-bit counts** — the neutral **512**, and the default envelope **190–833** (`engine/trajectory/limits.py`, `Envelope`). ⇒ **A box in 12-bit mode makes those numbers mean something else, silently, with nothing to ring on it.** ⚠️ **What the current STM32 generation actually does in 12-bit mode is not known** — one guess on the record is that it is not supported at all.

⛔ **And "1 count = N degrees" is written down nowhere, and cannot be.** Counts are raw sensor readings. The range comes from the linkage and from `Clip Input` / `Max Limits`, both of which the vendor expects the owner to change. **Measure the limits per axis, on this machine.**

### And (c) is not a formality either

⚠️ **A third party measured an H3 and reported three things.**

- `[ver]` returned **`v33.07`**, not 70 — **and the upstream `.ino` was still a usable model of the protocol.** ⇒ A differing version is a warning, not a stop.
- **`rd` responses are prefixed with a debug string.** The response to `[rdS]` does not begin with the 5-byte frame. ⇒ **Do not read fixed 5-byte frames; scan the stream for `[` … `]`.** ⚠️ A widely-copied third-party library takes `buffer[:5]` unconditionally, and would read a debug string as a position.
- The measured `InputClip` on that machine was **220..803**, not the manual's default 190..833. ⇒ **Limits are per-machine. Read them; do not assume them.**

## The one check that gates everything

**Can the port be opened at 500000?** Do this before anything else, because **if it fails, the backend design changes.**

1. Does `serial.tools.list_ports.comports()` show a `/dev/cu.*` entry?
2. Does `serial.Serial('/dev/cu.XXX', 500000)` raise?
3. **Try 115200 as well** — a jumper switches the rate, and if that path works it is the safer main line.
4. ⛔ **Record which chip the adapter uses — CH340 or FTDI.** **"It opened" is not the measurement. Which chip it opened on is.**

⚠️ **"It opened" is not the same as "it opened at 500000."** On macOS, pyserial reaches 500000 through `IOSSIOSPEED`, and it sets **38400** with `tcsetattr` *before* raising the rate. ⇒ **There is a 38400 window immediately after the port opens.** If the box is already streaming feedback, frames crossing that window are corrupted — and a parser that does not check for `]` will read them as positions. ⚠️ macOS offers few ways to ask a port what rate it actually reached, so **there is no guarantee except a measurement.**

⚠️ **And "the port opened" is not "the protocol was understood."** `flush()` (tcdrain) was **measured blocking forever on a macOS pty**. That is the one place the Mock cannot stand in for the machine. ⇒ **If `flush()` hangs, that is not a bug in your code — that is the divergence this repository warned about.**

## What the protocol will surprise you with

⚠️ **All of these are read from the upstream firmware source and from a third-party library. None has been checked on a DOF Reality box.**

- ⛔ **The scale you read at is not the scale you write at.** Position is **sent** as 0–1024 in two bytes, and **read** as `Feedback/4`, `Target/4` — one byte, **0–255**. ⇒ **Sending a position you just read back flies to a quarter of that position.**
- ⚠️ **Two sources disagree about the order of the two values in a feedback frame.** The upstream firmware sends feedback first; a third-party library's parameter names assume target first. **Which is right on a DOF Reality box is unconfirmed.** ⇒ **Do not pick one; arrange a test that can tell you.**
- ⚠️ **`[mo1]`–`[mo3]` overwrite each other.** The enable flag is a single variable, so sending `[mo1]` and then `[mo3]` **stops Motor 1's stream.**
- ⛔ **The box returns no errors.** There is no NAK and no error frame, and unknown commands are **silently ignored.** ⇒ **Silence is not success.** The only way to know a read worked is to look at the value.
- ⚠️ **The upstream command table is a floor, not the whole.** The vendor's firmware is a derivative of the upstream sketch rather than the sketch itself, and at least two commands observed in the vendor's own protocol are not in the upstream table at all. ⇒ **"There is no stop command" is a conclusion about upstream.** Whether the vendor's firmware has one is unknown until the command space is swept on a real box.

## The machine side — nine things never confirmed

⚠️ **Every row is "not checked."**

| # | what | what is known now |
|---|---|---|
| 1 | **The generation of the box** | The finding that most changes the design. "The H3 is a USB serial device" may not hold for the current generation. |
| 2 | **Axis-to-motor correspondence** | **No canonical form exists.** Three independent pieces of software all say the user decides. **The sign of each axis depends on the wiring** — do not bake one in as a constant. |
| 3 | **The range of each axis** | **Not a protocol constant, and it cannot be.** The upstream firmware contains the word "degree" zero times. |
| 4 | **Payload** | **Four sources disagree, and the vendor publishes two figures at once.** Do not write "200 kg" as the rating. |
| 5 | **The e-stop** | Whether the eBreak cuts power or sends a signal, and how the box recovers from a limit. |
| 6 | **What `[mo0]` does in real time** | Whether anything stops immediately is unconfirmed. **Until it is checked, do not write "there is an emergency stop."** |
| 7 | **Whether the vendor firmware is SMC3-compatible** | The earlier generation is settled. Whether the current STM32 firmware derives from SMC3 is written nowhere by the vendor. |
| 8 | ⛔ **Balance, and the condition under which the platform leaves the floor** | **This is the row that exists nowhere else.** The vendor calls balancing a **mandatory** step, done by disconnecting both front motor arms with one or two people — **not automatable** — and writes that **the best counterbalance is the rider's own weight.** **This machine's balance is designed for a person sitting on it.** |
| 9 | **The PID gains and the real tracking performance** | Only the machine can say. |

⚠️ **And on row 8, do not skip the decision it forces.** An owner reported the platform **lifting off the floor**, and the same owner explains why the vendor's own motion is gentle: it lifts when driven hard. ⚠️ **"One centimetre" is a single visual estimate, not a measurement, and it is a report of one event.** Which angle, which acceleration and which mass distribution cause it **cannot be written down at a desk.**

## The host side — seven things never confirmed

| # | what |
|---|---|
| 1 | Does 500000 baud work on the real machine? |
| 2 | Does the WCH vendor driver implement `IOSSIOSPEED`? |
| 3 | Does Apple's bundled driver actually claim the CH340 board in hand? (That the bundled driver's `Info.plist` **lists** the CH340 vendor/product pair is confirmed — but it lists only two pairs in total. **Whether it claims the actual board in hand is a measurement, and has not been made.**) |
| 4 | **How long does `flush()` (`tcdrain`) actually wait on the real machine?** |
| 5 | Does reading `[mo1]`–`[mo3]` feedback every 15 ms hold up — dropped frames, reordered frames? |
| 6 | How far apart do the Mock and the machine turn out to be? |
| 7 | ⛔ **Re-measure the cycle on this machine.** The achievable period is tier-dependent and varies with machine and load. **The number in the design notes was not measured on the machine you will use.** |

## What "stop" is, here

⛔ **There is no stop command in the protocol.** What exists:

| command | what it actually does |
|---|---|
| `[mo0]` | stops **reporting** |
| `[sav]` | writes EEPROM |
| `[ena]` | **returns from a forced stop** — it does not stop anything |
| stopped sending | torque falls to about a quarter after 15 seconds — **and the motors do not stop** |
| driving a target | the box servos there — **that is not the same as stopping quickly** |

**The only "stop" the vendor ships is a mode in the vendor's own host application** (`set the Mode to Off`). **This host is not that application.** And when one of the three axes enters a forced stop, **the other two can no longer be operated** — the vendor's own phrase is `one motor locks all`.

⇒ **The stop you will actually use is the power switch.** Know where it is before you open a port.

## ⛔ The ending that must not be misread

**This step cannot be defined by success.** "It worked" is an ending. "It did not work" is also an ending — the backend design changes.

⚠️ **And there is a third ending, which is the one most likely to happen: the box opened, and the machine did not move.**

⛔ **When that happens, nothing has been finished.** The port opening is a fact about a USB device. **Reading "it opened" as "it moved" is the easiest mistake to make on this page** — and a green log makes it easier, because a log can only contain what left the host, **never whether anything moved.**

**What to write down:**

- the results of the port check — what `comports()` showed, whether it raised, **and which chip**
- the nine machine-side items — **what was learned and what was not**
- the seven host-side items
- ⛔ **and what the machine did.** This is the one thing no log can carry.

## What is not here

- ⛔ **No serial layer.** `engine/backend/` frames, gates and transmits to a mock, and stops there. Everything above is a list of work, not a description of code.
- ⛔ **Nothing on this page rings on a check.** It is prose, and **this repository's own definition of a defect is a rule that nothing rings on.** ⚠️ **A checker was considered and not written** — these are confirmations performed once, by hand, at a machine, and a check asserting that a list of strings was typed would be noise in the shape of a check. ⚠️ **The cost is real: this page can go stale and nothing will say so.**
- ⚠️ **This page is not the record vessel.** When there is something to record, it goes to `projects/` — see `CLAUDE.md`.
