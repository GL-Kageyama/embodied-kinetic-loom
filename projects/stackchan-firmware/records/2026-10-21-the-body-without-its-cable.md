<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-body-without-its-cable.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-body-without-its-cable.md) | [日本語](2026-10-21-the-body-without-its-cable-ja.md) | [中文](2026-10-21-the-body-without-its-cable-zh.md)

# The body without its cable — 2026-10-21

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A row the daemon wrote is not a head that moved.

**What was counted.** One unit, one Mac, one access point, one socket, and **no USB cable at any point**: `/dev/cu.usb*` did not exist and `system_profiler SPUSBDataType` listed no JTAG device for the whole of the measurements below. **What was not counted:** the screen — ⛔ **no eye was in the room for any of this** — any Wi-Fi drop, any access-point restart, any change of the Mac's address, and any packet capture. Every number below was read from a log or from the board's own printed line.

## What was asked

「線を抜くよ？」 — then 「抜いた」 — then 「今後は、給電だけ用にどこかのコンセントに繋いでおくね」.

⚠️ **That last sentence is not a test; it is the arrangement the unit will live in.** ⇒ **A daemon that opens `/dev/cu.usbmodem101` has no path at all.** The link is not an improvement here; **it is the only route the body has left.**

## What was seen

**The Mac could not tell the absence of a console from the absence of a board.** The old job kept running and kept writing rows:

```
{"frame": "{...}", "sent": false, "accepted": null, "err": "ENOENT", ...}
```

⛔ **`ENOENT` is the host's own missing file, not the board's silence** — and until this page, nothing in the log distinguished the two.

**The board dials again by itself, every time the listener goes away.** Four swaps of the listener, four dials — **0.3 s to 4 s** after the port came back:

```
1792527289.638 accepted 192.168.0.19:50836
1792527566.570 accepted 192.168.0.19:50840
```

**The daemon now waits for it, and the body's whole conversation crosses that one socket.** `bench pos` was answered over the link, a frame's own acceptance line came back, and a gesture streamed — all inside one event, with the cable out:

```
{"link": "the board dialled in", "peer": "192.168.0.19:50841"}
{"position": [331, 500], "heard": true, "read": "bench: yaw=ok pitch=ok ...", "at": 9971.837653958}
{"neck": "look_up", "from": [331, 500], "to": [80, 500], "poses": 22, "at": 9971.837653958}
{"neck": "look_up", "applied": 22, "late": 21, "held": 27, "at": 9972.958619791}
{"neck": "look_up", "verdict": {"applied": 49, "refused": 0, "clamped": 0}, "at": 9974.254092916}
{"position": [96, 500], "heard": true, "read": "bench: yaw raw 491, angle 9.6 deg (zero 460) ..."}
```

✅ **The head moved.** Yaw was read at **33.1°** before the gesture and **9.6°** after it, and the board's own tally — **49 applied** — equals the host's **22 applied + 27 held**, exactly. ⚠️ **That agreement is the 0.19.38 rule holding over a socket as it held over a wire**, and it is the first time it has been checked with the cable out.

**And the wait that was measured on a wire did not survive the journey.** The first two runs heard nothing at all:

```
{"position": null, "heard": false, "read": "", "at": ...}
```

Ten `bench pos` queries over the link, timed at the listener:

| query | `bench: yaw=ok` arrived | the position line arrived |
|---|---|---|
| 1 | +0.441 s | +0.471 s |
| 2 | +0.640 s | +0.803 s |
| 3 | +0.331 s | +0.345 s |
| 4 | +0.461 s | +0.474 s |
| 5 | +0.479 s | **+1.045 s** |
| 6 | +0.723 s | +0.861 s |
| 7 | +0.299 s | +0.418 s |

⚠️ **Ten queries were sent and seven are in the table** — the last three were written as the capture was closed, and their answers were not recorded. ⛔ **That is a limit of this page, not a count of silent queries.**

⛔ **`PORT_WAIT = 0.5` is a number measured against a wire, and it does not travel with the question.** ⇒ **`LINK_WAIT = 1.5`** now bounds a probe on a link, and a slow board is a test: `SlowBoard` answers after 0.7 s and the position is read.

**The verdict window fell outside in the same way.** Twenty-two poses written in **0.526 s**:

```
1792527570.448  sent b'pose 96 500*FB\n'
1792527570.860  recv pose: stream started — goals on the present positions (yaw 565, pitch 780), torque on
1792527570.950  sent b'pose 350 500*24\n'
1792527571.938  recv pose: stream lost after 500 ms — torque released
1792527572.097  recv pose: 22 applied, 0 refused, 0 clamped
```

⛔ **The board's own tally arrived 1.647 s after the last pose was written** — outside `VERDICT_WAIT = 1.5`, and the first live run recorded `verdict: null` because of it. ⇒ **`LINK_VERDICT_WAIT = 3.0`**, which is ⚠️ **a margin placed on a measurement, not a measurement.**

**Twenty-one of twenty-two poses were applied late.** ⛔ **The positions land; the schedule does not.** A 20 ms stream is not what this link carries, and neither the host nor the board hides it.

## What is not claimed

- ⛔ **The link is not authenticated.** Anything that can reach the Mac's port 3333 can move the head, light the LEDs and sound the speaker. **That exposure did not exist while the body's only wire was a USB cable.** ⚠️ **What the board refuses over the link is `bench wifi` and `bench dial`; frames and poses go straight through.**
- ⛔ **The board's own monologue does not cross the link.** Only lines written through `Say()` travel — `bench:`, `pose:`, `frame:`. `servo: silent for 3 checks…`, `servo: present …` and the whole boot banner are `printf`, and **outside the cable nobody reads them any more.** ⇒ **This host can no longer learn that the servo bus went silent**, which is the fault 0.19.34 was built to answer.
- ⛔ **`let go` has never been logged.** Every disconnect observed today was the daemon being replaced — **the side that cut the link died first.** The row for a board that hangs up on its own does not exist yet.
- ⛔ **A position landing is not a schedule landing.** 21 of 22 poses were late. **The head was where the plan ended and not when the plan said.**
- ⛔ **Surviving without a cable is not what this measures.** What it measures is **a charger-powered body driven by the daemon over the link, answering with its own numbers.** ⚠️ **A Wi-Fi drop, an access-point restart, and the Mac's address changing are all unmeasured**, and the address the board dials is one DHCP lease it cannot be talked out of without a console.
- ⚠️ **No eye has seen the screen since the cable came out.** The face, the lights and the sound are claimed here only as frames the board accepted, never as things a person saw.
