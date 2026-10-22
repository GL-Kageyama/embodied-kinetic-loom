<!-- i18n-version: 1.1.0 | canonical: projects/stackchan-firmware/records/2026-10-23-the-board-looked-for-the-host.md | translated: 2026-10-23 -->

**Language:** [English](2026-10-23-the-board-looked-for-the-host.md) | [日本語](2026-10-23-the-board-looked-for-the-host-ja.md) | [中文](2026-10-23-the-board-looked-for-the-host-zh.md)

# The board that looked for its host — 2026-10-23

⛔ **This page records a lease that moved, a board that kept dialling the address it had been given, and the day the dialer was taught to look.** ⚠️ **What the author did is short and is written first**: the USB cable was plugged in, and the word was 「やろう」. **Everything up to the last section is what the console and the daemon's log said while this session worked** — ⛔ **no eye was asked about the head, the light or the screen while the search was being made** — and **the one word the author gave at the end, 「全部OK」, is recorded where it was said and is not turned into a claim about whether anything is there.**

**What was counted.** One unit, one console (`/dev/cu.usbmodem1101` — ⚠️ **not the `.101` device of the 2026-10-21 records**, and **why this Mac named it differently today is not established**), one access point, one Mac whose `en0` carried **two** addresses (`192.168.0.106` as the lease, `192.168.0.103` as an alias added by hand during this session, and still present at the end). **What was not counted:** any packet capture (it needs root), the access point's own log, and ⛔ **the head, the light and the screen — nobody looked at any of them.**

## What the author did

**Plugged the USB cable in**, and when asked whether to carry the change through (a board-side search with a greeting, and a host-side line for *nobody came*), said **「やろう」**. ⚠️ **No physical action beyond the cable**: the unit sat where it was, and the head was never asked to move.

## The fault, as the daemon's log held it

⚠️ **The Mac rebooted at 04:55 and its DHCP lease came back as `192.168.0.106`.** The board's NVS still named `192.168.0.103`. **The board dialled, and nothing answered.** Frames the daemon tried to send that morning were logged like this:

```
{"frame": "{\"face\":\"greeting\",\"gesture\":\"look_up\",\"light\":\"warm\",\"sound\":null}",
 "sent": false, "accepted": null, "err": "nobody", "at": 501.860373416, "session": "…"}
```

⛔ **`"err": "nobody"` says the host had no connection. It does not say that the board tried and missed** — and the board's own side had no line at all, because the dial that fails only counted a number. **A quiet log was being read as a quiet machine.**

## What the board said, before the search was gated

✅ **The first version swept on any failed dial.** That morning the console answered `bench dial` with:

```
dial: 192.168.0.106:3333, down — 2 dial(s), 0 connect(s)
dial: 402 address(es) swept, 0 found by the sweep
dial: 403 connect attempt(s) failed (last -1), 0 opened without a greeting
dial: 0 attempt(s) had no socket to make
```

⛔ **402 addresses in about 7 s, and every one of them failed in 0 ms.** The reason was in the count that was written to make this visible: `connect` returned **`errno 118`**, `ENETUNREACH`. ⚠️ **The sweep ran at boot, before Wi-Fi had an address of its own** — **a missing route and a missing host are one failure to a socket**, and the walk was measuring the first one 254 times.

## What the board said, after the gate

✅ **The rule `sweep_when(routed, now_us, last_us, every_us)` puts `kNoRoute` first.** At boot, twice on the same day (05:38 and 05:44):

```
I (197) app_init: Project name:     stackchan-vessel
I (197) app_init: App version:      a465702-dirty
I (197) app_init: Compile time:     Oct 23 2026 05:21:18
reset: reason 11 (usb peripheral)
dial: pointed at 192.168.0.106:3333
dial: 192.168.0.106:3333 gave nothing in 1 ms (errno 118)
dial: no route yet — 192.168.0.106:3333 is not being looked for
dial: 192.168.0.106:3333 gave nothing in 0 ms (errno 118)
dial: no route yet — 192.168.0.106:3333 is not being looked for
wifi: connected ip=192.168.0.100
dial: connected to 192.168.0.106:3333
dial: 192.168.0.106:3333, up — 3 dial(s), 1 connect(s)
dial: 0 address(es) swept, 0 found by the sweep
dial: 2 connect attempt(s) failed (last 118), 0 opened without a greeting
```

- ⚠️ **`reset: reason 11 (usb peripheral)` is this page's own doing** — the console was opened to read the banner, and opening it resets the chip. **The two refusals and the connection that follow are a boot this page caused, not a boot that happened by itself.**
- ✅ **`0 address(es) swept` is the finding**: with no route the board no longer doubts the address, and the walk it used to spend on nothing is not spent.
- ⚠️ **The gate is a rule, not a wait**: `no route yet` printed twice and then stopped because the address arrived, not because an interval expired.

