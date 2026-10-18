# -*- coding: utf-8 -*-
"""**事象を、段階・顔・光・身振りの記号に決める層。** `Motion Intent` より上流であり、数を持たない。

⛔ **この層は時計を読まない。** 時刻は呼び出し側から値で来る
（`offer(event, at)` と `tick(at)`）。
⇒ **同じ台本を渡せば、同じ判定が返る。** これが焼く前に検査できる理由である。

## 相棒であり、鏡ではない（決定、2026-10-18）

⛔ **エージェントの状態は、すでにターミナルに在る。** ロボットが同じ情報を繰り返しても、
情報量はゼロである。⇒ **この層が表すのは遷移だけである**——
**人の番・機械の番・休む時。** **作業中は、顔も体も動かさない。**
光だけが低く呼吸し、そこに何かが居ることを周辺視に伝える。

## 6つの段階

| 段階 | 入る事象 | 顔 | 光 | 体 |
|---|---|---|---|---|
| `present`（在席） | 表情が尽きたとき／起きたとき | curious | breathe | 動かない |
| `greeting`（挨拶） | `SessionStart` | greeting | warm | `look_up` |
| `working`（作業中） | `UserPromptSubmit` | curious | dim | **動かない** |
| `blocked`（許可待ち） | `PermissionRequest` | curious | alert | `look_side` |
| `closing`（締め） | `Stop` / `StopFailure` | happy / angry | warm / error | `nod` / `recoil` |
| `resting`（休息） | 無事象が続く／`SessionEnd` | sleepy | off | `rest`（去るときだけ） |

⚠️ **`working` を支えるのは、反応しない25の事象である。** `PreToolUse` と `PostToolUse` は
**体で表さないだけで、届いている**——**そのたびに idle の時計が戻る。**
⛔ **だから、長いビルドの間もロボットは眠らない。**

## 4つのチャンネル

| チャンネル | 音 | 既定 | 何を運ぶか |
|---|---|---|---|
| 画面 | 無音 | 常に | 顔。直視したときの情報 |
| LED ×12 | 無音 | 常に | 呼吸・暖色・注意・消灯。**周辺視で「生きている」** |
| 首（2軸） | サーボ音 | on | **遷移のときだけ** |
| スピーカー | 有音 | off | 遷移の4つに1語ずつ。✅ **2026-10-18 に着いた**——語は `hello` / `pip` / `chime` / `fall` |

⛔ **「無音モード」という名前は無い。** サーボは鳴る。
**音と運動は別の軸であり、1つの enum に畳まない。**

⚠️ **スピーカーには、もう1つ外からの軸がある**（2026-10-19）——**静かな時間**である。
21:00–05:00 は `quiet=True` として縁から来て、**`sound` の欄だけを閉じる**
（`quiet.py`）。⛔ **顔も光も首も従わない。** **静かであることは、居ないことではない。**

## 窓が2つ以上あっても、部屋は1つである（要求、2026-10-18）

⚠️ **VSCode の窓を2つ以上並べ、複数のセッションが同時に走ることがある。**
⇒ **首は1本であり、顔は1枚である。** 全部を写すことも、交互に振り向くこともできない。
✅ **だから注目は1つだけ持ち、外れにくくする**（`Focus`）——**自然に片方へ寄る。**
⛔ **もう片方の事象は捨てない。** 部屋が生きている証拠として数え、**何も表さない。**

## 数を持たない

⛔ **`GESTURES` は候補語であり、語彙の行ではない。**
**語彙の行は、その語がその機体で数になった日にしか書けない**（`references/README.md`）。
⇒ **この層が返す `gesture` は記号であり、`sent` は常に `False` である。**
**数の無い記号を送ったことにしない**——それが `no-intent` だった理由を、
この版は `sent=False` という1つの欄で言う。

⛔ **`sound` も同じである。** 語は音の名前であり、**周波数はこの層に無い**——
語から音への表はファームに在り、**この機体の耳で決まる**（身振りと同じ規則）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from projects.pet.expressions import State
from projects.stackchan import hooks


class Phase(Enum):
    """**ロボットがしていること。** Pet の5つの顔とは別の軸である。"""

    PRESENT = "present"
    GREETING = "greeting"
    WORKING = "working"
    BLOCKED = "blocked"
    CLOSING = "closing"
    RESTING = "resting"


class Light(Enum):
    """**12個の LED に渡す、意味だけの値。** ⛔ RGB の数はここに無い。

    ⚠️ **色への変換はファームウェアの仕事である**——機体2の LED の並びも、
    色の順も、このリポジトリのどの記録にも無い。
    """

    OFF = "off"
    DIM = "dim"
    BREATHE = "breathe"
    WARM = "warm"
    ALERT = "alert"
    ERROR = "error"


#: ⛔ **候補語である。** 語彙表の行ではない——**数になった日に、行が書かれる。**
GESTURES: tuple[str, ...] = ("look_up", "nod", "look_side", "rest", "recoil")

#: ✅ **2026-10-18 の語である。** 音の名前であり、周波数でも長さでもない。
#: ⚠️ **鳴る理由が1つずつ違う**——挨拶（`SessionStart`）・人を要る瞬間
#: （`PermissionRequest`）・終わり（`Stop`）・失敗（`StopFailure`）である。
#: ⛔ **`SessionEnd` は鳴らない。** 去る窓に声をかけても、聞く人がいない。
SOUNDS: tuple[str, ...] = ("hello", "pip", "chime", "fall")

#: ✅ **作者の決定、2026-10-18。** 運動は既定で入り、音は既定で出ない。
DEFAULT_MOTION = True
DEFAULT_SOUND = False

#: ⚠️ **製品の決定であり、測定値ではない。** 顔は3秒で戻る。
EXPRESSION_SECONDS = 3.0

#: ⚠️ **製品の決定であり、測定値ではない。** 90秒の無事象で休む。
IDLE_SECONDS = 90.0

#: ⚠️ **製品の決定であり、測定値ではない。** 20秒未満のターンは、締めのうなずきを省く。
LONG_TURN_SECONDS = 20.0

#: ⛔ **借り物である。** 10/04 の個体の `MOVE_SETTLE = 1.0` を下限として借りている。
#: **この個体では測られていない**——測った日に、この数を置き換える
#: （`docs/first-contact-stackchan.md`）。
MIN_BODY_INTERVAL = 1.0

#: ⚠️ **製品の決定であり、測定値ではない。** 同じターンで3回続いた失敗が、最初の合図である。
CONCERN_AFTER_FAILURES = 3

# ---------------------------------------------------------------------------
# 体の欄。⛔ 理由（reason）とは別の軸である。
# ---------------------------------------------------------------------------

BODY_GESTURE = "gesture"    # 記号を選んだ。⛔ まだ送っていない（数が無い）
BODY_NONE = "none"          # この事象は体を動かさない
BODY_STILL = "still"        # 運動チャンネルが切られている
BODY_COOLDOWN = "cooldown"  # 前の身振りから MIN_BODY_INTERVAL 未満である

BODY_VALUES: tuple[str, ...] = (BODY_GESTURE, BODY_NONE, BODY_STILL, BODY_COOLDOWN)

# ---------------------------------------------------------------------------
# 判定の理由。閉じた集合である。
# ---------------------------------------------------------------------------

ACTED = "acted"        # 段階が変わり、顔と光を当てた
OBSERVED = "observed"  # 証拠を読んだ。体では表さない
IGNORED = "ignored"    # 読まない。それでも生存の証拠である
CONCERN = "concern"    # 同じターンで3回目の失敗。光だけで示す
SETTLED = "settled"    # 表情が尽きて、在席へ戻った
SLEPT = "slept"        # 無事象が続いて、休息へ入った
DISTANT = "distant"    # 見ている側ではない。生きてはいるが、何も変えない

DECISION_REASONS: tuple[str, ...] = (
    ACTED, OBSERVED, IGNORED, CONCERN, SETTLED, SLEPT, DISTANT
)

#: ⚠️ **注目を奪う事象。** 2つである——**人の行為**（窓を開く・プロンプトを送る）と、
#: **機械が人を要する瞬間**（`PermissionRequest`）である。
#: ⛔ **`Stop` と `StopFailure` は含めない。** 機械が終わったことは、
#: 人がその窓を見ていることではない——**背後の窓が終わるたびに首を振れば、首は震える。**
STEALS = frozenset({"SessionStart", "UserPromptSubmit", "PermissionRequest"})

#: ⚠️ **待ちを終わらせる証拠。** `Notification` は含めない——
#: **注意の合図は、人が答えたことの証拠ではない。**
CLEARS_BLOCKED = frozenset({
    "PreToolUse",
    "PermissionDenied",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
})


@dataclass(frozen=True)
class Decision:
    """**1つの事象（または1つの刻み）に対する、1つの答え。**

    ⚠️ `face` が `None` なら顔は変わらない。`gesture` が `None` なら身振りは選ばれていない。
    ⚠️ `sound` は**語か `None`** である——`None` は「この判定は鳴らない」であり、
    **チャンネルが切られているときも `None`** になる（切れていることは語にならない）。
    ⛔ **`sent` は常に `False` である**——**機体2へ渡す数が1つも無いからである。**
    `body` は体の欄であり、`reason` は判定の理由である。**2つは別の軸である。**
    """

    event: str | None
    phase: Phase
    face: State | None
    light: Light
    gesture: str | None
    body: str
    sound: str | None
    sent: bool
    reason: str

    def as_row(self, at: float, session: str | None) -> dict:
        """**1行の写し。** ⚠️ **時計も窓も、値として受け取る。**

        ⛔ **写しを2つ書かない。** CLI の台本とデーモンのログは、
        同じ欄を同じ順で読めなければならない。
        """
        return {
            "at": at,
            "session": session,
            "event": self.event,
            "phase": self.phase.value,
            "face": self.face.value if self.face else None,
            "light": self.light.value,
            "gesture": self.gesture,
            "body": self.body,
            "sound": self.sound,
            "sent": self.sent,
            "reason": self.reason,
        }


@dataclass
class Companion:
    """**段階を1つ持ち、事象のたびに進める。**

    ⚠️ **`motion` と `sound` は独立である。** 顔と光はどちらにも従わない——
    **それらは無音だからである。**
    """

    motion: bool = DEFAULT_MOTION
    sound: bool = DEFAULT_SOUND
    _phase: Phase = field(default=Phase.PRESENT, init=False)
    _face: State | None = field(default=State.CURIOUS, init=False)
    _light: Light = field(default=Light.BREATHE, init=False)
    _hold_until: float = field(default=0.0, init=False)
    _idle_until: float | None = field(default=None, init=False)
    _last_body: float | None = field(default=None, init=False)
    _turn_started: float | None = field(default=None, init=False)
    _failures: int = field(default=0, init=False)
    _concerned: bool = field(default=False, init=False)
    _dropped: int = field(default=0, init=False)

    @property
    def dropped(self) -> int:
        """**捨てた身振りの数。** 並べなかったことの、数えられる証拠である。"""
        return self._dropped

    @property
    def deadline(self) -> float | None:
        """**次に目を覚ますべき時刻。** ⛔ **新しい数を発明しない。**

        表情の保持が先に尽きる段階ではその期限、在席と作業中では idle の期限を返す。
        ⛔ **`blocked` と `resting` は期限を持たない**——事象を待つだけである。
        """
        if self._phase in (Phase.GREETING, Phase.CLOSING):
            return self._hold_until
        if self._phase in (Phase.PRESENT, Phase.WORKING):
            return self._idle_until
        return None

    # -- 時計 ---------------------------------------------------------------

    def tick(self, at: float) -> Decision | None:
        """**事象の無い時刻を1つ進める。** 表情の失効と、休息への移行だけを見る。

        ⛔ **時計は読まない。** `at` は呼び出し側が渡す値である。
        ⚠️ **何も変わらなければ `None`**——**空の判定を返さない。**
        """
        reason = self._advance(at)
        if reason is None:
            return None
        return Decision(
            event=None,
            phase=self._phase,
            face=self._face,
            light=self._light,
            gesture=None,
            body=BODY_NONE,
            sound=None,
            sent=False,
            reason=reason,
        )

    def _advance(self, at: float) -> str | None:
        """**期限を過ぎた段階を進める。** 判定は返さず、理由だけを返す。"""
        if self._phase in (Phase.GREETING, Phase.CLOSING) and at >= self._hold_until:
            self._phase = Phase.PRESENT
            self._face = State.CURIOUS
            self._light = Light.BREATHE
            return SETTLED
        if (
            self._phase in (Phase.PRESENT, Phase.WORKING)
            and self._idle_until is not None
            and at >= self._idle_until
        ):
            self._phase = Phase.RESTING
            self._face = State.SLEEPY
            self._light = Light.OFF
            return SLEPT
        return None

    # -- 事象 ---------------------------------------------------------------

    def offer(self, event: str, at: float, quiet: bool = False) -> Decision:
        """**事象を1つ受け取り、判定を返す。** 時計は読まない。

        ⛔ **33のすべてが、まず生存の証拠である。** 段階が `resting` なら、
        **種類に関わらず起きる**——**無視される事象でも、セッションは生きている。**

        ⚠️ **`quiet` は音の欄だけを閉じる**（21:00–05:00、`quiet.py`）。
        **顔も光も首も従わない**——無音の時間であり、**存在しない時間ではない。**
        ⛔ **時刻そのものは持たない。** 時を読むのは縁であり、ここへは真偽で来る。
        """
        reaction = hooks.classify(event)
        self._advance(at)

        # ⛔ **すべての事象が idle の時計を戻す。** これが「長いビルドで眠らない」規則である。
        self._idle_until = at + IDLE_SECONDS

        if reaction.kind is hooks.Kind.TRANSITION:
            return self._transition(event, at, quiet)

        woke_face = None
        if self._phase is Phase.RESTING:
            self._wake()
            woke_face = self._face

        if reaction.kind is hooks.Kind.IGNORED:
            return self._decision(
                event, face=woke_face, light=self._light,
                gesture=None, body=BODY_NONE, sound=None, reason=IGNORED,
            )

        return self._evidence(event, at, woke_face)

    def witness(self, event: str, at: float) -> Decision:
        """**別の窓の事象を受け取る。** 生存の証拠として数え、**何も表さない。**

        ⚠️ **2つの VSCode は1つの部屋である。** 首は1本、顔は1枚であり、
        2つのエージェントを同時に映すことはできない（`Focus`）。
        だが**届いた事象は、部屋が生きている証拠である**——idle の時計は戻る。
        ⛔ **見ている側でないことは、見ていないことではない。**
        """
        hooks.classify(event)  # ⛔ **知らない名前は、ここでも断る。**
        self._advance(at)
        self._idle_until = at + IDLE_SECONDS
        return self._decision(
            event, face=None, light=self._light,
            gesture=None, body=BODY_NONE, sound=None, reason=DISTANT,
        )

    def _transition(self, event: str, at: float, quiet: bool) -> Decision:
        # ⚠️ **音は、この4つの遷移に1つずつ在る。** `UserPromptSubmit` は鳴らない——
        #    人はいま自分で喋った。`SessionEnd` も鳴らない——去る窓に声をかけない。
        # ⛔ **音は体の下限に従わない。** 別の軸である（「音と運動は別」）。
        sound: str | None = None

        if event == "SessionStart":
            self._phase = Phase.GREETING
            self._face = State.GREETING
            self._light = Light.WARM
            self._hold_until = at + EXPRESSION_SECONDS
            gesture, body = self._body("look_up", at)
            sound = "hello"

        elif event == "UserPromptSubmit":
            self._phase = Phase.WORKING
            self._face = State.CURIOUS
            self._light = Light.DIM
            self._turn_started = at
            self._failures = 0
            self._concerned = False
            gesture, body = self._body("look_up", at)

        elif event == "PermissionRequest":
            # ⛔ **唯一の割り込みである。** 体が間に合わなくても、光は必ず出る。
            self._phase = Phase.BLOCKED
            self._face = State.CURIOUS
            self._light = Light.ALERT
            gesture, body = self._body("look_side", at)
            sound = "pip"

        elif event == "Stop":
            long_turn = (
                self._turn_started is not None
                and at - self._turn_started >= LONG_TURN_SECONDS
            )
            self._phase = Phase.CLOSING
            self._face = State.HAPPY
            self._light = Light.WARM
            self._hold_until = at + EXPRESSION_SECONDS
            self._turn_started = None
            self._failures = 0
            self._concerned = False
            # ⚠️ **短いターンは、締めのうなずきを省く。** 返事に挨拶を重ねない。
            gesture, body = self._body("nod", at) if long_turn else (None, BODY_NONE)
            sound = "chime"

        elif event == "StopFailure":
            self._phase = Phase.CLOSING
            self._face = State.ANGRY
            self._light = Light.ERROR
            self._hold_until = at + EXPRESSION_SECONDS
            self._turn_started = None
            self._failures = 0
            self._concerned = False
            gesture, body = self._body("recoil", at)
            sound = "fall"

        else:  # SessionEnd
            self._phase = Phase.RESTING
            self._face = State.SLEEPY
            self._light = Light.OFF
            self._turn_started = None
            gesture, body = self._body("rest", at)

        return self._decision(
            event, face=self._face, light=self._light,
            gesture=gesture, body=body, sound=self._sound(sound, quiet), reason=ACTED,
        )

    def _evidence(self, event: str, at: float, woke_face: State | None) -> Decision:
        face = woke_face

        if event in CLEARS_BLOCKED and self._phase is Phase.BLOCKED:
            self._phase = (
                Phase.WORKING if self._turn_started is not None else Phase.PRESENT
            )
            self._face = State.CURIOUS
            self._light = Light.DIM if self._phase is Phase.WORKING else Light.BREATHE
            face = self._face

        if event == "PostToolUseFailure":
            self._failures += 1
            if self._failures >= CONCERN_AFTER_FAILURES and not self._concerned:
                self._concerned = True
                # ⛔ **怒らない。** 光だけが「引っかかっている」と言う。
                self._light = Light.ALERT
                return self._decision(
                    event, face=face, light=self._light,
                    gesture=None, body=BODY_NONE, sound=None, reason=CONCERN,
                )

        elif event == "PostToolUse":
            # ⚠️ **成功が連続を切る。** 失敗の数は、成功のときにだけ0へ戻る。
            self._failures = 0
            self._concerned = False
            if self._phase is Phase.WORKING:
                self._light = Light.DIM
            elif self._phase is Phase.PRESENT:
                self._light = Light.BREATHE

        return self._decision(
            event, face=face, light=self._light,
            gesture=None, body=BODY_NONE, sound=None, reason=OBSERVED,
        )

    # -- 部品 ---------------------------------------------------------------

    def _wake(self) -> None:
        if self._turn_started is not None:
            self._phase = Phase.WORKING
            self._light = Light.DIM
        else:
            self._phase = Phase.PRESENT
            self._light = Light.BREATHE
        self._face = State.CURIOUS

    def _body(self, name: str, at: float) -> tuple[str | None, str]:
        """**身振りを選ぶ。** ⛔ **選ぶだけで、送らない。**

        順序は、切られているか → 近すぎないか、である。
        ⚠️ **近すぎる場合は捨てる。並べない**——10/04 の個体では、約1秒より近い指令が
        サーボを止め、電源系を落とした（`MOVE_SETTLE`）。**並べれば、その間隔をこの層が決める。**
        """
        if not self.motion:
            return None, BODY_STILL
        if self._last_body is not None and at - self._last_body < MIN_BODY_INTERVAL:
            self._dropped += 1
            return None, BODY_COOLDOWN
        self._last_body = at
        return name, BODY_GESTURE

    def _sound(self, word: str | None, quiet: bool = False) -> str | None:
        """**音の欄を決める。** ⚠️ **切られていれば、語は選ばれない。**

        ⛔ **「切っている」を語にしない。** `None` は「鳴らない」であり、
        切られていることも、この事象が音を持たないことも、同じ1つの値で言える。
        2つを区別する必要が出た日に、欄が1つ増える——**いまは区別しない。**

        ⚠️ **静かな時間も同じ1つの値になる**（`quiet=True` → `None`）。
        ✅ **2026-10-19 に足した**——**夜を守る方法が「音を切る」しか無かった**ためである。
        ⛔ **それでも2つを区別しない。** 区別が要る日は、欄が1つ増える。
        """
        if not self.sound or quiet:
            return None
        return word

    def _decision(
        self,
        event: str,
        *,
        face: State | None,
        light: Light,
        gesture: str | None,
        body: str,
        sound: str | None,
        reason: str,
    ) -> Decision:
        return Decision(
            event=event,
            phase=self._phase,
            face=face,
            light=light,
            gesture=gesture,
            body=body,
            sound=sound,
            sent=False,
            reason=reason,
        )


#: ⚠️ **台本で窓の名前を書かないときの名前である。** 数ではない。
DEFAULT_SESSION = "main"


@dataclass
class Focus:
    """**1つの部屋に窓が2つ以上あるとき、首を1本に保つ層。**

    ⚠️ **「自然に片方へ寄る」がこの規則である**（作者の要求、2026-10-18）——
    **最初に事象を出した窓が注目を取り、持ち主は黙るまで持ち続ける。**
    持ち主が `IDLE_SECONDS` のあいだ黙れば注目は離れ、次に事象を出した窓が取る。
    ⛔ **窓のあいだで交互に振り向かない。** 交互なら身振りは毎回1秒の下限に当たり、
    **首は端末のあいだで震えることになる。** だから注目は**外れにくい**。
    ⚠️ **窓の数は2に限らない**——数えるのは持ち主が1人かどうかだけである。

    ✅ **注目は、人が動いた側へ移る**（`STEALS`）——**窓を開く・プロンプトを送る**のは
    人の行為であり、**`PermissionRequest` は機械が人を要している瞬間**である。
    ⛔ **背後の窓の `Stop` は奪わない。** 機械が終わったことは、人がそこを見ていることではない。

    注目の外の事象は `Companion.witness` へ行く——**部屋は起きたままで、何も表さない。**
    ⛔ **`sent` は、どちらの窓の行でも `False` である。**
    """

    companion: Companion = field(default_factory=Companion)
    _held: str | None = field(default=None, init=False)
    _quiet_until: float | None = field(default=None, init=False)

    @property
    def held(self) -> str | None:
        """**いま見ている窓の名前。** `None` なら、まだ誰も見ていない。"""
        return self._held

    @property
    def deadline(self) -> float | None:
        """**部屋として次に目を覚ますべき時刻。**

        ⚠️ **部屋の期限と、持ち主の沈黙の期限の早い方である。**
        ⛔ **同じ `IDLE_SECONDS` を使うが、時計は2つである**（`_quiet_until`）。
        """
        room = self.companion.deadline
        if self._held is not None and self._quiet_until is not None:
            return self._quiet_until if room is None else min(room, self._quiet_until)
        return room

    def tick(self, at: float) -> Decision | None:
        """**持ち主が黙りすぎていれば、注目を離してから時計を進める。**"""
        self._release_if_quiet(at)
        return self.companion.tick(at)

    def offer(self, session: str, event: str, at: float,
              quiet: bool = False) -> Decision:
        """**窓を名乗る事象を1つ受け取る。**

        ⚠️ **注目が誰にも無ければ、その事象を出した窓が取る**——起動直後でも、
        前の持ち主が黙った後でも同じである。**窓の数は2に限らない。**

        ⚠️ **`quiet` は、持ち主の事象にだけ渡る。** 背後の窓は元より鳴らない。
        """
        self._release_if_quiet(at)

        if self._held is None or session == self._held:
            self._held = session
            self._quiet_until = at + IDLE_SECONDS
            decision = self.companion.offer(event, at, quiet=quiet)
            # ⚠️ **`SessionEnd` は、持ち主を空ける。** 去った窓を見続けない。
            if decision.phase is Phase.RESTING:
                self._held = None
                self._quiet_until = None
            return decision

        if event in STEALS:
            self._held = session
            self._quiet_until = at + IDLE_SECONDS
            return self.companion.offer(event, at, quiet=quiet)

        return self.companion.witness(event, at)

    def _release_if_quiet(self, at: float) -> None:
        """**持ち主の無事象は、部屋の無事象とは別の時計である。**

        ⛔ **同じ `IDLE_SECONDS` を使うが、数は1つである。** 部屋が他の窓で
        起きているあいだも、**見ている窓が黙れば注目は離れる。**
        """
        if self._held is not None and self._quiet_until is not None:
            if at >= self._quiet_until:
                self._held = None
                self._quiet_until = None


__all__ = [
    "Phase",
    "Light",
    "GESTURES",
    "SOUNDS",
    "DEFAULT_MOTION",
    "DEFAULT_SOUND",
    "EXPRESSION_SECONDS",
    "IDLE_SECONDS",
    "LONG_TURN_SECONDS",
    "MIN_BODY_INTERVAL",
    "CONCERN_AFTER_FAILURES",
    "BODY_GESTURE",
    "BODY_NONE",
    "BODY_STILL",
    "BODY_COOLDOWN",
    "BODY_VALUES",
    "ACTED",
    "OBSERVED",
    "IGNORED",
    "CONCERN",
    "SETTLED",
    "SLEPT",
    "DISTANT",
    "DECISION_REASONS",
    "CLEARS_BLOCKED",
    "STEALS",
    "Decision",
    "Companion",
    "DEFAULT_SESSION",
    "Focus",
]
