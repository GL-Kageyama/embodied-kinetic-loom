# -*- coding: utf-8 -*-
"""軌道——**同じ入力なら、同じビット列が出る。**

⚠️ **ここが「決定論的」の意味である。** 乱数も、時刻も、環境変数も読まない。
標本の時刻は等間隔に**数え上げて**作る（`duration * k / (count-1)`）。
⚠️ **`numpy` を使わない**——`linspace` は親切だが、親切の分だけ規則が外から来る。

⛔ **自由度とモーターの対応を、この型は持たない。**
[02_調査/01] §3.3 が
「軸対応の正準は無く、符号は配線依存」と書いている。**だから `labels` は名札であって、配線ではない。**
実際にどのモーターへ送るかは、バックエンドが設定として持つ（`admit` の docstring を見よ）。
"""
from __future__ import annotations

from dataclasses import dataclass

from .profile import profile_of

__all__ = ["Sample", "Trajectory", "plan"]

DEFAULT_SAMPLES = 257  # ⚠️ **固定である。** 「何点で測るか」を入力から決めると、入力が増える。


def _scale(value: float, distance: float, denominator: float) -> float:
    """正規化した値を、このチャネルの実値へ移す。

    ⛔ **動かないチャネルを、ここで止める。** 台形のジャークは `inf` なので、
    `0.0 * inf` は **`nan`** になる——そして **`nan > limit` は `False` である**。
    **動かない軸が、制限の検査を静かに通り抜ける。**（`CLAUDE.md`「空の検査は OK と言う」）
    """
    if distance == 0.0:
        return 0.0
    return distance * value / denominator


@dataclass(frozen=True)
class Sample:
    """1時点の、全チャネルの値。**位置・速度・加速度・ジャークを並べて持つ。**"""

    t: float
    position: tuple[float, ...]
    velocity: tuple[float, ...]
    acceleration: tuple[float, ...]
    jerk: tuple[float, ...]


@dataclass(frozen=True)
class Trajectory:
    """1つの動作（同時に動くチャネルの組）の、標本列。

    ⚠️ **`labels` は名札である**（配線の対応ではない）。**並びの意味は呼ぶ側が決める。**
    """

    duration: float
    starts: tuple[float, ...]
    ends: tuple[float, ...]
    profile: object
    labels: tuple[str, ...]
    samples: tuple[Sample, ...]

    @property
    def channel_count(self) -> int:
        return len(self.starts)

    def at(self, t: float) -> Sample:
        """時刻 `t` の標本を返す。**補間しない**——標本の外なら `ValueError`。

        ⛔ **補間しないのは意図である。** 標本の間に値をこしらえるのは、
        **機械へ送る点を作るという設計**であって、ここで黙ってやることではない。
        """
        if not 0.0 <= t <= self.duration:
            raise ValueError(f"t は [0, {self.duration}] である: {t!r}")
        step = self.duration / (len(self.samples) - 1)
        k = round(t / step)
        sample = self.samples[k]
        if abs(sample.t - t) > step * 1e-9:
            raise ValueError(f"{t!r} は標本点でない（刻みは {step!r}）")
        return sample


def plan(starts, ends, duration: float, profile="min-jerk", labels=None,
         count: int = DEFAULT_SAMPLES) -> Trajectory:
    """`starts` から `ends` へ、`duration` 秒で動く軌道を組む。

    ⛔ **端は厳密に置く。** `u = 0` の標本は `start` そのもの、最後の標本は `end` そのものである——
    **丸め誤差で目標に届かない、という失敗を作らない。**
    （`start + (end - start)` は、浮動小数では `end` に一致しないことがある。）

    ⚠️ **プロファイルは族である。** `"min-jerk"` は追加の数を要さず、`"trapezoid"` は要る
    （`profile.Trapezoid` を渡す）。**その違いは `profile.py` に書いてある。**
    """
    if isinstance(profile, str):
        profile = profile_of(profile)
    starts = tuple(float(v) for v in starts)
    ends = tuple(float(v) for v in ends)
    if len(starts) != len(ends):
        raise ValueError("starts と ends の長さが違う")
    if not starts:
        raise ValueError("チャネルが1つも無い")
    if duration <= 0.0:
        raise ValueError(f"duration は正である: {duration!r}")
    if count < 2:
        raise ValueError(f"count は 2 以上である: {count!r}")
    if labels is None:
        labels = tuple(f"ch{i}" for i in range(len(starts)))
    labels = tuple(labels)
    if len(labels) != len(starts):
        raise ValueError("labels の数がチャネル数と違う")

    deltas = tuple(e - s for s, e in zip(starts, ends))
    samples = []
    for k in range(count):
        t = duration * k / (count - 1)
        u = k / (count - 1)
        shape = profile.shape(u)
        if k == 0:
            position = starts
        elif k == count - 1:
            position = ends
        else:
            position = tuple(s + d * shape.position for s, d in zip(starts, deltas))
        samples.append(Sample(
            t=t,
            position=position,
            velocity=tuple(_scale(shape.velocity, d, duration) for d in deltas),
            acceleration=tuple(_scale(shape.acceleration, d, duration * duration)
                               for d in deltas),
            jerk=tuple(_scale(shape.jerk, d, duration ** 3) for d in deltas),
        ))

    return Trajectory(
        duration=duration,
        starts=starts,
        ends=ends,
        profile=profile,
        labels=labels,
        samples=tuple(samples),
    )
