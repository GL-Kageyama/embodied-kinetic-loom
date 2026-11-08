<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-11-09-the-address-that-did-not-come-home.md | translated: 2026-11-09 -->

**Language:** [English](2026-11-09-the-address-that-did-not-come-home.md) | [日本語](2026-11-09-the-address-that-did-not-come-home-ja.md) | [中文](2026-11-09-the-address-that-did-not-come-home-zh.md)

# The address that did not come home — 2026-11-09

✅ **The author carried the body home and asked whether it was connected.** ⛔ **It was not — and the network was not the reason.** The body had joined the home network and held an address on it, and the host it dialled was **still the venue's**: `dial: pointed at 10.5.0.114:3333`, **3 dial(s), 0 connect(s)**, **56 address(es) swept, 0 found by the sweep**, **58 connect attempt(s) failed**. ✅ **The dial was pointed at the Mac by hand, and the next boot connected within two seconds of getting an address** — then a face came up on the glass: 「顔の表示が出た」.

**What was counted.** One unit, one Mac, one serial console opened three times, and three boots. The numbers below come from the board's own lines (`bench wifi`, `bench dial`, `bench net call`, `bench pos`) and from the Mac's (`lsof`, `arp`, `ping`, `nc`, `ifconfig`, `socketfilterfw`), and each number says which. **What was not counted:** when the body was powered on — ⛔ **nobody watched the boot that followed its arrival**, and the first console line is a boot this session caused; **which SSID the Mac was associated with** — `system_profiler` redacted the name and `networksetup` answered *not associated*, so the two are on **the same subnet** and that is all that is established; and **whether the ICMP failure has a cause on the Mac's side** — no packet was captured.

## What the body held, and where it pointed

✅ **The network was right.** The radio came up on `BFW6K-G-48420_EXT` at channel 1, bssid `dc:62:79:d0:ad:2e`, rssi **−45**, and the station took **`192.168.0.100`**. `bench wifi` named two rows of four with `*` on the home one:

```
wifi: credentials "BFW6K-G-48420_EXT", associated, 192.168.0.100
wifi: list 2 of 4 — `*` is the row the radio is on
wifi:   * "BFW6K-G-48420_EXT"
wifi:     "Cokoga-5F"
wifi:   ch 1 rssi -44
wifi:   sys_evt stack, 1600 bytes never used
```

⛔ **The dial was not.** It was pointed at the address the venue's Mac had held two days earlier, stored in NVS by `bench dial` and therefore kept across every reboot since:

```
dial: pointed at 10.5.0.114:3333
dial: 10.5.0.114:3333 gave nothing in 3002 ms (errno -1)
dial: 10.5.0.114:3333, down — 3 dial(s), 0 connect(s)
dial: 56 address(es) swept, 0 found by the sweep
dial: 58 connect attempt(s) failed (last -1), 0 opened without a greeting
```

⇒ **Two facts that look alike from the Mac and are not**: a body that cannot reach the Mac, and a body that is reaching somewhere else. ⛔ **The daemon's own log cannot tell them apart** — it wrote `{"link": "nobody dialled in", "for": 300.1}` at 300 s, which is true and names no cause. **The console is what separates them, and the address it prints is the whole distinction.**

## What the console said

✅ **The repoint is one line, and it says it survives a reboot**:

```
bench: dial -> 192.168.0.106:3333, kept across a reboot
```

⛔ **And the same boot did not connect.** Twenty seconds later:

```
dial: 192.168.0.106:3333, down — 3 dial(s), 0 connect(s)
dial: 84 address(es) swept, 0 found by the sweep
dial: 86 connect attempt(s) failed (last -1), 0 opened without a greeting
```

⚠️ **Why is not separated.** The sweep may have been carrying the previous address's `/24` — **that is a reading of the source, not a measurement** — and the counters are RAM, so each boot starts at zero and the two reports are not the same arithmetic.

✅ **The next boot did connect, and the order is the finding**:

```
dial: pointed at 192.168.0.106:3333
dial: 192.168.0.106:3333 gave nothing in 0 ms (errno 118)
dial: no route yet — 192.168.0.106:3333 is not being looked for
wifi: connected ip=192.168.0.100
dial: connected to 192.168.0.106:3333
```

