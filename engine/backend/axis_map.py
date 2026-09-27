# -*- coding: utf-8 -*-
"""軸の対応——⛔ **このリポジトリは、これを決めない。**

[02_調査/01] の実測:
- **§3.1** 「左＝Motor 1」で2票、「右＝Motor 1」で1票——**割れている**
- **§3.2** ベンダーは `pitch`/`roll`/`yaw` を**軸の意味としては**書くが、**モーター番号には結びつけない**
- **§3.3** ソフト側の割り当ては、どこも「利用者が決める」——**正準の対応は存在しない**
- **§3.4** 唯一「固定した対応」を主張するのは第三者の小プロジェクトで、**符号は配線依存である**
- **§5.1** 角度と刻み（0–1024）の対応は**書かれていない。そしてそれは原理的に書けない**

⛔ **⇒ ゆえに、このモジュールには既定値が1つも無い。**

⚠️ **`AxisMap()` を引数なしで作れないようにしてあるのは、意図である。**
**空欄は中立ではない**（`CLAUDE.md` の文書規則）——**既定値を置けば、誰かがそれを配線の事実として使う。**
**そしてこの値は、実機の上でしか測れない。**

⚠️ **そして `scale` と `offset` は「校正」である。** 角度から計算する式は無い
（§5.1「原理的に書けない」）——**ゆえに、ここに入る数はすべて、誰かが測った数である。**
**このリポジトリは、その数を1つも持っていない。**
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = ["ChannelCalibration", "AxisMap", "AxisMapError"]


class AxisMapError(ValueError):
    """対応が無い、または壊れている。**黙って既定値を使わない。**"""


@dataclass(frozen=True)
class ChannelCalibration:
    """1つの自由度を、1つのモーターに結びつける。**数はすべて実測である。**

    - `sign` は **+1 か −1 だけ**。⚠️ **配線依存である**（§3.4）
    - `offset` は**その自由度のゼロが、何カウントなのか**
    - `scale` は**その自由度の1単位が、何カウントなのか**——
      ⛔ **角度からは計算できない**（§5.1）。**測るしかない**
    """

    motor: int
    sign: int
    offset: float
    scale: float

    def __post_init__(self) -> None:
        if self.sign not in (-1, 1):
            raise AxisMapError(f"符号は +1 か −1 だけ: {self.sign}")
        if self.scale == 0:
            raise AxisMapError("`scale` が 0——**動かない自由度は、対応を持たない**")
        if self.motor < 0:
            raise AxisMapError(f"モーターが負: {self.motor}")

    def to_counts(self, value: float) -> float:
        """自由度の値 → カウント。⚠️ **丸めない**——丸めるのは門の手前である。"""
        return self.offset + self.sign * self.scale * value


@dataclass(frozen=True)
class AxisMap:
    """⛔ **引数なしで作れない。** 既定の対応は存在しない（モジュールを見よ）。"""

    channels: Mapping[str, ChannelCalibration]

    def __post_init__(self) -> None:
        if not self.channels:
            raise AxisMapError(
                "対応が空である——⛔ **正準の対応は存在しない**（[02_調査/01] §3.3）。"
                "**実機の上で測った数を、呼ぶ側が渡す**"
            )
        motors = [c.motor for c in self.channels.values()]
        if len(set(motors)) != len(motors):
            raise AxisMapError(
                f"2つの自由度が同じモーターを指している: {sorted(motors)}"
                "——⛔ **同じモーターへ2つ送ると、後が勝つ**"
            )

    def to_counts(self, dof: str, value: float) -> float:
        try:
            return self.channels[dof].to_counts(value)
        except KeyError as exc:
            raise AxisMapError(
                f"自由度 {dof!r} の対応が無い（在るのは {sorted(self.channels)}）"
                "——⚠️ **`pitch`/`roll`/`yaw` という名前は、このリポジトリの名札である。**"
                "**機体の軸ではない**（`plan.py` を見よ）"
            ) from exc
