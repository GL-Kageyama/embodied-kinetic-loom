<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-23-the-board-looked-for-the-host.md | translated: 2026-10-23 -->

**Language:** [English](2026-10-23-the-board-looked-for-the-host.md) | [日本語](2026-10-23-the-board-looked-for-the-host-ja.md) | [中文](2026-10-23-the-board-looked-for-the-host-zh.md)

# 寻找自己主机的基板 — 2026-10-23

⛔ **这一页记录的是一个移动了的租约、一块继续敲着它被给予的地址的基板，以及 dialer 被教会去张望的那一天。** ⚠️ **作者做的事很短，写在最前**：USB 线被插上，说的话是「やろう」。**之后的一切，都是这个会话工作时控制台与守护进程日志说出的话**——⛔ **头、灯和屏幕都没有被问过任何一只眼睛，这一页里没有任何一句是关于那里是否有什么东西的主张。**

**数了什么。** 一台机体、一本控制台（`/dev/cu.usbmodem1101`——⚠️ **不是 2026-10-21 记录里的 `.101`**，而**这台 Mac 今天为什么这样命名，没有确定**）、一个接入点，以及 `en0` 上带**两个**地址的 Mac 一台（`192.168.0.106` 是租约，`192.168.0.103` 是这个会话中途手工加上的别名，结束时仍在）。**没有数的：** 任何抓包（需要 root）、接入点那一侧的日志，以及⛔ **头、灯和屏幕——没有任何人看过其中任何一个。**

## 作者做了什么

**插上了 USB 线。** 然后，在被问到这个改动（基板侧带名号的搜索，以及主机侧说出*没有人来*的那一行）是否要一路做到底时，说了**「やろう」**。⚠️ **除了线缆之外没有物理动作**：机体留在原地，头一次也没有被要求移动。

## 故障——守护进程的日志所持有的形状

⚠️ **Mac 在 04:55 重启，DHCP 租约以 `192.168.0.106` 回来。** 基板的 NVS 仍然指着 `192.168.0.103`。**基板拨号了，没有人回答。** 那天早上守护进程试图发出的帧，被这样记录：

```
{"frame": "{\"face\":\"greeting\",\"gesture\":\"look_up\",\"light\":\"warm\",\"sound\":null}",
 "sent": false, "accepted": null, "err": "nobody", "at": 501.860373416, "session": "…"}
```

⛔ **`"err": "nobody"` 说的是主机没有连接。它没有说基板试过而落空**——而基板那一侧一行也没有，因为失败的拨号只数了一个数。**安静的日志被读成了安静的机器。**

## 在给搜索装门之前，基板说了什么

✅ **第一个版本在每次拨号失败时都扫。** 那天早上，控制台对 `bench dial` 这样回答：

```
dial: 192.168.0.106:3333, down — 2 dial(s), 0 connect(s)
dial: 402 address(es) swept, 0 found by the sweep
dial: 403 connect attempt(s) failed (last -1), 0 opened without a greeting
dial: 0 attempt(s) had no socket to make
```

⛔ **402 个地址，约 7 秒，而且每一个都在 0 ms 内失败。** 原因就在为了让这件事可见而写下的计数里：`connect` 返回了 **`errno 118`**，`ENETUNREACH`。⚠️ **扫掠在启动时运行，而 Wi-Fi 还没有自己的地址**——**没有路由与没有主机，对套接字来说是同一种失败**，那趟行走把前者量了 254 次。

## 装了门之后，基板说了什么

✅ **规则 `sweep_when(routed, now_us, last_us, every_us)` 把 `kNoRoute` 放在最前。** 启动时，同一天两次（05:38 与 05:44）：

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

- ⚠️ **`reset: reason 11 (usb peripheral)` 是这一页自己招来的**——为了读启动横幅而打开了控制台，而打开它会复位芯片。**随后的两个拒绝和那条连接，是这一页引起的启动，不是自己发生的启动。**
- ✅ **`0 address(es) swept` 才是发现**：没有路由时，基板不再怀疑地址，从前白白花掉的那趟行走不再被花掉。
- ⚠️ **门是规则，不是等待**：`no route yet` 印了两次就停了，**不是因为间隔用完，而是因为地址来了**。

## 路由之下的扫掠

✅ **在地址上来之后，指向一个无人持有的地址：**

```
bench: dial -> 192.168.0.104:3333, kept across a reboot
dial: 192.168.0.104:3333 gave nothing in 3002 ms (errno -1)
dial: found the host at 192.168.0.103:3333 — 2 address(es) past the named one
dial: connected to 192.168.0.103:3333
dial: 2 address(es) swept, 1 found by the sweep
```

- ⚠️ **`errno -1` 是时钟用完了**——3,000 ms 的窗口——**不是网络给出的理由。** 报告里把两种拼写分开，就是为了这个。
- ⚠️ **`2 address(es) past the named one` 意味着 `.104` 被先试过并被拒绝**：指名的地址有它自己的 3,000 ms，之后行走才开始。
- ⛔ **`.103` 会回答，是因为它是这个会话手工加到 `en0` 上的别名。** ⇒ **行走量过了；它为之而存在的事件——一个移动了的主机——没有复现。** ⚠️ **`.103` 不回应 Mac 自己发出的连接**（那边的 `connect` 在 3 秒后超时，而 `.106` 立即回答）；**原因没有调查。**

## 主机那一侧

✅ **主机会报出名号，然后说出没有人来过。** 从 Mac 对监听测得：

| 量了什么 | 值 | 从哪里来 |
|---|---|---|
| 名号 | 每条连接的头几个字节是 `loom\n` | 从 Mac 打开的套接字 |
| 受理 | `.106` 在 **0.001 秒**内被受理 | 同一个套接字 |
| 到达 | `{"link": "the board dialled in", "peer": "192.168.0.100:50406"}` | 守护进程的日志，在上面那次启动之后 |
| 帧 | `sent: true, accepted: true` | 守护进程的日志 |

⛔ **`{"link": "nobody dialled in", "for": N}` 这一行，还没有在这台机器上印出过。** 那天每次启动基板都来了，所以撑着它的只有测试；⚠️ **一行从未印出过，就是机器没有确认过的行。**

## 这一页没有确立的事

- ⛔ **基板能找到移动了的主机。** 它找到的地址，是这个会话放在那里的。**在运行中的基板下面 DHCP 租约移动才是故障，而它没有被重新摆出来。**
- ⛔ **名号规则拒绝过任何东西。** `0 opened without a greeting` 从来只是 0——还没有候选回答过别的话。
- ⛔ **「nobody」这一行会在 300 秒之后印出。** 这次运行里，没有谁把基板留在外面等那么久。
- ⛔ **早先版本的 `connect` 失败为什么全都在 0 ms 内返回**，除了计数印出的 `118` 之外没有更多。⚠️ **`118` 是 `connect` 说的话；站点什么时候获得路由，是从随后出现的 `wifi: connected` 行推断的。**
- ⚠️ **找到的地址能活过什么。** 它只在 RAM 里——链路上的 `bench dial` 仍然被拒绝——所以这一页找到的地址在下一次启动时就没了。**而没有哪一次运行量过：一次扫掠找到的链路能持续多久。**
- ⛔ **什么都没有动。** 没有回放任何手势，没有点灯，**屏幕没有被看。** 这是一个关于搜索和一句话的记录，不是关于身体的。
