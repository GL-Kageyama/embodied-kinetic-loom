<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-11-08-the-body-that-carried-its-networks.md | translated: 2026-11-08 -->

**Language:** [English](2026-11-08-the-body-that-carried-its-networks.md) | [日本語](2026-11-08-the-body-that-carried-its-networks-ja.md) | [中文](2026-11-08-the-body-that-carried-its-networks-zh.md)

# 带着自己的网络出门的身体 — 2026-11-08

✅ **作者把这具身体带到了另一个地方，并问它能否持有不止一个网络。** ⛔ **它不能**——一个 SSID、一个 PSK，厂商的单一 station 配置，而 `bench wifi join` 会把它覆盖掉。**于是这一天做了一张四行的表，身体连上了一个它从未见过的网络，而它取种的那一个却够不到。** ⛔ **接着链路没有通过**: 同一天里，身体与 Mac 在任何一个方向都够不到对方，**而身体在 19 ms 内够到了网关。**

**数了什么。** 一台机、一台 Mac、一条串口控制台、一次硬复位。下面的数字来自板子自己的行（`bench wifi`、`bench dial`）与 Mac 的行（`arp`、`ping`、`nc`、`ifconfig`、`ioreg`），每个数字都写明了是哪一个。**没有数的:** 这个地方有多少个网络——一次扫描看到 **14** 个，**而安静的那个看不见**；**Mac 当时在哪个 SSID 上**——`system_profiler` 隐去了它，`networksetup` 回答*未关联*，`sudo wdutil info` 要一个它没有的密码；是否有别的无线客户端可达——**没有第二台可以问**；以及隔离者是 AP 还是它身后的东西——**抓包需要 root，所以一个包也没有抓。**

## 在这一天之前身体持有什么

⛔ **恰好一个网络。** station 从厂商向导留在 NVS 里的东西站起来，而控制台的 `bench wifi join` 把它写掉——**没有第二行，也没有不靠密码回到旧网络的路。** ⇒ **被带到从未见过的网络之处的身体，可以被教会那个网络，却无法被教会同时保住两个。**

## 造了什么

✅ **一张四行的表，装在一个块里。** `main/wifi_profiles.h` / `.cpp` 是一个纯模块——不含任何 ESP-IDF 头文件，由 `tests/test_stackchan_wifi_profiles.py` 在主机上编译，沿用了 `wifi_retry.cpp` 与 `dial_scan.cpp` 的先例——它持有:

| 什么 | 值 | 怎么定的 |
|---|---|---|
| 行数 | **4** | 选择，不是测量 |
| 一行 | **97 字节**——SSID 占 33，PSK 占 64 | 驱动自己的字段宽度，含 NUL |
| 这个块 | 至多 **390 字节**，版本 **1** | 2 + 4 × 97 |
| 一行的轮次 | **2 次尝试** | 选择: 第二个网络在第一次尝试后 6 秒到达，而 2 / 4 / 8 秒的阶梯得以保留 |

- ⚠️ **64 个字符的 PSK 过去会被无声截断**——驱动的字段是含 NUL 的 64 字节——所以表会拒绝超过 63 个字符的 PSK，并打印 *the psk is longer than 63 characters*。**它不缩短。**
- ✅ **`add` 就地更新一行，`remove` 保持其余的顺序**；无线电所在的那一行带 `*` 打印。
- ✅ **等待保留它的阶梯，动的只是行**——早期草稿会随行一起复位等待，那会在网外每两秒永远重试，**正是 `wifi_retry` 存在所要避免的空转。**
- ⛔ **控制台可以覆盖这一轮**: `bench wifi join` 抬高 `g_epoch`，而 retry 任务在 epoch 一动时就退出——**一个人刚刚选中的网络，不会在他眼前被轮走。**
- ✅ **控制台有三个动词**: `bench wifi add <ssid> [psk]` 存而不切换，`forget` 删掉一个，`join` 存下并连接。⛔ **在链路上它们被拒绝**——`bench wifi …` 属于控制台，因为**出现在明文 socket 上的 PSK，就是写在线上的 PSK。**

## 机做了什么

✅ **第一个烧进去的版本 panic 了。** 在 `wifi: added "Cokoga-5F" (2 of 4)` 之后，板子打印了 **`***ERROR*** A stack overflow in task wifi_retry has been detected`**——`ApplyProfile` 把 390 字节的整张表压到了 **3,072 字节**的任务栈上。⇒ **`RowAt` 改为只拷贝 97 字节的一行，栈升到 4,096**（⚠️ **是余量，不是测量**——机器给出的数字只有 3,072）。

✅ **修好之后，不重启即测量**: `wifi: added "Cokoga-5F" (2 of 4)`、`wifi: connected ip=10.5.0.136`，而 `wifi: list 2 of 4` 两行都点名，`*` 落在会场那一个上。

✅ **然后是一次硬复位——这正是这个功能存在所要的测量**——身体先试了家里的网络，听不到它（原因 **201, no ap found**）:

