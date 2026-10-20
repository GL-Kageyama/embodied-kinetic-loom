<!-- i18n-version: 1.1.0 | canonical: projects/stackchan-firmware/records/2026-10-21-two-directions.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-two-directions.md) | [日本語](2026-10-21-two-directions-ja.md) | [中文](2026-10-21-two-directions-zh.md)

# The two directions — 2026-10-21

⛔ **The observation is the spine of this file. The program's numbers are quoted inside it as evidence, not around it.** A packet the host's `sendto` accepted is not a packet that reached the board.

**What was counted.** One unit, one Mac, one access point, one wired port, and one evening of attempts in both directions. **What was not counted:** any second wireless client, any second access point, any packet capture — none was available without root, so **no frame on the wire was ever seen**; every statement below is inference from what each end reported.

## What was asked

The author's instruction for this session was one line: **「そもそもwifi接続できているか？の確認あたりから始めて」** — start by checking whether the radio is connected at all.

## What was seen

**The radio is connected.** The board prints it in its own words:

```
wifi: nvs holds "BFW6K-G-48420" — connecting
wifi: associated — waiting for an address
wifi: connected ip=192.168.0.19
wifi: credentials "BFW6K-G-48420", associated, 192.168.0.19
wifi:   ch 1 rssi -60
```

**That sentence cost a boot loop first.** Every boot died about a second after the address arrived, with a `LoadProhibited` on a `l32i` from a queue pointer whose fields held PS-register values. **A coredump named the crash**: the task was `sys_evt`, interrupted inside `esp_netif_lwip_ipc_call_get_netif` — the IPC round trip behind `esp_netif_get_ip_info`, which the `IP_EVENT_STA_GOT_IP` handler was calling — and its stack had run past its end into the heap. The task's stack is `CONFIG_ESP_SYSTEM_EVENT_TASK_STACK_SIZE`, **2304 by default**. Raised to 4096, the same handler reports **`sys_evt stack, 1600 bytes never used`**, so the need was about 2496 — over the default by roughly 200.

## The direction that never worked

**From the Mac to the board, nothing was ever delivered.** Not one of these reached it:

| tried | result |
|---|---|
| `connect()` to `192.168.0.19:3333`, 33 attempts | `EHOSTUNREACH`, **0.0001–0.0002 s each** |
| the same from a socket bound to `en0` | the same, and the board heard `0 datagram(s)` |
| `sendto()` on UDP, **any port** — 3333, 9999, 40000, 1 | the same, instantly |
| `sendto()` with no bind, with a bind to `0.0.0.0`, with a bind to the Mac's own address | the same |
| a subnet broadcast to `192.168.0.255:3333` | **sent, and the board heard nothing** |
| 87 `connect()` attempts in 9 s, with a frame from the board arriving mid-run | **0 open** |

⚠️ **The refusal is the host's, not the network's, and that is why it is written down this way.** It returns in **0.1 ms** — too fast for a frame to have left and an answer come back. The route was present and current (`route get` showed `UP,HOST,DONE,LLINFO,WASCLONED,IFSCOPE,IFREF`, `expire 1182`), and **`arp -an` held this board's own MAC, `80:45:6b:54:6d:b0`, the whole time**, while a host that genuinely was not there showed `(incomplete)`. ⇒ **The Mac held the right address for the right machine and still refused to speak first.**

**Controls, run on the same bound sockets in the same minute:**

- the gateway `192.168.0.254` — `connect()` to port 80 **open in 0.005 s**, and a UDP query to port 53 **answered, 17 bytes**;
- a second, fresh address given to the board (`192.168.0.77`, for that boot only) — **also refused**, so this is not one stale cache entry.

⛔ **A gratuitous ARP from the board changed nothing.** The board broadcast its own address to the segment (`net: announced this address to the whole segment`) and the next 33 attempts failed exactly as before.

## The direction that worked every time

**Whatever the board sends first arrives, and the answer comes back.**

- a UDP datagram out — the Mac read `b'still-there'` from `192.168.0.77:61530` and answered, and the board printed **`net: reply "pong"`**;
- a **TCP connection the board opened out** — the Mac accepted it, read `b'can-you-hear-me\n'`, answered, and the board printed **`net: the host said "yes-loud-and-clear"`**.

⇒ **One connection, opened from the board, carried both directions.** ⚠️ Every success in this session was a reply inside a flow the board had opened, and every failure was the Mac trying to speak first.

## What is not claimed

- ⛔ **Why the Mac refuses is not established.** The 0.1 ms says the decision is taken on the host. It does not say by what. No packet capture was taken, and no second client existed to tell "this board" from "any wireless client".
- ⛔ **This is not a diagnosis of the access point.** The AP was never asked anything directly; it is named as a *possibility* and nothing more.
- ⛔ **Stability is not measured.** Every result above is from one evening, one unit, one AP, one wired port. **Nothing here says the outward direction holds for an hour.**
- ⛔ **Nothing here is a transport decision.** The proven direction is outward; what to build on it, and who owns the body when two paths can reach it, is not settled by this page.
- ⚠️ **The probe that measured this is not a feature.** `main/net.cpp` accepts a connection and answers its length; it never dispatches a line, because the console already owns the body and a second writer on one bus is the failure 0.19.27 measured.
