<!-- i18n-version: 2.4.0 | canonical: projects/stackchan/README.md | translated: 2026-10-18 -->

**Language:** [English](README.md) | [日本語](README-ja.md) | [中文](README-zh.md)

# projects/stackchan/ —— 电线之上的层

**它决定机器人正在做什么、戴着哪张脸、发什么颜色的光、意味着哪个身势。它不决定任何东西移动多远。**

⛔ **它没有机器 2 的任何数字，也不借用机器 2 的数字。** 手边这一台的刻度、零点、符号、框架、速度上限、周期与静止时间，都不在任何记录里（`docs/first-contact-stackchan.md`）。⇒ **它选择的身势是背后没有任何数字的符号，每一行的 `Decision.sent` 都是 `False`。** 这是发现，不是故障。

⚠️ **Stack-chan 的路线中，一行固件都不用烧就能检查的部分，就在这里。** 从事件到阶段的对应不需要机体测量；运动需要。**这一层建在检查能响的那一侧。**

✅ **2026-10-18 的四项裁定就是这一页的形状：** 机器人是**伙伴**，不是镜子；**只有转换时身体才动**；电线运送的是**身势命令**，不是 20 ms 的流；并且**十二个 RGB LED 是一等通道，始终亮着**。

## 连着什么，没连着什麼

✅ **它 import Pet 的 `State`，不是复制。** 五张表情只画过一次（决定 A，`projects/pet/expressions.py`）。第二套就是对同一个问题的第二个答案。

⛔ **它没有连到机体。** 没有端口、没有电线、没有固件、没有记录。检查之外的消费者只有它自己的 CLI 和守护进程的日志。⚠️ **它也还没有连到 Claude Code**——`settings.json` 里没有任何东西调用它。**这个目录是层，不是安装。**

## 六个阶段

**五张脸是 Pet 的，六个阶段是这一层的。** 阶段是机器人正在做的事，脸是它显示出来的东西。

| 阶段 | 进入的事件 | 脸 | 光 | 身体 |
|---|---|---|---|---|
| `present` | 表情到期，或醒来 | `curious` | `breathe` | 不动 |
| `greeting` | `SessionStart` | `greeting` | `warm` | `perk` |
| `working` | `UserPromptSubmit` | `curious` | `dim` | **不动** |
| `blocked` | `PermissionRequest` | `curious` | `alert` | `turn` |
| `closing` | `Stop` / `StopFailure` | `happy` / `angry` | `warm` / `error` | `nod` / `flinch` |
| `resting` | 90 秒没有事件，或 `SessionEnd` | `sleepy` | `off` | `settle`（只在离开时） |

⚠️ **支撑 `working` 的，是它不用身体表达的二十五个事件。** `PreToolUse` 和 `PostToolUse` **不用身体表达，但确实被接收了**——**每一次都会重置 idle 时钟。** ⛔ **所以，长时间的构建期间机器人也不会睡着。**

⚠️ **表情有寿命。** `greeting` 和 `closing` 在三秒后回到 `present`。**这是产品决定，不是测量值。** **一直留到下一个事件的脸，会对那个瞬间持续了多久说谎。**

## 三十三个事件，三种类型

**三十三个名字，来自 hooks 文档的表，2026-10-18 读取。** ⛔ **名字不在这里发明。** 不在列表里的名字会抛出 `UnknownEvent`——**上游新增的事件会以错误出现，而不是被静默地当作默认值。**

⛔ **分法不是「反应／不反应」。它是同一个事件的三种接收方式。**

### 转换——六个，改变阶段

| 事件 | 阶段 | 为什么 |
|---|---|---|
| `SessionStart` | `greeting` | 会话开始了 |
| `UserPromptSubmit` | `working` | 人的回合结束，机器的回合开始 |
| `PermissionRequest` | `blocked` | **唯一的打断**——机器需要人 |
| `Stop` | `closing` | 回合结束了 |
| `StopFailure` | `closing` | 因为 API 错误，回合死了 |
| `SessionEnd` | `resting` | 会话正在离开 |

### 证据——十二个，读取但不表达

| 事件 | 为什么 |
|---|---|
| `PreToolUse`, `PostToolUse`, `PostToolBatch` | 回合还活着；身体不按工具调用逐次说话 |
| `PostToolUseFailure` | 数着；一个回合里的第三次，是最初的信号 |
| `PermissionDenied` | 等待结束了——拒绝也是一种结束 |
| `Notification` | 它唤醒机器人并重置 idle 时钟；⛔ **它不是人的回答** |
| `MessageDisplay` | 它没有开始；文字显示期间一直在响 |
| `SubagentStart`, `SubagentStop`, `TeammateIdle`, `TaskCreated`, `TaskCompleted` | 回合内部；外面的 `Stop` 才是信号 |