```
wifi: asking again — attempt 2, waited 4000 ms, on "BFW6K-G-48420_EXT"
wifi: not connected — reason 201 (no ap found)
wifi: trying "Cokoga-5F" (2 of 2)
wifi: asking again — attempt 3, waited 8000 ms, on "Cokoga-5F"
wifi: connected ip=10.5.0.136
wifi: associated after 3 attempt(s)
```

⚠️ **打印出来的 `waited` 是刚刚睡过的等待**，所以三次尝试是 2,000 / 4,000 / 8,000 ms，而关联落在启动后 **20.2 秒**（`sta ip` 在 `I (21289)`）。⚠️ **第 1 次尝试的那一行不在采集里**——打开控制台时它已经过去——所以**第一个等待是从阶梯读的，不是从一行读的。**

✅ **它熬过了第二次启动**: `bench wifi` 回答 `wifi: list 2 of 4`，`"BFW6K-G-48420_EXT"` 无记号，`* "Cokoga-5F"`，ch 1，RSSI −55。⇒ **表在 NVS 里，不在 RAM 里。**

⚠️ **控制台的名字随端口移动了**: 把线换到另一个 USB 口之后，设备从 **`.2101`** 变成了 **`/dev/cu.usbmodem101`**——⛔ **那个号码属于端口，不属于板子**，记住它的脚本什么也找不到。

## 网络做了什么

⛔ **身体与 Mac 之间，任何方向都没有东西通过。**

| 方向 | 看到什么 | 出处 |
|---|---|---|
| 身体 → Mac (`10.5.0.114:3333`) | `gave nothing in 3002 ms (errno -1)` | 板子的控制台 |
| 同一个，数出来 | **976 connect attempt(s) failed**、connect **0**、**934 address(es) swept**、找到 **0** | `bench dial` |
| Mac → 身体 (`10.5.0.136`) | `? (10.5.0.136) at (incomplete)`、`ping` → `No route to host`、`nc` → `No route to host` | `arp -an`、`ping`、`nc` |
| 身体 → 网关 (`10.5.0.1:3333`) | `gave nothing in 19 ms (errno 104)` | 板子的控制台 |

⇒ **身体的无线电是好的**——它够到了网关自己的端口，19 ms 被拒——**而两个无线客户端看不见彼此**，同时 Mac 的防火墙是**关的**（`socketfilterfw --getglobalstate` → `State = 0`），起来的口只有 Wi-Fi。

⚠️ **这个读法是客户端隔离**——AP 上的隐私分隔器，访客网络被配置成的样子。⛔ **它是读法而不是测量**: 一个包也没抓，没有第二台无线客户端可比较，**Mac 在哪个 SSID 上也没有确定。**

⚠️ **失败连接里有三个打开了却什么也没说**: 扫描包含身体自己的地址，身体自己的探针服务器（`net.cpp`）打印了 **`net: open from 10.5.0.136`**，而那个服务器逐行回答 `ok <n>`，**从不写 `loom`**。⇒ **`3 opened without a greeting` 大概是身体遇见了自己**——⛔ **计数器不点出对端，所以三个的身份都是推断。**

## 这一天试了、却做不到的

- ⛔ **另一个网络**: 扫描看到 14 个接入点（`Cokoga-5F`、`monchan-only`、`smartut11`、`Cokoga-4F`、`Buffalo-G-7C98`、`AQyrkDo-7915`、`IODATA-513df8-2G`、`Buffalo-2G-D820`，以及同名的弱副本）——**而 Mac 没有其中任何一个的密码**。Keychain 对七个名字都回答 *not in Keychain*。⇒ **换一个网络需要 Mac 没有的密码。**
- ⛔ **有线**: 以太网适配器始终没有枚举出来——`ioreg -p IOUSB` 只显示**一台设备，Espressif 的 JTAG/serial 单元**，三个 Thunderbolt 口都回答 `No device connected`，`en4` / `en5` / `en6` 在两次换线与两个端口之间一直是 `inactive`。⇒ **没有第二个口可以承载链路。**
- ✅ **作者的计划有三步**——*先试多个网络，再找线，再放弃*——而这一天停在第一步与第二步之间: ⛔ **路由器不是作者的，碰不得**（「ルーターは触れない」），而且没有一根线到得了 Mac。**下一次尝试在家里**（「家でwifi接続をやってみる」）。

## 这份记录没有说的

- ⛔ **AP 隔离它的客户端。** 证据与之一致，并不证明它。
- ⛔ **表在家里会正确地轮转。** 家里的网络被取种为第 1 行，从这里一次也没有到达；**测到的是离开它的轮转，而不是回到它。**
- ⛔ **身体这一天做过任何事。** 没有流过手势，没有受理过帧，没有判定过脸，**也没有眼睛报告过屏幕**——守护进程的行从第一分钟起就是 `sent: false, err: "nobody"`。
- ⛔ **玻璃是否暗过。** 没有链路五分钟是规则，而链路一次也没有打开；⛔ **没有人看**，而一行控制台输入会唤醒身体，这一天打了好几行。
- ⛔ **有什么被修好了。** 四行的表是一个在机身上跑过的机构；**作者要的是一具在被带到的地方能工作的身体，那还没有被观察到。**
