<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-line-that-crosses.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-line-that-crosses.md) | [日本語](2026-10-21-the-line-that-crosses-ja.md) | [中文](2026-10-21-the-line-that-crosses-zh.md)

# The line that crosses — 2026-10-21

⛔ **This page is a record of a reading, not of motion.** Nobody watched the head; it did not move for any of it (`look_up` came back `skipped: "no motion"` both times). What was watched is **one silence, seen from two sides** — the board's console and the host's log — and the two agree.

**What was counted.** One unit, one Mac, one socket. **Two of the rows below were taken with no USB cable at all**: `/dev/cu.usb*` did not exist and `ls` said so. **What was not counted:** anything an eye saw; any packet capture; any Wi-Fi drop or access-point restart; and ⛔ **the two silences were not faults the machine produced — I typed `bench power off` and took my hand away.**

## What was asked

The 0.19.61 record ended on a sentence that was also a debt:

> ⛔ **The board's own monologue does not cross the link.** Only lines written through `Say()` travel. `servo: silent for 3 checks…` … are `printf`, and **outside the cable nobody reads them any more.** ⇒ **This host can no longer learn that the servo bus went silent**, which is the fault 0.19.34 was built to answer.

⛔ **And that debt was created by the same version that made the link the only route** — so it was not a gap at the edge; it was the machine losing a sense at the moment it lost its wire. 0.19.62 pays it with one line: **the board puts its own watchdog's two numbers into the answer to a question**, because the rule that survived 0.19.61 is *lines that answer a question cross; lines the body volunteers do not.*

## What was seen

**The board, on the console, doing the work:**

```
bench: servo power OFF — the expander took the write; the head is limp
servo: no answer (1 of 3 before the rail is cycled)
servo: no answer (2 of 3 before the rail is cycled)
servo: silent for 3 checks — cycling the rail (1 since this boot)
servo: rail cycled — ping yaw=0/3 pitch=3/3
servo: present yaw=491 pitch=779; goals set; torque off
```

⛔ **Every one of those six lines is `printf`, and in 0.19.61 none of them reached the host.**

**The same afternoon, as the host read it — ten probe rows, in order:**

```
{"strikes": 0, "rail": 0}
{"strikes": 0, "rail": 0}
{"strikes": 0, "rail": 0}
{"strikes": 0, "rail": 0}
{"strikes": 0, "rail": 1}
{"strikes": 0, "rail": 1}
{"strikes": 2, "rail": 1}
{"strikes": 0, "rail": 2}
{"strikes": 0, "rail": 2}
{"strikes": 0, "rail": 2}
```

⚠️ **The seventh row is the one that matters.** Its whole record is:

```
{"position": null, "heard": true, "servo": {"strikes": 2, "rail": 1},
 "read": "bench: servo strikes=2 rail=1\nbench: yaw=no answer pitch=no answer\n", "at": 11671.812024583}
```

**The console answered, the servos did not, and the board said which** — two checks missed, one rail cycle already spent. That is the 2026-10-19 failure, arriving at the host as a number instead of as a sentence nobody could read. ⚠️ **`strikes` is the early warning and `rail` is the event**, and the row shows both at once: **the silence is still running, and a recovery has already happened once.**

**The last row was taken with the cable out:**

```
{"position": [96, 496], "heard": true, "servo": {"strikes": 0, "rail": 2},
 "read": "bench: servo strikes=0 rail=2\nbench: yaw=ok pitch=ok\nbench: yaw raw 491, angle 9.6 deg (zero 460)\nbench: pitch raw 779, angle 49.6 deg (zero 620)\n", "at": 11738.901884791}
```

⛔ **`/dev/cu.usb*` did not exist when that line was written.** The number the watchdog prints with `printf`, which 0.19.61 took away, now arrives on `Say()` — and it arrives **first, before the position lines**, because the host closes the window the moment it can read a pose. ⚠️ **That ordering is asserted, not assumed**: the test reads both literals out of `main.cpp` and compares their positions.

**The day instrument counts it without being told how.** Over the same log: `servo reports 10`, `seen silent 1`, `rail cycles 2`, `rail resets 0`. ⚠️ **`rail cycles` is the one count in that file that is not a tally** — `rail` is the board's count since *its* boot, so the cycles are the **increases**, and a decrease is a board reboot whose earlier cycles are not observable (`rail resets`). ⛔ **That exception is named in the source and held by a test that reverses the lines and shows exactly which field moves.**

**The first `bench power off` did not land.** I wrote the line and closed the port at once; the next probe showed the servos answering and `strikes: 0` — **the write had returned and the line had not arrived.** The second attempt held the port open for two seconds and the board obeyed. ⛔ **A write that returns is not a line that arrived**, which is the same sentence this repository already wrote about `sent: true`, one layer down.

## What this does not fix, found on the way

**A restarted daemon orphans the body.** After `launchctl kickstart -k` the new socket was listening and the board never came: its old connection sat in **`FIN_WAIT_1` for over a minute with no ACK**, and `ping -c 2 192.168.0.19` returned **2 sent, 0 received** while `arp -an` held the board's own MAC. ⇒ **The 0.19.59 direction is unchanged** — the Mac cannot send first — and the board was sitting in `select()` on a socket that will never speak again, with no read timeout in `DialTask`.

⛔ **Only a reset brought it back** — `esptool`'s hard reset, with the cable in. **With the cable out, that recovery does not exist**, and the body would have to be power-cycled by hand.

⚠️ **Not claimed: that this always happens.** Four listener swaps on 2026-10-21 recovered by themselves, in 0.3–4 s. **This is one observation of the failure, not a rate.**

## What is not claimed

- ⛔ **No head moved.** This page is a reading; the positions it quotes are the same ones before and after.
- ⛔ **The two silences were induced.** `bench power off` typed at the console is a command, and the watchdog's answer to it is the machine working — **not a fault occurring on its own.** The spontaneous silence of 2026-10-19 (22.8 minutes, nothing asked) is still unattributed.
- ⛔ **The counter is per boot.** A board reset takes `rail` back to 0, and the host cannot see the cycles before it.
- ⚠️ **`strikes` was read at 0 and at 2, never at 1**, and never during a silence that arrived by itself.
- ⚠️ **The link is still not authenticated**, and `bench power off` crossed it. **Anything that can reach port 3333 can now make the head limp** — that was already true of poses and frames; this page only shows that the bench is reachable too.
- ⚠️ **No eye saw the screen, the lights or the head** for any of it.
