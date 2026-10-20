<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-line-that-crosses.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-line-that-crosses.md) | [日本語](2026-10-21-the-line-that-crosses-ja.md) | [中文](2026-10-21-the-line-that-crosses-zh.md)

# 穿过的那一行 — 2026-10-21

⛔ **这一页是读数的记录，不是运动的记录。** 没有任何人看着头部；整个过程它一次也没有动（`look_up` 两次都返回 `skipped: "no motion"`）。看到的是**一次沉默，从两个方向看**——主板的控制台和主机的日志——而两者一致。

**数了什么。** 一台机体、一台 Mac、一个 socket。**下面的行里有两条是在完全没有 USB 线的情况下取的**：`/dev/cu.usb*` 不存在，`ls` 是这样说的。**没有数的：** 眼睛看到的东西、任何抓包、任何 Wi-Fi 掉线或接入点重启；并且 ⛔ **这两次沉默不是机器自己产生的故障——是我敲了 `bench power off`，然后把手指抬起来。**

## 被问到了什么

0.19.61 的记录结尾是一句话，而那也是一笔债：

> ⛔ **主板的自语不穿过链路。** 只有通过 `Say()` 写出的行会走。`servo: silent for 3 checks…` ……是 `printf`，而**在线缆之外，已经没有人读它们了。** ⇒ **这台主机再也无法得知伺服总线沉默了**，而那正是 0.19.34 被建造出来回答的故障。

⛔ **而这笔债，正是把链路变成唯一路径的那一个版本造成的**——所以它不是边缘上的缺口；**它是机器在失去自己那根线的瞬间，失去了一个感觉。** 0.19.62 用一行偿还：**主板把看门狗的那两个数，放进对一个问题的回答里**，因为活过 0.19.61 的规则是——*回答问题的行走，身体自己说话的行不走。*

## 看到了什么

**主板在控制台上，正在做事：**

```
bench: servo power OFF — the expander took the write; the head is limp
servo: no answer (1 of 3 before the rail is cycled)
servo: no answer (2 of 3 before the rail is cycled)
servo: silent for 3 checks — cycling the rail (1 since this boot)
servo: rail cycled — ping yaw=0/3 pitch=3/3
servo: present yaw=491 pitch=779; goals set; torque off
```

⛔ **那六行每一行都是 `printf`，而在 0.19.61 里，它们一行也没有到达主机。**

**同一个下午，按主机读到的那样——十行探针，按顺序：**

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

⚠️ **第七行才是关键的那一行。** 它的完整记录是：

```
{"position": null, "heard": true, "servo": {"strikes": 2, "rail": 1},
 "read": "bench: servo strikes=2 rail=1\nbench: yaw=no answer pitch=no answer\n", "at": 11671.812024583}
```

**控制台回答了，伺服没有回答，而主板说了是哪一个**——连续两次没答上，导轨已经落了一次。**那就是 2026-10-19 的故障，作为一个数到达主机，而不再是一句没人能读的话。** ⚠️ **`strikes` 是预警，`rail` 是事件**，这一行同时给出两者：**沉默仍在继续，而恢复已经发生过一次。**

**最后一行是在拔掉线缆的状态下取的：**

```
{"position": [96, 496], "heard": true, "servo": {"strikes": 0, "rail": 2},
 "read": "bench: servo strikes=0 rail=2\nbench: yaw=ok pitch=ok\nbench: yaw raw 491, angle 9.6 deg (zero 460)\nbench: pitch raw 779, angle 49.6 deg (zero 620)\n", "at": 11738.901884791}
```

⛔ **写下那一行的时候，`/dev/cu.usb*` 并不存在。** 看门狗用 `printf` 印出的那个数——0.19.61 拿走的那个——现在搭在 `Say()` 上到达了；而且**它在位置行之前到达**，因为主机在能读出姿势的那一刻就关上窗口。⚠️ **那个顺序是被断言的，不是被假设的**：测试从 `main.cpp` 里读出两个字面量，比较它们的位置。

**一天的仪器没有被教过，却把它数了出来。** 在同一份日志上：`servo reports 10`、`seen silent 1`、`rail cycles 2`、`rail resets 0`。⚠️ **`rail cycles` 是那个文件里唯一一个不是计数的数**——`rail` 是主板*自它启动*以来的次数，所以次数是**增加的部分**，而减少意味着主板重启，那之前的次数不可观测（`rail resets`）。⛔ **这个例外写在源码里，并由一个把行倒过来、显示出究竟是哪一栏在动的测试撑着。**

**第一次 `bench power off` 没有落下去。** 我写下那一行就立刻关掉了端口；下一次探针显示伺服在回答、`strikes: 0`——**写入返回了，而行没有到达。** 第二次把端口保持打开两秒，主板照做了。⛔ **返回的写入不是到达的行**，这正是这个仓库已经就 `sent: true` 写下过的那句话，往下深了一层。

## 没有修好的、路上发现的

**重启后的守护进程会让身体成为孤儿。** 在 `launchctl kickstart -k` 之后，新的 socket 在监听，而主板没有回来：它的旧连接**在 `FIN_WAIT_1` 里坐了一分多钟，没有 ACK**，`ping -c 2 192.168.0.19` 返回**2 发送、0 接收**，而 `arp -an` 一直握着主板自己的 MAC。⇒ **0.19.59 的方向没有变**——Mac 无法先说话——而主板坐在一个再也不会说话的 socket 的 `select()` 里，`DialTask` 没有读取的期限。

⛔ **把它带回来的只有一次复位**——`esptool` 的硬复位，线缆插着。**线缆不在的时候，那个恢复并不存在**，身体只能靠人手断电重开。

⚠️ **不作的主张：没有说这一定发生。** 2026-10-21 的四次监听器替换，都在 0.3–4 秒内自己回来了。**这是那个故障的一次观察，不是一个频率。**

## 没有主张什么

- ⛔ **头部一次也没有动。** 这一页是一次读数；它引用的位置前后相同。
- ⛔ **那两次沉默是被引起的。** 在控制台上敲下的 `bench power off` 是一条命令，而看门狗对它的回答是**机器在工作**——**不是故障自行发生。** 2026-10-19 那次自发的沉默（22.8 分钟，什么也没有问）仍然没有被解释。
- ⛔ **计数是按每次启动的。** 主板复位会把 `rail` 带回 0，而主机看不到它之前的次数。
- ⚠️ **`strikes` 在 0 和 2 上读过，从未在 1 上读过**，也从未在一次自行到来的沉默期间读过。
- ⚠️ **链路仍然没有认证**，而 `bench power off` 穿过了它。**任何能到达 3333 端口的东西，现在都能让头部瘫软**——姿势和帧早就是这样了；这一页只多说明一点：**bench 也通得到。**
- ⚠️ **这段时间里，屏幕、灯光、头部，都没有在谁眼前。**