### 忽略——十五个，不读取，但仍是生命的证据

| 事件 | 为什么 |
|---|---|
| `Setup`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `FileChanged`, `WorktreeCreate`, `WorktreeRemove` | 会话的上下文变了；身体没有参与这件事 |
| `UserPromptExpansion` | 它在 `UserPromptSubmit` 之后立即响起 |
| `PreCompact`, `PostCompact`, `PreModelSwitch`, `PostModelSwitch`, `Elicitation`, `ElicitationResult` | 还没有带数字的行为——⛔ **而且词不在数字之前加上** |

⚠️ **`ignored` 不是「没有送到」。** 三十三个全部都会重置 idle 时钟，并把机器人从 `resting` 唤醒。**「不表达」不是「没看见」。**

⚠️ **`no-behavior` 不是「没有行为」，而是「没有带数字的行为」。** 词汇是映射，不在表里的词就不在词汇里（`references/README.md`）。⇒ **对其中的任何一个作出反应，都会在它还变不成机体能做的事之前，先用掉一个词。**

## 四条通道

| 通道 | 声音 | 默认 | 运送什么 |
|---|---|---|---|
| 屏幕 | 无声 | 始终 | 脸——看过去时的信息 |
| **RGB LED ×12** | **无声** | **始终** | 呼吸、暖色、注意、熄灭——**周边视觉里的在场** |
| 脖子（2 轴） | 舵机声 | `--motion on` | **只在转换时** |
| 扬声器 | 有声 | `--sound off` | ⛔ **还不存在** |

⛔ **这里没有「无声模式」，因为名字会是假的。** 舵机会响。**运动和声音是两条轴，不是一个 enum**，脸和光不服从任何一条——**它们不发出声音。**

✅ **光是意义，不是 RGB。** `Light` 是 `off`、`dim`、`breathe`、`warm`、`alert`、`error`。映射到十二个像素是固件的工作，**这一台的 LED 顺序和颜色顺序，这里的任何记录里都没有。** 原厂固件公开了 `set_led_color`；这一层不调用它。

## 密度——只在转换时

⚠️ **身势只在阶段转换时被选中，节奏由事件本身封顶：** 回合打开时一个 `perk`，长回合关闭时一个 `nod`——**每个回合两个节奏身势。** `PermissionRequest` 是打断而不是节奏，不计入这个数。**但逃不过身体自己的下限。**

⛔ **离前一个身势不到一秒的身势会被丢弃，而不是排队**——身体栏变成 `cooldown`，`Companion.dropped` 会计数。两个理由：**排队会让这一层决定指令之间的间隔。** 并且**在 10/04 的那一台上，小于约一秒的间隔会让舵机停住并让电源轨掉落**（`MOVE_SETTLE = 1.0`）。⚠️ **那个 1.0 秒是这个包里唯一的借来的数字**——**它是另一台的下限，不是这一台的测量值。** **向安全侧借，标明是借的，在测量这一台的那天替换掉。**

✅ **光不等身体。** 即使舵机在 cooldown，阶段仍然改变，LED 也仍然改变：**唯一的打断可以失去脖子，但不会失去颜色。**

## 两个以上的窗口，一个房间

⚠️ **可能同时开着两个以上的 VSCode 窗口、跑着多个会话**（作者的要求，2026-10-18）。**脖子只有一根，脸只有一张**——无法同时映出全部，**也不能在它们之间来回转**：来回转时每一次身势都会撞上那一秒的下限，**脖子会在终端之间发抖。**

✅ **所以注意力只有一个，而且不容易离开**（`Focus`）——**最先开口的窗口取得它，并一直持有到沉默为止。** 持有者沉默 **90 秒**后——**同一个 `IDLE_SECONDS`，不是新的数**——注意力空出，由下一个开口的窗口取得。**所数的只有「持有者是不是只有一个」。**

✅ **注意力会移向人有所动作的窗口**——`SessionStart` 与 `UserPromptSubmit`——**以及机器需要人的瞬间**——`PermissionRequest`。⛔ **背景窗口的 `Stop` 不会移动它**: 机器结束，不等于人在看着那里。若允许移动，**背景任务每结束一次，脖子就会甩一次。**

⚠️ **其他窗口不会被丢弃。** 它们的事件会重置房间的 idle 时钟，并以理由 `distant` 报告——**「看见了、还活着、不是这一个」**。⛔ **那里的 `sent` 同样是 `False`。**

## 失败——连续三次

⚠️ **一次工具失败是日常，会被重试。** 它得到 `observed`，仅此而已。