⚠️ **The first three lines are the board saying it has no route yet** — `errno 118` in **0 ms**, and then the refusal to sweep without one. ✅ **The address arrived at `I (2079)`, and the connect is printed before `I (3996)`** ⇒ **within two seconds of an address, and under four seconds of a boot.**

## What the Mac saw

✅ **One TCP connection, held**:

```
TCP 192.168.0.106:3333->192.168.0.100:51251 (ESTABLISHED)
```

✅ **And four rows on the daemon's side, one per connection**, because the board re-dials when a connection is taken or dropped:

```
{"link": "the board dialled in", "peer": "192.168.0.100:50763"}
{"link": "the board dialled in", "peer": "192.168.0.100:51249"}
{"link": "the board dialled in", "peer": "192.168.0.100:51250"}
{"link": "the board dialled in", "peer": "192.168.0.100:51251"}
```

✅ **Then the frames, with acceptance read from the board's own line**:

```
{"frame": "{\"face\":\"focused\",\"gesture\":null,\"light\":\"writing\",\"sound\":null}", "sent": true, "accepted": true, "err": null, "at": 662.790517791}
{"frame": "{\"face\":\"watching\",\"gesture\":null,\"light\":\"busy\",\"sound\":null}", "sent": true, "accepted": true, "err": null, "at": 700.936800416}
```

⚠️ **The daemon cannot tell a probe made by hand from the board.** This session's own `nc -z 192.168.0.106 3333` — the Mac connecting to itself — produced:

```
{"link": "the board dialled in", "peer": "192.168.0.106:49501"}
{"link": "the board let go", "peer": "192.168.0.106:49501"}
```

⛔ **The peer address is the only clue, and this row's peer is the Mac's own.** ⇒ **a check that opens the port to see whether the port is open writes a row that says the body arrived.**

⛔ **`ping` does not answer, and the record will not pretend to know why**: `sendto: No route to host`, three times, 100 % loss — while `arp -n 192.168.0.100` holds `80:45:6b:54:6d:b0 on en0` and the TCP connection above is ESTABLISHED. ⚠️ **The cause is not separated**: ICMP may not cross this access point, and the neighbour entry may be stale. ⛔ **What is established is only this: on this network, `ping` is not a probe for this machine.** The Mac's firewall was **off** (`State = 0`), and a self-connect to `192.168.0.106:3333` succeeded.

## What the eye saw

✅ **The author's observation is the spine of this page, and it is one sentence**: 「顔の表示が出た」 — **the face appeared**, after the frames above were accepted. ⛔ **It says a drawing is on the panel; it does not say which face.** No word was judged, no colour was named, and the light was not compared with the panel.

⚠️ **Before that, two observations that are not the same thing**: 「LEDはついている。」 — the body was awake and lit, ⛔ **which does not mean it was connected** — and 「USB繋ぐ？」→「繋いだ」.

⚠️ **Opening the console resets the board.** Three opens, three boot banners. ⇒ **the console is not a free look** — every line on this page is from a boot this session caused, and ⛔ **the body's state between coming home and the first open is not observed.**

## What this record does not say

- ⛔ **That the body was connected before the console was opened.** It was not, as far as anything here can tell — but the console's first act was a reset, so the state it was in on arrival is gone.
- ⛔ **Why the same boot did not connect after the repoint, and the next one did.** The source offers a reading; nothing measured it.
- ⛔ **That `ping` says anything about this machine on this network.** It does not, and the cause is unnamed.
- ⛔ **That the panel's drawing was judged.** A face appeared; which one is not written here.
- ⛔ **That the body will find the Mac anywhere.** The sweep covers **the named address's `/24`** — so at home, where the lease moves inside `192.168.0.0/24`, the greeting can still find the host, and **on a network on another subnet it cannot**: a move like 2026-11-08's needs `bench dial` at a console, ⛔ **and `bench dial` is refused over the link.**
- ⛔ **That anything was fixed.** No code moved and no test moved; **the table of four worked at home** — it associated on the first row — and what a day of this body at home looks like is not yet written.
