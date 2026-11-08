<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-11-09-the-address-that-did-not-come-home.md | translated: 2026-11-09 -->

**Language:** [English](2026-11-09-the-address-that-did-not-come-home.md) | [日本語](2026-11-09-the-address-that-did-not-come-home-ja.md) | [中文](2026-11-09-the-address-that-did-not-come-home-zh.md)

# 没有跟着回家的地址 — 2026-11-09

✅ **作者把身体带回了家，问它是否连着。** ⛔ **没有连着——而网络并不是原因。** 身体已经加入了家里的网络，并在上面拿到了地址，而它拨向的主机**仍然还是会场的那一个**：`dial: pointed at 10.5.0.114:3333`、**3 dial(s), 0 connect(s)**、**56 address(es) swept, 0 found by the sweep**、**58 connect attempt(s) failed**。✅ **把拨号目标手动指向 Mac 之后，下一次启动在拿到地址的两秒之内就连接了**——然后屏幕上出现了一张脸：「顔の表示が出た」（脸显示出来了）。

**数了什么。** 一台身体、一台 Mac、三次打开的串口控制台，以及三次启动。下面的数字来自板子自己的行（`bench wifi`、`bench dial`、`bench net call`、`bench pos`）和 Mac 的行（`lsof`、`arp`、`ping`、`nc`、`ifconfig`、`socketfilterfw`），每个数字都说明来自哪一边。**没有数的：** 身体是什么时候上电的——⛔ **没有人看见它到家后的那次启动**，而控制台的第一行是本会话自己引起的一次启动；**Mac 关联的是哪个 SSID**——`system_profiler` 隐去了名字，`networksetup` 回答*未关联*，所以**只有“在同一子网”这一点是确定的**；以及 **ICMP 不返回是否在 Mac 这一侧有原因**——一个包也没有抓。

## 身体拥有什么，又指向哪里

✅ **网络是对的。** 无线电在 `BFW6K-G-48420_EXT` 上启动，信道 1，bssid `dc:62:79:d0:ad:2e`，rssi **−45**，station 拿到了 **`192.168.0.100`**。`bench wifi` 在四行里点名了两行，`*` 在家的那一行上：

```
wifi: credentials "BFW6K-G-48420_EXT", associated, 192.168.0.100
wifi: list 2 of 4 — `*` is the row the radio is on
wifi:   * "BFW6K-G-48420_EXT"
wifi:     "Cokoga-5F"
wifi:   ch 1 rssi -44
wifi:   sys_evt stack, 1600 bytes never used
```

⛔ **拨号目标不是对的。** 它指向两天前会场那台 Mac 持有的地址，是 `bench dial` 写进 NVS 的，**因此从那以后跨过了每一次重启**：

```
dial: pointed at 10.5.0.114:3333
dial: 10.5.0.114:3333 gave nothing in 3002 ms (errno -1)
dial: 10.5.0.114:3333, down — 3 dial(s), 0 connect(s)
dial: 56 address(es) swept, 0 found by the sweep
dial: 58 connect attempt(s) failed (last -1), 0 opened without a greeting
```

⇒ **两个从 Mac 看去一样、却并不一样的事实**：一个到不了 Mac 的身体，和一个正在到达别处的身体。⛔ **守护进程自己的日志分不开它们**——它在 300 秒时写下 `{"link": "nobody dialled in", "for": 300.1}`，这是真的，而且没有点出任何原因。**把它们分开的是控制台，而它打印出的地址就是全部的区别。**

## 控制台说了什么

✅ **重新指向只有一行，而且它说自己能跨过重启**：

```
bench: dial -> 192.168.0.106:3333, kept across a reboot
```

⛔ **而同一次启动并没有连上。** 二十秒后：

```
dial: 192.168.0.106:3333, down — 3 dial(s), 0 connect(s)
dial: 84 address(es) swept, 0 found by the sweep
dial: 86 connect attempt(s) failed (last -1), 0 opened without a greeting
```

⚠️ **原因没有分开。** 扫描可能还抱着前一个地址的 `/24`——**那是对源码的解读，不是测量**——而且计数器在 RAM 里，每次启动都从零开始，**两个报告不是同一套算术**。

✅ **下一次启动确实连上了，而顺序就是这一页的发现**：

```
dial: pointed at 192.168.0.106:3333
dial: 192.168.0.106:3333 gave nothing in 0 ms (errno 118)
dial: no route yet — 192.168.0.106:3333 is not being looked for
wifi: connected ip=192.168.0.100
dial: connected to 192.168.0.106:3333
```

