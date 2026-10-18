<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-18-the-lights.md | translated: 2026-10-18 -->

**Language:** [English](2026-10-18-the-lights.md) | [日本語](2026-10-18-the-lights-ja.md) | [中文](2026-10-18-the-lights-zh.md)

# The lights — 2026-10-18

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A log that holds only what the program emitted cannot answer what this record is for — whether a light was lit — and it reads as proof when it is not.

**What was counted.** One board, one day, one pair of eyes. **What was not counted:** brightness, colour temperature, what a second observer would have called each colour, and whether any light outside these twelve was on.

## What was seen

The author's words, in order, each at the moment it was said. ⚠️ **They are quoted verbatim, and they are the only thing in this file that can say a light was lit.**

| # | what was said | what was on the machine at that moment |
|---|---|---|
| 1 | 「さした　LED光った」 | the cable went back in, after a hang had forced it out; the twelve lit |
| 2 | 「いまも点いている」 | still lit while the vendor image was being read off the board |
| 3 | 「ぼんやり青白く光っている　今も」 | pale blue-white, and not bright |
| 4 | 「赤に変わった」 | after `bench leds` wrote full red to all twelve |
| 5 | 「橙色になった」 | after one line carrying `light=warm` was written to the console |
| 6 | 「呼吸している」 | after one line carrying `light=breathe` |
| 7 | 「黄色のled」 | while the daemon's own frame carried `light=alert` |
| 8 | 「その後呼吸」 | when the next frame carried `light=breathe` |

⚠️ **Rows 1–3 come after a failure that is not in this table, and it was the same board on the same day**: the same firmware, the same writes, and the author's word for it was 「光っていない」.

## The first frame, and no light

Earlier the same day, the first frame a host ever sent to this unit carried `light=dim`, the board accepted it, and **nothing lit**. The same writes were then made by a bench command, `bench leds`, and read back:

```
leds: ready=1 version=0x41 cfg=0x0C
leds: M_H=0x20 (pin 13 set)
leds: PU_H=0x20 (pin 13 set)
leds: DRV_H=0x1F (pin 13 clear)
leds: pixel 0 = 0x18C5 (r=3 g=6 b=5)
leds: wrote full red to 12, refresh ok; pixel 0 now 0xF800
```

**What the numbers say:** the expander held the right count (`cfg=0x0C`, twelve), the data pin was an output with a pull-up and push-pull drive, and the colour held in the first four pixels was `0x18C5` — **RGB565 for `{24, 24, 40}`, which is exactly the `dim` colour this repository chose**. A full-red write read back as `0xF800` with no error.

⛔ **And the author, watching the twelve, said 「光っていない」.** The registers held the colour; the pixels did not show it. **Those had been one word until this moment, and this is the day they came apart.**

## What changed the outcome — and what did not

The lights began to work after **one thing**, and the rest of the day is consistent with it: **the expander was power-cycled.** The board had been unplugged to recover from a hang (below), and when it was plugged back in, the twelve lit before any new code, new build or new write existed.

⛔ **That is a hypothesis, not a finding.** Nothing here separated the power cycle from the plug-in moment, the re-enumeration, or the fact that the firmware had just been reflashed. **What is a finding is narrower:** no amount of correct register content produced a light until that cycle, and after it every write produced one.

⚠️ **The palette was multiplied by four the same day, before this.** The first values were written before any LED on this unit had been looked at; at `r=28/255` a warm light is below what daylight shows. **The ratio between the words is unchanged; only the scale moved.** ⛔ **Not one of these colours is a measurement.**

## A hang that cost the machine, twice

**First, by an unknown register bit.** A bench command wrote `LED_CFG` bit 7 — a bit no vendor driver writes — and held it for three seconds. The console stopped, the heartbeat stopped, and the USB-Serial-JTAG ROM stopped answering esptool while the USB device stayed enumerated. **Only unplugging recovered it.** The command was deleted, and the reason is left in `main/leds.cpp`: an untouched register bit is not "unused", it is "unknown".

**Second, by a read that was not a read.** On the same day, a host opened the console with `pyserial` to watch whether a daemon-written frame arrived. The open reset the board — `rst:0x15 (USB_UART_CHIP_RESET)` in the capture — the reader lost the stream mid-boot, and afterwards the console delivered nothing and esptool reported `No serial data received`, with the USB device still enumerated. **The signature was identical to the first hang. Unplugging recovered it again.**

⛔ **The second one looked like the new transport's fault, and it was not.** The daemon's write path — `os.open`, `os.write`, `os.close`, one frame at a time — was then run **alone**, with the console read through `os.open` and raw `termios` instead of `pyserial`:

```
10.05 frame: light=dim face=none
```

`alive` continued every three seconds across the whole window, with no boot banner and no gap. ⇒ **The daemon's own open, write and close delivered the line and did not reset the board. What reset it was `pyserial`'s open, and what wedged it afterwards is not established.**

⚠️ **The cost is named:** a port opened by a tool that asserts DTR and RTS is a reset, and a reset mid-boot is not free on this board. **The next reader that wants to watch the console should use `os.open` and `termios`, or accept that it is rebooting the machine.**

## The daemon writes, and the board answers

