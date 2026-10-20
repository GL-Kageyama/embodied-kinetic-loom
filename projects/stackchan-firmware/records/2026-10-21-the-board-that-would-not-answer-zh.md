<!-- i18n-version: 1.1.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-board-that-would-not-answer.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-board-that-would-not-answer.md) | [日本語](2026-10-21-the-board-that-would-not-answer-ja.md) | [中文](2026-10-21-the-board-that-would-not-answer-zh.md)

# 没有回答的基板 — 2026-10-21

⛔ **这份文件的脊梁是观察。程序的数字被引用在它内部作为证据，而不是围着它。** tty 接受的帧，不是基板收到的帧。

**数了什么。** 一台机体、一台 Mac、一根 USB 线、那一次插拔，以及已安装守护进程的日志——从登录时启动，到回来的那一帧。**没有数什么:** 基板为什么沉默、电源开关是否打开、沉默期间是否有东西动过、玻璃上显示的是什么。

## 看到的

**作者自己的说法只有一句:** 2026-10-20 关掉了 Mac，**同时把机体的电源也关掉了。** 2026-10-21 的早晨，Mac 回来了，守护进程也跟着起来了。

**插拔之前，主机看到的:**

- launchd 的作业在运行（`embodied-kinetic-loom.stackchan-next`，PID 822），套接字也活着
- `/dev/cu.usbmodem101` 存在，USB 上能看到 **`USB JTAG_serial debug unit`（Espressif）**
- 守护进程**写出了 8 帧，8 帧全是 `sent: true`，而 `accepted: true` 一帧也没有**

**主机拿不到的:** `SessionStart` 时守护进程自己的探针读到 `{"position": null, "heard": false, "read": ""}`；手写的 `bench pos` **什么也没有**返回；IDF 环境里的 `esptool.py read_mac` 以 **`No serial data received`** 失败——两次，一次直接、一次加 `--before usb_reset`。

⇒ **USB 设备在那里，芯片没有在回答。**

## 从猜测组出来的动作

⚠️ **守护进程没有等待。** 在 `SessionStart` 它流出了 `look_up`: `{"neck": "look_up", "from": [0, 30], "to": [80, 500], "poses": 40, "seconds": 0.783}`。

⛔ **`from: [0, 30]` 不是测量。** 基板什么都没回答，所以既没有最后的姿势也没有探针，**计划是从默认值组出来的。** 它的判定始终没有回来（`verdict: null`、`read: ""`）。

⚠️ **这份文件之所以必要，就是这个形状:** 沉默的基板和死掉的基板，从这里看是一样的，**而日程表不区分这两者。**

## 插拔

作者写了「差し直した」——把线拔出来，再插回去。**然后，同一个主机、同一份代码:**

```
bench: yaw=ok pitch=ok
bench: yaw raw 482, angle 6.8 deg (zero 460)
bench: pitch raw 778, angle 49.3 deg (zero 620)
alive
```

而手写的帧返回了 `(sent, accepted) = (True, True)`。**守护进程自己接下来的帧带上了 `accepted: true`。**

## 插拔只维持了七十秒

**这一节在这份文件最初写下时并不存在。** 内核自己的日志带着它的两端:

- `03:46:51.190` — `AppleUSBHostPort::enumerateDeviceComplete_block_invoke: enumerated 0x303a/1001/0101 (USB JTAG/serial debug unit / 1) at 12 Mbps`
- 基板回答了 `bench pos` 和 `alive`，手写的帧返回了 `accepted: true`
- `03:48:01.891` — **70.7 秒之后** — `AppleUSBHostPort::terminateDevice: destroying 0x303a/1001/0101 (USB JTAG/serial debug unit): hardware port disabled`
- `/dev/cu.usbmodem101` 消失了: `esptool.py read_flash 0xd000 0x2000` 停在 `could not open port … No such file or directory`；到 03:55，这台设备既不在 `ioreg` 也不在 `system_profiler` 里，总线上也没有任何东西在重新枚举它。

⇒ **插拔买到的只有七十秒。**

⚠️ **插拔有没有复位芯片，并不知道，而那七十秒的意思正取决于这个。** 如果线拔出时芯片的电源断了，那么这就是**一个在冷启动后大约一分钟就重现的故障**。如果是电池撑住了它，芯片一次也没有重启，**同一个状态两次结束了端口**。⛔ **这里没有任何东西能区分这两者**——而当时的固件，一行能说出这件事的字也没有印: **`reset: reason` 那一行就是它，而它已经在下一个构建里了。**

## 作为证据的数字

| 什么 | 值 | 从哪里来 |
|---|---|---|
| 沉默期间写出的帧 | 8，全部 `sent: true` | 守护进程的日志 |
| 沉默期间被接受的帧 | **0** | 守护进程的日志 |
| 守护进程的探针 | `position: null`、`heard: false`、`read: ""` | 守护进程的日志 |
| 手写的 `bench pos` | 空 | 主机自己的 tty |
| `esptool.py read_mac` | `No serial data received`，两次 | IDF 的 venv，esptool 4.12.0 |
| 从 `[0, 30]` 流出的 pose | 40——`applied` 与 `late` 都没有被确认 | 守护进程的日志 |
| 插拔之后 | `yaw raw 482`、`pitch raw 778`、`alive` | 基板自己的那一行 |
| 之后的帧 | `sent: true`、`accepted: true` | 基板自己的那一行 |
| 设备被枚举 | `03:46:51.190` | 内核日志 |
| 端口被终止，第一次 | `03:24:03.560` | 内核日志 |
| 端口被终止，第二次 | `03:48:01.891` | 内核日志 |
| **插拔维持了多久** | **70.7 秒** | 上面两个内核日志时刻 |

## 这份文件没有说的

- ⛔ **没有说基板为什么沉默。** 电源开关、线的接触、卡住的固件、ROM 的状态——**四个候选，一个都没有分开。**
- ⛔ **没有说沉默期间有没有东西动过。** 写下了 40 个 pose，**一个都没有被确认**，基板的判定没有回来。
- ⛔ **没有说玻璃是黑的。** ⚠️ **固件在启动时不画脸**，所以在屏幕上，运行着的基板和不运行的基板看起来一样——**这就是这份文件存在的理由，不是对今天早晨的评论。**
- ⛔ **没有说两次终止是同一个故障。** 一次在沉默 23 分钟之后，那一刻并没有握着端口；另一次在基板正在回答的 70.7 秒之后。**形状相同，机构并未确立。**
- ⚠️ **这不是诊断。** **恢复不是诊断**——2026-10-19 那份文件对电源轨说过完全相同的话，同样的形状第二次出现。⚠️ **插拔是同一个形状的第三次**: 它维持了多久是知道的，它为什么有效是不知道的。