⚠️ **前三行是板子在说自己还没有路由**——`errno 118` 用了 **0 ms**，然后是“没有路由就不扫”的拒绝。✅ **地址在 `I (2079)` 到达，而 connect 印在 `I (3996)` 之前** ⇒ **拿到地址后两秒之内，启动后不到四秒。**

## Mac 看到了什么

✅ **一条 TCP，保持着的**：

```
TCP 192.168.0.106:3333->192.168.0.100:51251 (ESTABLISHED)
```

✅ **守护进程这一侧有四行，每条连接一行**——连接被接走或被断开时，身体会再次拨号：

```
{"link": "the board dialled in", "peer": "192.168.0.100:50763"}
{"link": "the board dialled in", "peer": "192.168.0.100:51249"}
{"link": "the board dialled in", "peer": "192.168.0.100:51250"}
{"link": "the board dialled in", "peer": "192.168.0.100:51251"}
```

✅ **然后是帧，受理是从板子自己的行读出来的**：

```
{"frame": "{\"face\":\"focused\",\"gesture\":null,\"light\":\"writing\",\"sound\":null}", "sent": true, "accepted": true, "err": null, "at": 662.790517791}
{"frame": "{\"face\":\"watching\",\"gesture\":null,\"light\":\"busy\",\"sound\":null}", "sent": true, "accepted": true, "err": null, "at": 700.936800416}
```

⚠️ **守护进程分不出一只手打的探针和板子。** 本会话自己的 `nc -z 192.168.0.106 3333`——Mac 连自己——让它写下了：

```
{"link": "the board dialled in", "peer": "192.168.0.106:49501"}
{"link": "the board let go", "peer": "192.168.0.106:49501"}
```

⛔ **唯一的线索是 peer 的地址，而这一行的 peer 是 Mac 自己。** ⇒ **一个为了看端口开不开而去开这个端口的检查，会写下一行说身体来了。**

⛔ **`ping` 不返回，而这份记录不假装知道原因**：`sendto: No route to host` 三次，100% 丢失——而 `arp -n 192.168.0.100` 仍持有 `80:45:6b:54:6d:b0 on en0`，上面的 TCP 也仍是 ESTABLISHED。⚠️ **原因没有分开**：ICMP 可能过不了这个接入点，邻居表项也可能是旧的。⛔ **确定的只有这一点：在这个网络上，`ping` 不是这台机器的探针。** Mac 的防火墙是**关的**（`State = 0`），而且连到 `192.168.0.106:3333` 的自我连接是成功的。

## 眼睛看到了什么

✅ **作者的观察是这一页的脊梁，而且只有一句话**：「顔の表示が出た」——**脸出现了**，在上面那些帧被受理之后。⛔ **它说的是屏幕上有一幅画，而不是哪一张脸。** 没有词被判定，没有颜色被点名，光也没有和面板比较过。

⚠️ **在那之前，两个观察不是同一件事**：「LEDはついている。」——身体醒着、亮着，⛔ **这并不表示它连着**——以及「USB繋ぐ？」→「繋いだ」。

⚠️ **打开控制台会让板子复位。** 三次打开，三次启动横幅。⇒ **控制台不是免费的窥视**——这一页上的每一行都来自本会话引起的启动，⛔ **从到家到第一次打开之间的身体状态，没有被观测。**

## 这份记录不说什么

- ⛔ **不说不开控制台之前身体是连着的。** 就这里所有的一切而言，它并没有——但控制台的第一件事就是复位，所以**它到达时的状态已经没有了**。
- ⛔ **不说为什么重新指向的同一次启动没连上、而下一次连上了。** 源码给出一个解读；没有什么测量过它。
- ⛔ **不说 `ping` 在这个网络上能说明这台机器的什么。** 它说明不了，而原因没有名字。
- ⛔ **不说面板上的画被判定过。** 出现了一张脸；是哪一张，没有写在这里。
- ⛔ **不说身体在任何地方都能找到 Mac。** 扫描覆盖的是**被点名的那个地址的 `/24`**——所以在家里，租约在 `192.168.0.0/24` 里移动时，问候仍然能找到主机；**在另一个子网的网络上就做不到**：像 2026-11-08 那样的移动需要在控制台上用 `bench dial`，⛔ **而 `bench dial` 在链路上是被拒绝的。**
- ⛔ **不说有什么被修好了。** 没有代码移动，也没有测试移动；**四行的表在家里工作了**——它在第一行就关联上了——而**这台身体在家的一天是什么样子，还没有被写下来。**