## The sweep, with a route under it

✅ **Pointed at an address nobody held, after the address was up:**

```
bench: dial -> 192.168.0.104:3333, kept across a reboot
dial: 192.168.0.104:3333 gave nothing in 3002 ms (errno -1)
dial: found the host at 192.168.0.103:3333 — 2 address(es) past the named one
dial: connected to 192.168.0.103:3333
dial: 2 address(es) swept, 1 found by the sweep
```

- ⚠️ **`errno -1` is the clock running out** — the 3,000 ms window — and **not a reason the network gave**. The two spellings are kept apart in the report for that reason.
- ⚠️ **`2 address(es) past the named one` means `.104` was tried and refused first**: the named address gets its own 3,000 ms, and only then does the walk begin.
- ⛔ **`.103` answered because it is an alias this session added to `en0` by hand.** ⇒ **The walk was measured; the event it exists for — a host that moved — was not reproduced.** ⚠️ **`.103` does not answer a connection from the Mac itself** (a `connect` there times out after 3 s, where `.106` answers at once); **why was not investigated.**

## The host's side

✅ **The host greets, and then says when nobody came.** Measured from the Mac against the listener:

| what | value | where it came from |
|---|---|---|
| the greeting | the first bytes on every connection are `loom\n` | a socket opened from the Mac |
| the accept | `.106` accepted in **0.001 s** | the same socket |
| the arrival | `{"link": "the board dialled in", "peer": "192.168.0.100:50406"}` | the daemon's log, after the boot above |
| the frames | `sent: true, accepted: true` | the daemon's log |

⛔ **The `{"link": "nobody dialled in", "for": N}` row has not printed on this machine.** It is held by tests only, because the board arrived on every boot of the day; ⚠️ **a row that has never printed is a row the machine has not confirmed.**

## After the link came back

✅ **The link then carried two gestures, and the author watched and listened.** Two lines were written to the daemon's own socket — `SessionStart`, then `Stop` — and the room answered `acted` to both:

| the event | the phase | the face | the light | the sound | the body |
|---|---|---|---|---|---|
| `SessionStart` | `greeting` | `greeting` | `warm` | `hello` | `look_up` |
| `Stop` | `closing` | `happy` | `warm` | `chime` | `nod` |

**What the board said about the head** — over the link, in its own line, not the console:

```
look_up  from [56, 431] to [80, 500], 11 poses, 0.200 s
         pose: 39 applied, 0 refused, 0 clamped     (yaw 478, pitch 758)
nod      from [59, 493] to [80, 500], 79 poses, 1.555 s
         pose: 107 applied, 0 refused, 0 clamped    (yaw 479, pitch 778)
```

Both frames came back `sent: true, accepted: true` — `{"face":"greeting","gesture":null,"light":"warm","sound":"hello"}` and `{"face":"happy","gesture":null,"light":"warm","sound":"chime"}` — and the room then settled to `breathe` with no event behind it.

- ⚠️ **The schedule is still behind the positions**: **10 of the 11** `look_up` poses and **72 of the 79** `nod` poses were applied late — the split 0.19.61 measured, unchanged by the day's work.
- ⚠️ **The verdict line was read from its middle** (`tarted — goals on the present positions …`); the counts behind it are whole, and both said **0 refused**.

⛔ **The author's word was 「全部OK」**, given to three questions — whether the head moved, whether the sound rang, whether the light was seen. ⚠️ **It is one word for three questions**: it says all three were well, and ⛔ **it does not say what any of them looked or sounded like** — not the colour, not which of the two sounds — **and the screen was not among the questions, so nothing here is a claim about the face.**

## What this does not establish

- ⛔ **That a board can find a host that moved.** The address it found was one this session had put there. **A DHCP lease that changes under a running board is the fault, and it was not re-staged.**
- ⛔ **That the greeting rule refuses anything.** `0 opened without a greeting` has only ever been zero — no candidate has yet answered with something else.
- ⛔ **That the "nobody" line prints after 300 s.** Nothing in this run waited that long with the board away.
- ⛔ **Why the earlier version's `connect` failures all came back in 0 ms** beyond the `118` the counter printed. ⚠️ **`118` is what `connect` said; when the station got its route is inferred from the `wifi: connected` line that follows.**
- ⚠️ **Whether a found address survives anything.** It is held in RAM only — `bench dial` over the link is still refused — so this page's found address was gone at the next boot, **and no run measured how long a sweep-found link lasts.**
- ⛔ **Nothing moved *during the search*.** The two gestures above came after it, from two lines written into the daemon's socket — **they are the body's record and not the sweep's** — and **the screen has still not been looked at.** A record of a search and a sentence is what the search part of this page is; the body's part is the section above.
