# -*- coding: utf-8 -*-
"""演技——**顔と身体を、1つの時計から出す。**

⛔ **ここが、この器で最初に「意図が運動になる」場所である。**
[06] §11-8 の逐語は **「顔と身体は必ず同時に一つの時計から出す」**——
そして `projects/pet/README.md` が記録しているとおり、**5つの顔のうち2つは同じ絵である**
（`happy` と `greeting`、実測 2026-09-28）。
⇒ **その2つを見分けているのは運動だけである。****ゆえにこのファイルは、
「運動が意味を運ぶ」ことを、この機体の上で初めて実演する。**

⚠️ **このファイルは `engine/` の外に在る**（決定 C、2026-09-28）。
ゆえに `engine/` の純度検査は、**このファイルを1行も見ていない**——
だから自前の検査を持つ（`tests/test_pet_purity.py`）。
**そしてこのファイルは `time` を import しない**——**時計は `__main__.py` が持ち、ここへ渡る。**

## 段

    Pet Expression（顔＋語）  →  Motion Intent（型）  →  軌道  →  門  →  フレーム
                                                        ↘ 同じ時計が顔も駆動する

⛔ **`Pet Expression` から `Motion Intent` への段は、このファイルの中に無い。**
**それはセッションの Claude が行う**（D-03、2026-09-27）——
**そして変換が何を根拠にしたかは、`references/` に1行だけ書いてある。**

⚠️ **このファイルは LLM を呼ばない。** ゆえに決定 C の代価——
`CLAUDE.md` の「このリポジトリのコードは LLM を呼ばない」に但し書きが要ること——は、
**このコミットではまだ払われていない。** **但し書きは、呼ぶ最初のファイルと同じコミットで入る。**
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from engine.backend.axis_map import AxisMap
from engine.backend.cycle import Clock, Schedule, Tick, run
from engine.backend.gate import Gate
from engine.backend.mock import MockBox, Step
from engine.backend.protocol import Frame
from engine.backend.transmit import FrameSet, Transmitter
from engine.intent import Intent, load
from engine.trajectory import Admission, ChannelLimits, Envelope, Rejection, admit

from .expressions import State
from .screen import Screen

__all__ = [
    "EXPRESSIONS", "MOTIONS", "Expression", "MakeError", "Rig", "Take",
    "demo_rig", "load_expression", "perform",
]

#: ⛔ **書かれた意図の置き場。** `motions/<名>.json` が `Motion Intent` である。
MOTIONS = Path(__file__).resolve().parent / "motions"

#: ⛔ **語は、`Motion Intent` の型の中に無い。** `additionalProperties: false` だからである。
#: ⇒ **ゆえにここに置く。** **型の外に在ることが、この段の正体である**——
#: **`Motion Intent` は既にカウントであり、「なぜその数なのか」を自分では言えない。**
#: ⚠️ **語は概念文書 §5 の逐語である。** 括弧の中は、この1行がどの決定を通ったかを示す。
#: ⛔ **この表は語彙ではない**（`references/` を見よ）。**1つの表情の来歴である。**
EXPRESSIONS: dict[str, tuple[State, tuple[str, ...]]] = {
    "greeting": (State.GREETING, ("small forward tilt", "return")),
}


class MakeError(ValueError):
    """演技が組めない。**黙って既定値で埋めない。**"""


@dataclass(frozen=True)
class Expression:
    """**顔と、運動と、その運動がどの語から来たか。**

    ⛔ **素材2本が空けた段の中身である**（初稿 Q-2）。
    ⚠️ **`words` は飾りではない。** `Intent` は既にカウントであり、
    「なぜ +40 なのか」を `Intent` 自身は言えない——
    **語との対応がどこにも書かれていなければ、変換は書いた者の頭の中だけに在る。**
    """

    state: State
    words: tuple[str, ...]
    intent: Intent


@dataclass(frozen=True)
class Rig:
    """⛔ **実機の上でしか測れない数。** ⚠️ **既定値は、`envelope` の1つだけである。**

    | 欄 | 単位 | 誰が測るか |
    |---|---|---|
    | `axis_map` | —— | 配線。⛔ **正準は無い**（[02_調査/01] §3.3） |
    | `starts_by_dof` | カウント | フィードバック、または利用者。⛔ **知らずに最初の1フレームを出すのが、いちばん危ない段差である** |
    | `limits_by_dof` | **自由度の単位**／秒 | 配線と機構。**`admit` が読む** |
    | `limits_by_motor` | **カウント**／秒 | 同じ配線を、カウントで測ったもの。**門が読む** |
    | `envelope` | カウント | ⚠️ **これだけは既定値が実測である**（190〜833、`Clip Input`） |
    | `period` | 秒 | ⛔ **既定値は無い**（[02_調査/08] §8 の6番） |

    ⛔ **`limits_by_dof` と `limits_by_motor` は、同じ型だが同じ数ではない。**
    **`axis_map` の `scale` が 1 でなければ、片方は `scale` のぶんだけずれる。**
    ⚠️ **2つの欄が別々に在る理由は、それである**——**`ChannelLimits` という名前は、
    単位を言っていない。** **同じ数を両方へ渡すと、静かにずれる。**
    """

    axis_map: AxisMap
    starts_by_dof: Mapping[str, float]
    limits_by_dof: Mapping[str, ChannelLimits]
    limits_by_motor: tuple[ChannelLimits, ...]
    period: float
    envelope: Envelope = field(default_factory=Envelope)

    def motors(self) -> int:
        """⚠️ **モーターの数。** 対応が届いている範囲である。"""
        return max(c.motor for c in self.axis_map.channels.values()) + 1

    def starts_by_motor(self) -> tuple[float, ...]:
        """**開始位置を、モーターの番号で並べ直す。**

        ⛔ **届いていないモーターが1つでもあれば、組まない。**
        **0.0 で埋めるのは、知らない位置を「0 に居る」と主張することである**——
        そして門は、その数を使って最初の段差を測る。
        """
        n = self.motors()
        out: list[float | None] = [None] * n
        for dof, cal in self.axis_map.channels.items():
            if dof not in self.starts_by_dof:
                raise MakeError(
                    f"自由度 {dof!r} の現在位置が渡されていない——"
                    "⛔ **門は、最初の1フレームの段差をこの数で測る**"
                )
            out[cal.motor] = self.axis_map.to_counts(dof, self.starts_by_dof[dof])
        missing = [i for i, v in enumerate(out) if v is None]
        if missing:
            raise MakeError(
                f"モーター {missing} の現在位置が無い——"
                "⛔ **対応の無いモーターを 0.0 で埋めない。** "
                "**それは「0 に居る」という主張であり、門がそれを信じる**"
            )
        if len(self.limits_by_motor) != n:
            raise MakeError(
                f"モーターが {n} 個、上限が {len(self.limits_by_motor)} 個"
                "——⛔ **門はモーターごとに1つ要る**"
            )
        return tuple(float(v) for v in out)


@dataclass(frozen=True)
class Take:
    """**1回の演技の記録。** ⛔ **「そう見えた」ではない。何が送られたかである。**

    ⚠️ **記録が在る理由**（[07] の逐語）——**目標は、この工房では検証できない。
    残るのは記録だけである。** この型が持つのは**機構の側**である：
    どの刻みが遅れ、どのフレームが門を通り、箱が何を記録したか。
    ⛔ **「生きている感じ」は、この型の中に1つも入っていない。**

    ⚠️ **`steps` は「違反した段差」ではない。** `MockBox` が記録するのは
    **位置が動いた回**であり、**それが届く速さを超えているかは箱には分からない**
    （`engine/backend/mock.py` の `Step` を見よ）。**段差の判断は門の仕事である。**
    """

    expression: Expression
    admission: Admission | Rejection
    ticks: tuple[Tick, ...]
    sets: tuple[FrameSet, ...]
    steps: tuple[Step, ...]
    arrived: tuple[float, ...]
    #: ⚠️ **顔を描いた時刻。** **運動を送ったのと同じ刻みの時刻である**（`ticks[0].started`）。
    #: ⛔ **画面が無ければ `None`。** **そして、これを記録するために在る**——
    #: **「1つの時計から出た」を、主張ではなく検査にするためである。**
    drawn_at: float | None = None

    @property
    def ran(self) -> bool:
        """⚠️ **計画時の門を通ったか。** **門（実行時）を通ったか、ではない。**"""
        return isinstance(self.admission, Admission)

    @property
    def refusal(self) -> Rejection | None:
        return self.admission if isinstance(self.admission, Rejection) else None

    @property
    def sent(self) -> tuple[Frame, ...]:
        """⚠️ **実際に送ったもの。** 門が保った軸も、ここには入っている。"""
        return tuple(f for fs in self.sets for f in fs.verdict.frames)

    @property
    def refusals(self) -> int:
        """⛔ **門が「提案どおりには通さなかった」回数である。**
        **「機体が止まった回数」ではない**——弾かれた軸も、届く速さでなら寄る。
        """
        return sum(1 for fs in self.sets if fs.verdict.held)

    @property
    def worst_lateness(self) -> float:
        """⚠️ **いちばん遅れた刻み。** 1つも走らなければ 0.0 である。"""
        return max((t.lateness for t in self.ticks), default=0.0)

    @property
    def skipped(self) -> int:
        """⛔ **1周期を超えて遅れ、諦めた回。** **追いつかないときは、追いつかない方が正しい。**"""
        return self.ticks[-1].missed_before if self.ticks else 0


def load_expression(name: str) -> Expression:
    """`motions/<name>.json` を読み、`EXPRESSIONS` の語と組にする。

    ⛔ **語はファイルの中に無い**（型が閉じているからである）。**ゆえに別に要る。**
    """
    if name not in EXPRESSIONS:
        raise MakeError(
            f"表情 {name!r} を知らない（在るのは {sorted(EXPRESSIONS)}）——"
            "⚠️ **語は `Motion Intent` の型の外に在る**（`EXPRESSIONS` を見よ）"
        )
    path = MOTIONS / f"{name}.json"
    if not path.exists():
        raise MakeError(f"意図が無い: {path}")
    import json  # ⚠️ **ここで import する。** 読むのはこの関数だけである

    state, words = EXPRESSIONS[name]
    return Expression(state=state, words=words, intent=load(json.loads(path.read_text("utf-8"))))


def perform(expression: Expression, rig: Rig, *, clock: Clock,
            screen: Screen | None = None, box: MockBox | None = None) -> Take:
    """**1つの表情を、1つの時計で走らせる。**

    ⛔ **計画時に弾かれたら、1フレームも送らない。** 弾くのは `admit` の仕事であって、
    **門の仕事ではない**——ゆえにそのときの `Take.sets` は空である。

    ⚠️ **顔は、最初の刻みの中で1回だけ描く。** **運動を送るのと同じ刻みから出る**——
    **ゆえに `Take.drawn_at` は `ticks[0].started` と一致する。**
    ⛔ **ループの外で描かない。** 外で描けば、「1つの時計から出た」は主張ではなくなる
    ——**2つの時計が、たまたま同時に近い時刻を持っていただけである。**
    ⚠️ **この版の演技は、途中で表情を変えない**——**着替えながら動く演技は、まだ無い。**

    ⚠️ **`box` と `screen` は、どちらも省略できる。** 送らずに走らせれば、
    **運動だけを数えられる**——**Mock はプロトコルの試験であって、安全の主張ではない。**
    """
    admission = admit(expression.intent, rig.starts_by_dof, rig.limits_by_dof, rig.envelope)
    if isinstance(admission, Rejection):
        return Take(expression=expression, admission=admission, ticks=(), sets=(),
                    steps=(), arrived=())

    starts_by_motor = rig.starts_by_motor()
    gate = Gate(starts_by_motor=starts_by_motor,
                limits_by_motor=rig.limits_by_motor,
                envelope=rig.envelope)

    trajectories = admission.trajectories
    transmitters = tuple(
        Transmitter(trajectory=t, axis_map=rig.axis_map, gate=gate) for t in trajectories
    )
    durations = tuple(t.duration for t in trajectories)
    total = sum(durations)

    schedule = Schedule(period=rig.period)
    start = clock.now()
    # ⚠️ **組の始まりの時刻である。** 組は順に走るので、`n` 組目は `group_starts[n]` 秒から始まる。
    #
    # ⛔ **この列が在る理由。** **この版の最初は、`offset` を積み上げながら組を選び、
    # 終わった組を `len(durations) - 1` へ *戻して* いた**——**が、`offset` を戻していなかった。**
    # ⇒ **演技が終わった後の刻みが、最後の組の `0` 秒目を送っていた**——
    # **最後の目標（512）ではなく、最後の組の*最初の*標本（552）である。**
    # ⛔ **そして、それは段差である**: 機体は 512 へ向かって走っている途中で、
    # **いきなり 552 を commanded される。**
    # ⚠️ **この誤りは `admit` の欠陥に隠れていた**（実測 2026-09-28）——
    # **当時は2組目が「512 からの平らな線」だったので、その最初の標本も 512 だった。**
    # **⇒ 到着の検査は、2つの誤りが打ち消し合って緑だった。**
    group_starts: list[float] = []
    at = 0.0
    for duration in durations:
        group_starts.append(at)
        at += duration

    sets: list[FrameSet] = []
    drawn: list[float] = []

    def body(tick: Tick) -> None:
        now = clock.now()
        if screen is not None and not drawn:
            # ⚠️ **最初の刻みの中で描く。** ループの外で描けば、
            # **「1つの時計から出た」は検査できなくなる。**
            screen.draw(expression.state)
            drawn.append(now)
        elapsed = now - start
        # ⚠️ **どの組か。** 組は順に走る。**境目を跨いだ刻みは、次の組の 0 秒目である。**
        group = 0
        while group + 1 < len(durations) and elapsed >= group_starts[group + 1]:
            group += 1
        # ⛔ **終わった後も、最後の組を回し続ける。** **それは停止ではない**——
        # 最後の目標を保つことである。**プロトコルに停止コマンドは無い。**
        # ⚠️ **`now` が終わりを越えれば、`frames_at` の中の `clamped` が
        # 最後の標本を選ぶ**——**ゆえに保たれるのは、最後の目標である。**
        fs = transmitters[group].frames_at(start + group_starts[group], now)
        sets.append(fs)
        if box is not None:
            box.feed(b"".join(f.raw for f in fs.verdict.frames), now)

    # ⚠️ **端を跨ぐ刻みを1つ残す。** `+2` は、最後の目標が必ず1度送られるための余裕である。
    ticks = run(schedule, clock, body, math.ceil(total / rig.period) + 2)

    return Take(expression=expression, admission=admission, ticks=ticks,
                sets=tuple(sets),
                steps=tuple(box.steps) if box is not None else (),
                arrived=tuple(box.positions) if box is not None else (),
                drawn_at=drawn[0] if drawn else None)


def demo_rig() -> Rig:
    """⚠️ **このデモのための数である。⛔ 1つも測っていない。**

    | 欄 | この値 | 出どころ |
    |---|---|---|
    | `axis_map` | `pitch` → モーター0、符号 +1、オフセット 0.0、`scale` **1.0** | ⛔ **測定ではない。** ⚠️ **`scale` が 1.0 なのは、意図の `target` が既にカウントで書かれているからである**（型の定義）。**実機の符号と倍率は、これとは違う** |
    | `starts_by_dof` | `pitch` = **512.0** カウント | ⛔ **測定ではない。** ホストが送れる帯 190〜833 の真ん中に近い、というだけである。**「512 が中立」と明記した一次情報は見つかっていない**（[01] §3） |
    | `limits_by_dof` | **すべて `None`** | ⛔ **「制限しない」である。** 下を見よ |
    | `limits_by_motor` | **すべて `None`** | ⛔ **同上** |
    | `envelope` | 190〜833（既定） | ✅ **これだけは実測である**（`Clip Input`、[02_調査/01] §2.2） |
    | `period` | **20 ms** | ⛔ **測定ではない。** ⚠️ **実機の周期は、ループの実測から決まる**（[02_調査/08]） |

    ⛔ **`None` の意味を、隠さない。** **`ChannelLimits()` は「制限しない」であり、
    この走行では次の検査が鳴らない:**

    - `admit` の **3（可到達性）**——台形の族を見る検査であり、既定の `min-jerk` では元から走らない
    - `admit` の **4 のうち、軸ごとの上限**（**合成の検査は走る**——`envelope` を読むためである）
    - **門の段差の検査**（`velocity × elapsed`）

    ⇒ **この演技で実際に鳴っているのは、枠の検査だけである。**
    **枠（190〜833）は実測なので、そこだけは本物である。**
    ⚠️ **この数を「安全」と読まないこと**——**測定していない上限を書けば、
    書いた数が実測として読まれる。** **測るのは実機の上である。**

    ⛔ **そして `scale` が 1.0 である以上、`limits_by_dof` と `limits_by_motor` の単位は
    たまたま一致する。** **実機では一致しない。**
    """
    from engine.backend.axis_map import ChannelCalibration  # ⚠️ 対応の型は、ここでしか使わない

    return Rig(
        axis_map=AxisMap(channels={
            "pitch": ChannelCalibration(motor=0, sign=1, offset=0.0, scale=1.0),
        }),
        starts_by_dof={"pitch": 512.0},
        limits_by_dof={"pitch": ChannelLimits()},
        limits_by_motor=(ChannelLimits(),),
        period=0.02,
    )