- **同一个回合里连续三次 `PostToolUseFailure`**——中间没有成功的 `PostToolUse`——进入 `concern`：**光变成 `alert`，脸不变。** ⛔ **对测试失败发怒，不是这里的反应。**
- **`angry` 留给 `StopFailure`**——回合因 API 错误而死。那才是异常事件，也是唯一配得上这张脸的。
- **成功的 `PostToolUse` 把计数清零。**

## 运行它

从仓库根目录:

```
python3 -m projects.stackchan                                   # 把三十三个按三种类型打印出来
python3 -m projects.stackchan --event SessionStart@0 --event Stop@3
python3 -m projects.stackchan --motion off --event Stop@0.1
python3 -m projects.stackchan --sound on --event SessionStart@0
python3 -m projects.stackchan --json --event PostToolUseFailure@0
python3 -m projects.stackchan --event left:SessionStart@0 --event right:PermissionRequest@2
python3 -m projects.stackchan.daemon --socket /tmp/ekl.sock   # 监听；Ctrl-C 或 SIGTERM 停止
echo '{"session_id": "main", "hook_event_name": "SessionStart"}' | python3 -m projects.stackchan.hook --socket /tmp/ekl.sock
```

⚠️ **窗口写作 `窗口:事件@秒`；不写窗口就是 `main`，所以单窗口的剧本读起来与以前相同。** ⚠️ **时间由剧本给出，不从时钟读取。** 剧本不能倒流；倒流的剧本会被拒绝。这使一次运行可以复现——**也是 CLI 不是钩子所调用的东西的理由**（见下）。⚠️ **每一行都显示光和身体，脸改变时还显示脸的画**——**即使身势被丢弃，也仍然读得出反应。**

## 钩子还缺什么

⛔ **Claude Code 的钩子是一个事件一个进程。`Companion` 是一个在事件之间保持阶段、期限和 cooldown 的对象。** 这里没有任何东西把那个状态跨进程携带。

⇒ **一个长命进程现在有了**——`projects/stackchan/daemon/`，它拥有时钟、companion 和套接字。**核心（`room.py`）不读时钟、不读套接字，边缘（`__main__.py`）独自持有这两者。** ⛔ **它没有被安装**：没有 launchd 任务，钩子仍然够不到它。 ⚠️ **直接接到这个 CLI 的钩子，会在每个事件上重置阶段和 idle 时钟**——正是它要防止的洪水，而且更糟：**机器人永远无法安定，也无法入睡。**

✅ **而同一天，客户端也有了**——`projects/stackchan/hook/` 从标准输入读一个事件，发送一行，**什么都不打印，无论发生什么都以 0 退出。** ⛔ **它没有注册进 `settings.json`**：还没有东西调用它。

✅ **客户端发送的是事件的名字和窗口的名字，而不是提示词。** 时间由守护进程在行到达时盖戳，所以客户端不带时钟，也不带状态。机器人需要知道回合开始了，而不是说了什么；**需要窗口的名字，只是因为窗口共享一个身体。** **用结构守住隐私，而不是用方针。** ⚠️ **启动与停止的设计是 `docs/stackchan-daemon.md`**——**循环、套接字和客户端已经建好；launchd 任务和 `settings.json` 里的注册还没有。**

⚠️ **通往机体的路也缺:** 屏幕的渲染器、LED 的驱动、声音、串行电线。**这一层的输出是 `Decision`；除了终端和守护进程的日志没有消费者。**

## 保住房间的进程（2026-10-18）

✅ **`projects/stackchan/daemon/` 是唯一的长命进程。** `room.py` 是核心——请求的形状、房间、下一个期限——它不读时钟、不读套接字、不读环境。`__main__.py` 是边缘，它是唯一打开套接字并读取 `time.monotonic()` 的文件。

- **套接字就是锁。** 第二个实例探测它，不对机体说一个字就以退出码 3 结束；陈旧的套接字会被 unlink 并替换。没有 pidfile。
- **一行 JSON 进，一行 JSON 出**——`{"session": …, "event": …}`。**未知的键会被拒绝**，所以提示词无法搭车；未知事件和读不出的行会带着代码被拒绝。
- **时间由守护进程盖戳。** 客户端不发送时钟。
- **循环等待套接字或下一个期限**——`min(hold_until, idle_until, quiet_until)`——醒来时发出 `settled` 或 `slept`。**没有固定的刻。**
- **`SIGTERM` 让它停止**，unlink 套接字并以 0 退出。**不对机体发送任何东西**——因为还没有机体。

**客户端**是 `projects/stackchan/hook/`——一个事件一个进程。它读标准输入（上限 1 MiB），**只重建两个栏位**，发送，**不读回信就关闭。** **守护进程不在，不是钩子的失败: 以 0 退出，保持沉默。** 重建在 `client.line_from` 里，是纯函数，不用进程就能检查。