✅ **The daemon was then given a port and run as installed** — the launchd job, the installed plist, one path. One event was sent to its socket, and the capture shows both ends of it:

```
frame: light=warm face=greeting (no renderer yet)
frame: gesture perk refused — no gesture -> angle table exists
```

- **the daemon's log carries the same frame** as `{"frame": "{\"face\":\"greeting\",\"gesture\":\"perk\",\"light\":\"warm\"}", "sent": true, …}`;
- **the board received it**, because the board's own console printed it;
- **the gesture was refused by the board**, exactly as `command_frame.cpp` says it is, and the refusal did not stop the light;
- **nothing reset and nothing hung.**

⇒ **This is the first frame of this repository's that has arrived at a machine through a transport, with both ends observed.** ⛔ **`sent: true` alone would not have said that** — it says the host's tty accepted the bytes, and today those two claims were apart for an hour.

⚠️ **And the words are the whole frame.** The line carries `face`, `light` and `gesture`, and nothing else. ⛔ **No number leaves this process: the pose line has its own codec and the daemon does not write it.**

⚠️ **The author's 「黄色のled」 was a frame, not a fault.** The daemon's log shows `light=alert` at that moment — `{160, 104, 0}` in the palette — and the next frame, `light=breathe`, is what the author then called 「その後呼吸」. **A colour chosen for a word arrived as that colour, and the eye named it.**

## The port's name moved

⚠️ **The path in the plist is not an identity.** It read `/dev/cu.usbmodem1101` before the hang and `/dev/cu.usbmodem101` after the cable went back in — **measured on one board, sixteen minutes apart**. The installed plist names the second; **the next replug may name a third.** ⛔ **A frame written to a path that no longer exists is logged as `sent: false` and is not an error** — which is safe, and is also silent. **The memo's trap is now measured, not quoted.**

## What happened to the machine's other actor

⚠️ **This unit carried two applications, and the one in `ota_0` could replace the other.** Once, booting it by erasing `otadata` made it connect to a network and start an OTA into `ota_1` — this repository's own slot — before the cable was pulled.

⇒ **The vendor's image was read off the board first, then `ota_0` was erased.**

| what | value |
|---|---|
| the file | `~/stackchan/vendor-image/stack-chan-1.4.4-ota0.bin`, **outside this repository** |
| its size | **5,177,344 bytes** (0x4f0000) |
| its SHA-256 | `97b176049d75a3e1851ccc738003b62b3b3938c636f7edb2ba287296cf64ab5b` |
| its first bytes | `e9 06 02 4f` — the ESP image magic |
| the erase | `erase-region 0x20000 0x4f0000`, **4.9 seconds** |
| after it | boot from `0x510000`, this repository's app, `ready.` |

⚠️ **The partition table still lists `ota_0`; the region is empty.** ⛔ **Erasing it did not make the board safer or less safe — it made the machine have one actor instead of two.** ⚠️ **And the file is the only copy this workshop holds: it is not in the repository, and no check covers it.**

## What this record does not establish

- **It does not establish that the engine ran.** No `Motion Intent` was read, no trajectory was computed, no gate was passed. **The lights answer words; they do not compute a motion.**
- **It does not establish that `alert` is a good colour, or that `breathe` is a good breath.** Every colour is a choice in `main/leds.cpp`, and none is measured.
- **It does not establish why the first write produced no light.** The power cycle is the only named difference, and it is a hypothesis.
- **It does not establish that `pyserial` wedges this board.** It reset it, once, observed; what happened after the reset is not established.
- **It does not establish that the Pet is there.** ⛔ **That is the goal, and it cannot be verified in this workshop.** A light that follows a word is a mechanism, not a presence.

## The numbers, in one place

| what | value | where it comes from |
|---|---|---|
| the expander | PY32 IO expander at I²C `0x6F`, version **0x41**, twelve LEDs behind pin 13 | read back by `bench leds` |
| the pin | `M_H=0x20`, `PU_H=0x20`, `DRV_H=0x1F`, `O_H=0x00` | output, pull-up, push-pull, driven low |
| the colour held before the red write | `0x18C5` = `{24, 24, 40}`, the `dim` palette entry | read back from the first four pixels |
| after a full-red write | `0xF800`, refresh ok | read back from pixel 0 |
| the palette | off `{0,0,0}` · dim `{24,24,40}` · breathe `{40,48,72}` · warm `{112,64,24}` · alert `{160,104,0}` · error `{144,0,0}` | `main/leds.cpp`, a choice |
| the breathing period | 3 seconds, triangle, 20 %–100 % | `BreathScalePercent()` |
| the transport | one line per frame, `os.open`/`os.write`/`os.close`, no port held | `projects/stackchan/daemon/__main__.py` |
| a delivered frame | daemon wrote `{"face":"greeting","gesture":"perk","light":"warm"}`; board printed it | both logs, one moment |
| the gesture | `perk` refused — no gesture → angle table exists | the board's own line |
| the port | `/dev/cu.usbmodem1101` → `/dev/cu.usbmodem101` after one replug | measured 16:24 and 16:29 |
| the vendor image | 5,177,344 bytes, SHA-256 `97b176…cf64ab5b`, outside the repository | `read-flash` at `0x20000` |
| the erase | `0x20000` + `0x4f0000`, 4.9 s | esptool's own line |
