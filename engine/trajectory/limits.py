# -*- coding: utf-8 -*-
"""制限と、その非超過——**軸ごとに見て、終わりにしない。**

⛔ **[02_調査/02] §4.2 の結論はこれである**——
**「各軸をクランプすれば安全」は成り立たない。**
*pitch と roll を同時に振ると、合成は各軸の制限内でも大きくなりうる*（逐語）。

    軸ごと     |q̇_i| ≤ q̇_max,i            それぞれ独立に見る
    合成       √Σ (q̇_i / q̇_max,i)² ≤ 1     ⚠️ **半径が各軸の上限である楕円体**

⚠️ **「錐」とは書かない。** 同 §4.1 の**見出しは**「箱ではなく錐である」だが、
**同じ節の本文が「初稿は『錐（cone）』という語をロボティクスの文献では確認できなかった」と書いている。**
⇒ **見出しを引かない。** 確認できた形は3つである——**超矩形（箱）／楕円体／多面体**（逐語）。

⚠️ **合成の形は、ここで発明していない。** ASTM F2291 が**2軸の**合成加速度を
*"a curve defined in each quadrant by an ellipse, centered at (0,0), with major and minor radii
equal to the allowable 200 ms G limits"* と定義している（同 §4.1 が引く検索結果）。
**半径が各軸の上限である楕円**——それを**3軸へ、そして速度とジャークへ広げたものが上式である**。
⚠️ **その拡張は私のものである**（同 §4.1 は規格本文を読んでいない、と明記している）。

⛔ **同 §4.2 の「200 ms 以内に連続した事象が起きたらピークを50%減らす」は採らない。**
**緩める方向の規則を、根拠なしに持ち込まない。** ⚠️ **そして「持続した事象（sustained event）」という
概念が、この実装にはまだ無い**——無い概念に対する割り引きは、定義できない。

⛔ **そして、ここに既定の制限値は1つも無い。** 上限はすべて `ChannelLimits` として外から来る。
[02_調査/02] §1.4 の **1.2 m/s³ は ISO 8100-34 への帰属が支持されていない**（同 §8）ので、
**ジャークの既定値として置かない。** `None` は「その量を制限しない」である。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["ChannelLimits", "Envelope", "Violation", "check_targets", "check_trajectory"]

_DERIVATIVES = ("velocity", "acceleration", "jerk")


@dataclass(frozen=True)
class ChannelLimits:
    """1チャネル（1モーター）の上限。⚠️ **`None` は「制限しない」である。**"""

    velocity: float | None = None
    acceleration: float | None = None
    jerk: float | None = None


@dataclass(frozen=True)
class Envelope:
    """機体全体の枠。

    ⚠️ **`target_min` / `target_max` は、既定で 190 / 833 である**——
    [02_調査/01] §2.2 の `Clip Input` の実測値。
    ⛔ **これは「機械の限界」ではなく「ホストが既定で送れる範囲」である。**
    箱のリミットはフィードバック駆動で、プロトコルから読み出せる定数ではない。
    ⇒ **`None` を明示すれば枠は外れる。** **外すのは著者の判断である。**
    """

    target_min: float | None = 190.0
    target_max: float | None = 833.0
    composite: bool = True


@dataclass(frozen=True)
class Violation:
    """1つの違反。**時刻つきで返す**——「どこで超えたか」が言えない検査は、直せない。"""

    kind: str  # velocity / acceleration / jerk / target / composite-<量>
    channel: int | None  # ⚠️ **合成の違反はチャネルを持たない**（`None`）
    t: float
    value: float
    limit: float


def check_targets(ends, envelope: Envelope) -> tuple[Violation, ...]:
    """行き先が枠の内側か。⚠️ **これは「送る前」に見る唯一の検査である。**"""
    out = []
    for i, end in enumerate(ends):
        if envelope.target_min is not None and end < envelope.target_min:
            out.append(Violation("target", i, 0.0, end, envelope.target_min))
        if envelope.target_max is not None and end > envelope.target_max:
            out.append(Violation("target", i, 0.0, end, envelope.target_max))
    return tuple(out)


def check_trajectory(trajectory, channel_limits, envelope: Envelope) -> tuple[Violation, ...]:
    """標本ごとに、軸ごとの上限と合成の上限を見る。

    ⚠️ **`channel_limits` の並びは、軌道のチャネルの並びと同じでなければならない。**
    どちらの並びも**配線の事実**であり、このリポジトリは決めない（`plan.py` を見よ）。
    """
    limits = tuple(channel_limits)
    n = trajectory.channel_count
    if len(limits) != n:
        raise ValueError(f"制限が{len(limits)}個、チャネルが{n}個である")
    for i, lim in enumerate(limits):
        if lim is None:
            raise ValueError(f"チャネル{i}の上限が無い——`None` を使うなら ChannelLimits() を渡す")

    out = []
    for sample in trajectory.samples:
        for kind in _DERIVATIVES:
            values = getattr(sample, kind)
            ratios = []
            for i, v in enumerate(values):
                limit = getattr(limits[i], kind)
                if limit is None:
                    continue
                if math.isnan(v):
                    # ⛔ **`nan` を通さない。**「比較が偽だから通った」を作らない。
                    out.append(Violation(kind, i, sample.t, v, limit))
                    continue
                ratios.append((i, abs(v) / limit))
                if abs(v) > limit:
                    out.append(Violation(kind, i, sample.t, v, limit))
            if envelope.composite and len(ratios) >= 2:
                total = math.sqrt(sum(r * r for _, r in ratios))
                if total > 1.0:
                    out.append(Violation(f"composite-{kind}", None, sample.t, total, 1.0))
    return tuple(out)