⛔ **没有安装。** 没有 launchd 任务，也没有 `settings.json` 里的注册；那份设计的记录是 `docs/stackchan-daemon.md`。

## 检查了什么

**`tests/test_stackchan_behaviors.py` 有三十四条主张，`tests/test_stackchan_daemon.py` 有二十四条，`tests/test_stackchan_hook_client.py` 有十九条**，它们与其余检查一起运行:

- 列表是三十三个，没有重复；每个事件恰好属于三种类型之一，三种类型分割整个列表。
- 每个事件都带理由代码——**没有空白。**
- 一个剧本到达全部六个阶段、五张脸和六种光。
- 长回合点头，短回合不点头。
- 连续三次失败是第一个信号，第四次不是，成功会重置计数。
- 到达 `angry` 的路只有 `StopFailure`。
- `PermissionRequest` 是唯一的打断，`Notification` 不会结束等待。
- **三十三个事件全部会把机器人从 `resting` 唤醒**——包括被忽略的那些。
- 证据事件会重置 idle 计时器。
- 表情到期并回到 `present`。
- cooldown 里的身势被丢弃，**但光仍然改变。**
- 关掉运动，脸和光仍然保留。
- 声音默认不出，只跟随转换。
- **一个身势也不会被发送**——每一行的 `sent` 都是 `False`。
- **有多个窗口时，最先开口的窗口取得注意力**；人在另一个窗口动作时它会移过去，工具调用与背景窗口的 `Stop` 不会，背景窗口的 `PermissionRequest` 会夺走它。
- **规则数不到二**: 三个窗口也按同一条规则行动。
- 注意力在持有者沉默时、结束时空出；在那之前，持有者的事件让房间保持醒着。
- 剧本可以给窗口命名，每一行都说出它来自哪个窗口。
- 理由和身体两栏都是闭集，而且都能到达。
- 剧本可复现，倒流的剧本被拒绝。
- parser 在三种语言里都能建起，而且帮助不同。
- **这个包里没有机器 1 的名字、数字或模块**——用 AST 走过 `DofRealityWire`、`Envelope`、数字 190、512、833，以及任何来自 `engine` 的 import——并且没有 `motions/` 目录。

**守护进程再加二十四条:**

- 套接字会回答，而日志里的行就是客户端收到的同一行。
- 第二个实例以 3 退出，第一个继续回答。
- 陈旧的套接字会被 unlink 并替换。
- 未知的键、未知的事件、读不出的行，各自以自己的代码被拒绝。
- **提示词到不了日志**——秘密不在守护进程打印的任何一行里。
- 什么都不发的客户端会被关闭，下一个请求仍然能通过。
- 干净的退出会删除套接字。
- 下一次醒来先是表情，然后是 idle 时钟；`blocked` 和 `resting` 没有期限。

**客户端再加十九条:**

- 一份完整的钩子输入只产出一行 `session` 与 `event`——**提示词、cwd 和工具输入都不在其中。**
- 缺少两个栏位的输入被丢弃，未知事件在到达套接字之前被丢弃。
- 那一行能用守护进程自己的模式读出，并且不超过守护进程的上限。
- **套接字路径只有一种拼写**，两个入口都用它。
- 真实的输入到达房间，而其中的提示词不在守护进程的日志里。
- 没有守护进程、读不出的输入、过长的输入，都是沉默地以 0 退出。
- **客户端不等待回信**——永不作答的对方也不会让它迟延。

⚠️ **这些主张中没有一条是关于机体的。** 一次绿色的运行说的是，**这一层按它被告知的方式计算了**——与 `CLAUDE.md` 对五项检查要求的同一句话。

## 这里没有的东西

- **没有机器 2 的数。** 五个身势是候选词，不是词汇表里的行。行是在那个词于那台机体上变成数字的那天写下的。`projects/pet/motions/greeting.json` 是机器 1 的计数；借用它，这一层就会主张一个不会发生的运动。
- **没有串行层，没有固件，没有烧写。** 见 `docs/first-contact-stackchan.md`。
- **没有 LED 驱动，也没有屏幕渲染器。** 光是意义；没有东西把它变成像素。
- **没有声音。** `--sound on` 指出的是一条不存在的通道，而这一台的扬声器从未被验证。
- **没有头部触摸输入。** 传感器在这一台上有效（2026-10-18 在 AI.AGENT 中观察），但那是机体的输入，固件必须去读它。**钩子不是头。**
- **没有钩子注册，也没有 launchd 任务。** 客户端存在，但没有什么调用它——`settings.json` 没有被碰过——登录时也没有东西启动守护进程。
- **没有记录。** `projects/` 放的是工作；记录的容器仍然空着，而这一层从未观察过机体。
