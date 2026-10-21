<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-body-that-asked-again.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-body-that-asked-again.md) | [日本語](2026-10-21-the-body-that-asked-again-ja.md) | [中文](2026-10-21-the-body-that-asked-again-zh.md)

# 又问了一次的身体 — 2026-10-21

⛔ **这一页是一次断开、五次询问、以及一个在没有网络的情况下仍继续运行的身体的记录。** **著者把机体搬到约50 m 之外，然后带了回来。** ⚠️ **控制台一行也没有丢**，所以下面的窗口是完整的。**著者所做的就是脊梁，程序的数字作为证据引用在其中。**

**数了什么。** 一台机体、一个控制台（`/dev/cu.usbmodem101`，由一个给每行打上时刻的计量器读取）、一个接入点（`BFW6K-G-48420_EXT`，ch 6）、一次步行。**没有数的：** 接入点那边的日志、任何抓包、最后一个信标的时刻——驱动要等 **25,000 ms** 的信标丢失之后才把它叫作断开，而那个等待是设定，不是这次步行的测量——以及⛔ **身体不在的时候屏幕有没有动过什么：没有人看着并说出来。**

## 著者做了什么

**把它搬到离接入点约50 m 的地方**——著者自己的估计——**然后带了回来。** ⚠️ **USB 线也一起被搬走了**。计量器从17:55一直到结束都握着端口，**没有缺一行。**

## 基板说了什么

```
17:59:31.360 wifi: not connected — reason 200 (beacon timeout)
17:59:31.361 dial: the host let go
17:59:33.360 wifi: asking again — attempt 1, waited 2000 ms
17:59:35.770 wifi: not connected — reason 201 (no ap found)
17:59:37.361 wifi: asking again — attempt 2, waited 4000 ms
17:59:39.771 wifi: not connected — reason 201 (no ap found)
17:59:45.362 wifi: asking again — attempt 3, waited 8000 ms
17:59:47.772 wifi: not connected — reason 201 (no ap found)
18:00:03.771 wifi: not connected — reason 201 (no ap found)
18:00:31.369 wifi:state: init -> auth (0xb0)
18:00:31.745 wifi:connected with BFW6K-G-48420_EXT, aid = 9, channel 6, 40U, bssid = dc:62:79:d0:ad:2e
18:00:31.746 wifi:security: WPA2-PSK, phy: bgn, rssi: -72, cipher(pairwise:0x3, group:0x3), pmf:0
18:00:31.751 wifi: associated — waiting for an address
18:00:32.843 esp_netif_handlers: sta ip: 192.168.0.100, mask: 255.255.255.0, gw: 192.168.0.254
18:00:32.844 wifi: connected ip=192.168.0.100
18:00:32.860 wifi: associated after 5 attempt(s)
18:00:39.102 dial: connected to 192.168.0.103:3333
```

- ⛔ **第一个理由是 200，之后的每一次尝试都是 201。** 200 是失去了信标的 association，201 是找不到接入点的 connect。**两个都是驱动的话**，接入点那边没有被读过。
- **`dial: the host let go` 在断开后 1 ms 到达**——链路是架在那条无线电上的套接字，所以它随无线电一起死。
- ⛔ **`alive` 从 17:59:33.965 到 18:00:30.963 每3秒继续打印**——**在身体下面完全没有网络的二十行。** 网络停了，身体没有停。
- **回来的地址是同一个**：`192.168.0.100`，一个 DHCP 租约。⇒ **重连不需要领到新地址才被找到。**

## 没有打印出来的两次

⛔ **控制台只显示了三条 `asking again`，而基板数了五次。** `wifi_retry::worth_printing` 只打印最前面的三次、以及之后每十次一次，所以**第4次和第5次一行也没留下。**

| 尝试 | 等了 | connect 发出的时刻 | 打印了吗 |
|---|---|---|---|
| 1 | 2,000 ms | 17:59:33.360 | ✅ |
| 2 | 4,000 ms | 17:59:37.361 | ✅ |
| 3 | 8,000 ms | 17:59:45.362 | ✅ |
| 4 | 16,000 ms | 18:00:01.362 | ⛔ **没有行** |
| 5 | **30,000 ms**——上限 | 18:00:31.362 | ⛔ **没有行** |

⚠️ **两个没有打印的时刻是从打印出来的等待算出来的，不是基板发出的行。** 它们背后的失败是行——18:00:03.771 的 `reason 201` 属于第4次。

⇒ **数 `asking again` 行的人会把尝试数少。** 算数的数是基板的——控制台上的 `wifi: associated after 5 attempt(s)`，以及 18:01:43 `bench wifi` 的 `5 retries since boot, last drop reason 201 (no ap found)`。

## 回来的东西

| 什么 | 值 | 从哪里 |
|---|---|---|
| association | 18:00:31.369 的 `init -> auth`，18:00:31.540 的 `assoc -> run` | 驱动自己的行 |
| 信号 | **rssi −72**（搬走前是 −56） | `wifi:connected` |
| 地址 | `192.168.0.100`，**association 之后 1.48 秒** | `esp_netif_handlers` |
| 基板的数 | `wifi: associated after 5 attempt(s)`，**地址之后 16 ms** | 重试任务 |
| 链路 | `dial: connected to 192.168.0.103:3333`，**地址之后 6.24 秒** | `dial.cpp` |
| 之后 | `associated, 192.168.0.100`、**rssi −61**、`5 retries since boot`、`sys_evt stack 1604 bytes never used` | `bench wifi` |

⛔ **栈的余量没有动**：17:55:06（启动）是1604字节，18:01:43 还是1604字节——**而在这之间，事件任务跑了六个断开事件。** 修好 0.19.59 启动循环的那个 4,096 tick，在这一页测到的负载下仍然有效。

## 这没有确立的东西

- ⛔ **回来的网络会不会在等待结束之前被注意到。** 第5次 connect 在 18:00:31.362 发出，association 在它之后 7 ms 落地——**两者重合了，所以这次运行说不出「接入点回来之后，身体要等多久」。** ⇒ **按设计最长 30,000 ms**：结束等待的是 association，而接入点回来不是这个任务所听的事件。⚠️ **这次运行没有测那个窗口。**
- ⛔ **为什么第一个理由是 200**——接入点那边没有被读过，最后一个信标的时刻也没有留下。
- ⛔ **距离。** 50 m 是著者的估计，中间隔着几堵墙没有数。
- ⛔ **屏幕。** 身体不在的时候它映着什么，没有人说。
- ⚠️ **碰到上限只有一次，是第5次。** 更长的断会打印第10次和第20次，中间什么也不出——**那是规则，不是这次运行展示的东西。**
- ⚠️ **一次步行不是一条曲线。** 规则的两个数（2,000 ms 和 30,000 ms）是选出来的，这一页测的是一次断开的形状，不是曲线的拟合。
