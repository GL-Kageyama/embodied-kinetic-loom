<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-board-dials-out.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-board-dials-out.md) | [日本語](2026-10-21-the-board-dials-out-ja.md) | [中文](2026-10-21-the-board-dials-out-zh.md)

# 基板向外拨号 — 2026-10-21

⛔ **这份文件的脊梁是观察。程序的数字被引用在它内部作为证据，而不是围着它。** 接收端接受的一行，不是让头动起来的那一行。

**数了什么。** 一台机体、一台 Mac、一个接入点、**一整段时间里都插着的 USB 线一根**，以及一个套接字。**没有数什么:** **USB 线被拔下的区段一个也没有**——**下面没有一条测量是在控制台消失时取得的**——也没有第二条连接、真实的断线、抓包。下面每一行都从基板自己打开的那条链路回来；它这样做的时候，线还在那里。

## 被问的是什么

「最終的には、usb接続なしで動くようになるよね？」——最终会在没有 USB 线的情况下运行吗？

⚠️ **这个问题没有得到「是」，得到的是一个形状。** 上一页只留下一个方向: Mac 从来无法先开口，而基板打开的一条连接承载了两个方向。⇒ **所以由基板拨号。** 这是它第一次发生的构建。

## 看到的

**基板在启动时自己拨号了，在它说自己 ready 之前。** 没有人输入任何东西: 地址在 NVS 里，由 `bench dial` 写入过一次。

```
dial: pointed at 192.168.0.103:3333
waypoint: dial
dial: connected to 192.168.0.103:3333
ready. type `help`.
```

**头的位置沿着那条链路回来了。** Mac 把它正在监听的套接字里写入了 `bench pos`:

```
sent b'bench pos\n'
recv bench: yaw=ok pitch=ok
recv bench: yaw raw 478, angle 5.6 deg (zero 460)
recv bench: pitch raw 777, angle 49.0 deg (zero 620)
```

**一个帧下来了，基板在同一个套接字上回答。** 写入之后 `0.159 秒`，证据是基板自己的受理行——守护进程自 0.19.41 起一直在 USB 控制台上读的那一行:

```
sent b'{"face":"curious","gesture":null,"light":"writing","sound":null}\n'
recv frame: light=writing face=curious gesture=none sound=none
```

**一个姿势下来了，头动了。**

```
sent b'pose 100 491*26\n'
recv pose: stream started — goals on the present positions (yaw 478, pitch 777), torque on
recv pose: stream lost after 500 ms — torque released
recv pose: 1 applied, 0 refused, 0 clamped
```

⚠️ **要求 yaw 10.0°，头动了 6 个计数——1.9°——而下一次 `bench pos` 读到 `yaw raw 484`、7.5°，离目标差八个计数。** ⛔ **那个损失正是 0.19.36 在这台机体上已经量过的: 它是舵机的，不是日程的——而且无论那行走线缆还是走套接字，大小相同。** 写在这里，是作为**同一个东西**动了的核对，不是作为新发现。

**而链路拒绝了会改变「如何到达这块基板」的那些命令。** 下面的拼写是 `HandleBench` 真正接受的形状——它会跳过前导空格，所以两个空格是真正的命令，不是笔误:

```
sent b'bench  wifi\n'
recv dial: refused — that command is the console's
```

⛔ **那个拒绝在抵达机体之前，先在自己身上找到了一个洞。** 这条规则被写成严格匹配 `bench <verb>`，于是让 `bench  wifi`——两个空格——直接通过，因为它没有跳过 `HandleBench` 所跳过的那些空格。`tests/test_stackchan_dial_policy.py` 是先写的，并在那一行上失败；**被修好的是源码，不是那一行。**

## 没有声称的事

- ⛔ **线从来没有被拔下过。** 上面没有一行是在 USB 拔掉的状态下取得的。**这一页测量的是承载身体全部对话的那条链路；它没有测量身体在失去线缆之后仍然活着。** 那是两个不同的主张，这里只做了第一个。
- ⛔ **守护进程没有用这条链路。** 它仍然每一帧、每一个动作打开一次 `/dev/cu.usbmodem101`。上面所有测量中，链路另一端坐着的是为此写的一个探针——`/tmp/ekl-dial-listen.py`——而⚠️ **探针不是运输方式**。
- ⛔ **0.159 秒不是链路的代价。** 在那段区间里，基板画了一张脸、写了十二个 LED。把套接字和基板自己的工作分开的东西，这里一个也没有。
- ⛔ **一条连接，一次。** 真实断线后的重连、Mac 地址变化时的行为、两条连接同时是否安全，全部未测。⚠️ **基板带退避地重试，而它这样做的时候从未被看过。**
- ⚠️ **地址是一份 DHCP 租约。** `192.168.0.103` 是那天晚上 Mac 所在的地方。Mac 移动时去发现它的东西这里没有，而⛔ **线拔掉之后，也没有可以输入新地址的控制台。**
- ⛔ **对这台机器，从未跑过第二个写入者。** 控制台仍然持有身体，链路现在通过同一扇门（`RunLine`）来要它——一个互斥量，一次一个。**「这样就够了」是对源码的阅读，不是测量。**
