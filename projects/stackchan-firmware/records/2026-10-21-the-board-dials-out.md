<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-board-dials-out.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-board-dials-out.md) | [日本語](2026-10-21-the-board-dials-out-ja.md) | [中文](2026-10-21-the-board-dials-out-zh.md)

# The board dials out — 2026-10-21

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A line the listener accepted is not a line that moved a head.

**What was counted.** One unit, one Mac, one access point, one USB cable that stayed plugged in for the whole of it, and one socket. **What was not counted:** any interval in which the USB cable was out — **not one measurement below was taken with the console gone** — and any second connection, any real network drop, any packet capture. Every line below came back over the link the board had opened; the cable was still there while it did.

## What was asked

「最終的には、usb接続なしで動くようになるよね？」 — will it, in the end, run without the USB cable?

⚠️ **The question was answered with a shape, not with a yes.** The previous page left one direction open: the Mac could never speak first, and a connection the board opened carried both ways. ⇒ **So the board dials.** This is the first build in which it does.

## What was seen

**The board dialled by itself, at boot, before it said it was ready.** Nobody typed anything: the address is in NVS, written there once by `bench dial`.

```
dial: pointed at 192.168.0.103:3333
waypoint: dial
dial: connected to 192.168.0.103:3333
ready. type `help`.
```

**The head's position came back up that link.** The Mac wrote `bench pos` into the socket it was listening on:

```
sent b'bench pos\n'
recv bench: yaw=ok pitch=ok
recv bench: yaw raw 478, angle 5.6 deg (zero 460)
recv bench: pitch raw 777, angle 49.0 deg (zero 620)
```

**A frame came down it and the board answered on the same socket.** `0.159 s` after the write, with the board's own acceptance line as the evidence — the line the daemon has been reading on the USB console since 0.19.41:

```
sent b'{"face":"curious","gesture":null,"light":"writing","sound":null}\n'
recv frame: light=writing face=curious gesture=none sound=none
```

**A pose came down it, and the head moved.**

```
sent b'pose 100 491*26\n'
recv pose: stream started — goals on the present positions (yaw 478, pitch 777), torque on
recv pose: stream lost after 500 ms — torque released
recv pose: 1 applied, 0 refused, 0 clamped
```

⚠️ **Asked for 10.0° of yaw, the head moved 6 counts — 1.9° — and the next `bench pos` read `yaw raw 484`, 7.5°, eight counts short of the goal.** ⛔ **That loss is the one 0.19.36 already measured on this unit: the servo's, not the schedule's, and the same size whether the line arrives over a cable or a socket.** It is written here as a check that the *same* thing moved, not as a new finding.

**And the link refuses the commands that would change how the board is reached.** The spelling below is the one `HandleBench` really accepts — it skips leading spaces, so two spaces is a real command, not a typo:

```
sent b'bench  wifi\n'
recv dial: refused — that command is the console's
```

⛔ **That refusal found a hole in itself before it reached the unit.** The policy was written to match `bench <verb>` exactly and let `bench  wifi` — two spaces — straight through, because it did not skip the same spaces `HandleBench` skips. `tests/test_stackchan_dial_policy.py` was written first and failed on that row; the source was fixed, not the row.

## What is not claimed

- ⛔ **The cable was never out.** Not one line above was taken with the USB unplugged. **This page measures a link that carries the body's whole conversation; it does not measure the body surviving without its cable.** Those are two different claims and only the first one is made here.
- ⛔ **The daemon does not use this link.** It still opens `/dev/cu.usbmodem101` once per frame and once per gesture. The thing on the other end of the link in every measurement above was a probe written for the purpose — `/tmp/ekl-dial-listen.py` — and ⚠️ **a probe is not a transport**.
- ⛔ **0.159 s is not the link's cost.** The board draws a face and writes twelve LEDs inside that interval. Nothing here separates the socket from the board's own work.
- ⛔ **One connection, once.** Reconnection after a real drop, behaviour when the Mac's address changes, and whether two connections at once are safe are all unmeasured. ⚠️ **The board retries with a backoff and has never been watched doing it.**
- ⚠️ **The address is one DHCP lease.** `192.168.0.103` is where the Mac was that evening. Nothing here discovers the Mac when it moves, and ⛔ **with the cable out there is no console to type a new one into.**
- ⛔ **Two writers were never run against this machine.** The console still owns the body, and the link now asks for it through the same door (`RunLine`) — one mutex, one at a time. **That the mutex is enough is a reading of the source, not a measurement.**
