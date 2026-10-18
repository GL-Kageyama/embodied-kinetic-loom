# -*- coding: utf-8 -*-
"""首の動き——**機体2へ送る姿勢の列を、エンジンの軌道から作る。**

⛔ **ここは機体の数を1つも持たない。** 始点も終点も、度の10倍の整数として外から来る。
**ゼロ点も、封筒も、床も、このファイルには無い**——それらは基板の側に在り、
姿勢の行はそれを運ばない（`engine/backend/protocol_stackchan_pose.py` の但し書きと同じ規則）。

⛔ **時計も読まない。** 各標本の時刻 `Step.t` は**数え上げて**作られる
（`engine/trajectory/plan.py` が `t = duration * k / (count-1)` で作るのと同じ数である）。
**送る側は絶対の期限を引き、この列を追う。**

⚠️ **これは「動きの硬さ」への答えである。** 基板は姿勢を1つ受け取って1回動く。
**離れる姿勢と取る姿勢の間を埋めるのは、上流の仕事である**——
`records/2026-10-18-the-gestures.md` の「動きが硬い」は、表の欠陥ではなく、ここが無かったことである。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from engine.backend.protocol_stackchan_pose import Pose, encode
from engine.trajectory.plan import plan

__all__ = ["Motion", "Step", "motion", "chain"]


@dataclass(frozen=True)
class Step:
    """**1つの刻み。** 開始からの秒と、その時点の姿勢、そしてその行。

    ⚠️ **行をここで作るのは、送る側に規則を持たせないためである。**
    綴り・和・改行は `protocol_stackchan_pose.encode` のものであり、**ここは数えない。**
    """

    t: float
    pose: Pose
    line: bytes


@dataclass(frozen=True)
class Motion:
    """**1つの動き。** 両端と、等間隔の標本列。"""

    duration: float
    period: float
    starts: Pose
    ends: Pose
    steps: tuple[Step, ...]

    @property
    def count(self) -> int:
        return len(self.steps)

    @property
    def last(self) -> Step:
        return self.steps[-1]


def _tenths(value: float, name: str) -> int:
    """⚠️ **度を、この線の単位へ。** 有限でない値は、丸める前に断る。"""
    if not math.isfinite(value):
        raise ValueError(f"{name} が有限でない: {value!r}")
    return round(value * 10)


def motion(starts: Pose, ends: Pose, duration: float, period: float,
           profile: object = "min-jerk") -> Motion:
    """`starts` から `ends` へ、`duration` 秒で動く標本列を組む。

    ⚠️ **`profile` は名前でも、族の実体でもよい**——`engine/trajectory/profile.py` の
    `Spring` のように、名前だけでは決まらない数を持つ族があるからである
    （`Spring(sharpness=…)`）。**ここはその数を決めない。**

    ⛔ **端は厳密に置く。** `plan` が `k == 0` と `k == count-1` を両端そのものにするので、
    **10分の1度に戻したとき、始点と終点は入力と1つも違わない**（丸めは整数の上で閉じる）。

    ⚠️ **`period` は刻みの目安であり、契約ではない。** 標本は `round(duration/period)+1` 個で、
    実際の間隔は `duration/(count-1)` である——**送る側は `period` ではなく `Step.t` を追う。**
    そうしないと、割り切れない秒数のときに、要求した刻みと標本の時刻が静かにずれる。
    """
    for name, pose in (("starts", starts), ("ends", ends)):
        if not isinstance(pose, Pose):
            raise TypeError(f"{name} は Pose である: {type(pose).__name__}")
    if duration <= 0.0:
        raise ValueError(f"duration は正である: {duration!r}")
    if period <= 0.0:
        raise ValueError(f"period は正である: {period!r}")

    count = max(2, round(duration / period) + 1)
    trajectory = plan(
        (starts.yaw_tenths / 10.0, starts.pitch_tenths / 10.0),
        (ends.yaw_tenths / 10.0, ends.pitch_tenths / 10.0),
        duration,
        profile=profile,
        labels=("yaw", "pitch"),
        count=count,
    )
    steps = []
    for sample in trajectory.samples:
        pose = Pose(
            yaw_tenths=_tenths(sample.position[0], "yaw"),
            pitch_tenths=_tenths(sample.position[1], "pitch"),
        )
        steps.append(Step(t=sample.t, pose=pose, line=encode(pose)))
    return Motion(
        duration=duration,
        period=period,
        starts=starts,
        ends=ends,
        steps=tuple(steps),
    )


def chain(parts: tuple[Motion, ...]) -> Motion:
    """**いくつかの動きを、1つの列にする。**

    ⛔ **時刻は数え直す。** 2つ目の `Step.t` は**自分の動きの始まりから**の秒なので、
    そのまま並べると、2つ目が時刻0へ戻る——**続く列ではなく、重なった列**になる。

    ⚠️ **継ぎ目の姿勢は1つだけ残す。** 前の動きの最後の標本と、次の動きの最初の標本は
    同じ姿勢である——両方書けば、同じ瞬間に同じ行が2つ出る。
    ⇒ **次の動きの1つ目の標本を捨て、残りを前の長さだけずらす。**
    """
    motions = tuple(parts)
    if not motions:
        raise ValueError("chain には1つ以上の Motion が要る")
    steps: list[Step] = []
    offset = 0.0
    for index, part in enumerate(motions):
        for step in (part.steps if index == 0 else part.steps[1:]):
            steps.append(Step(t=offset + step.t, pose=step.pose, line=step.line))
        offset += part.duration
    return Motion(
        duration=offset,
        period=motions[0].period,
        starts=motions[0].starts,
        ends=motions[-1].ends,
        steps=tuple(steps),
    )
