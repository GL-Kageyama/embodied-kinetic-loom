# -*- coding: utf-8 -*-
"""送信——**軌道を、実際の時刻で引く。**

⛔ **ここに、このパッケージでいちばん見落としやすい1点がある。**

`Trajectory.at(t)` は**補間しない**——標本点でなければ `ValueError` を投げる（意図である）。
⚠️ **だが、周期ループの `now` は標本点に落ちない。** 遅れるからである。

⇒ **ゆえにここは、標本点で引くのでなく、`now` にいちばん近い標本を選ぶ。**

⛔ **どちらを選ぶかは、機体の上で意味が違う。**

| 選び方 | 遅れた刻みで何が起きるか |
|---|---|
| **標本を1つずつ進める**（時刻を無視） | ⛔ **軌道がゆっくりになる。** 5秒の動作が、遅れたぶんだけ長くかかる |
| **`now` にいちばん近い標本**（ここ） | ✅ **壁時計に追従する。** 遅れた刻みは**標本を飛ばす**——**そして、その段差は門が捕まえる** |

⇒ **門（`gate.py`）と、この選択は組で効く。**
**遅れは消せない。だが「遅れたときに何が機体へ行くか」は選べる。**

⚠️ **そして `stale_by` は、その選び方の代償を記録する**——
**送った値が、どの時刻の値なのか。** 0 ならちょうど、正なら遅れている。
**この数は Mock では意味を持たない。実機でだけ意味を持つ。**
"""
from __future__ import annotations

from dataclasses import dataclass

from ..trajectory.plan import Trajectory
from .axis_map import AxisMap
from .gate import Gate, Verdict
from .protocol import Frame, ProtocolError, encode_target

__all__ = ["FrameSet", "Transmitter"]


@dataclass(frozen=True)
class FrameSet:
    """**1刻みぶんの、実際に送るもの。**"""

    verdict: Verdict
    sample_t: float   # ⚠️ **送った値が対応する軌道の時刻**
    at: float         # ⚠️ **それを送ろうとした壁時計の時刻**
    stale_by: float   # `at - sample_t`。**0 が理想。正なら遅れている**


@dataclass
class Transmitter:
    """⚠️ **1つの軌道に1つ。** 組（`group`）を跨ぐのは呼ぶ側の仕事である。

    **`admit` は組ごとに1つの軌道を返す**（`engine/trajectory/admit.py`）——
    **ゆえに組の数だけ、これを順に走らせる。**
    """

    trajectory: Trajectory
    axis_map: AxisMap
    gate: Gate

    def _index(self, elapsed: float) -> int:
        n = len(self.trajectory.samples)
        step = self.trajectory.duration / (n - 1)
        k = round(elapsed / step)
        return min(n - 1, max(0, k))

    def frames_at(self, t0: float, now: float) -> FrameSet:
        """**`now` の時点で送るべき組を組む。** ⛔ **門を通してから返す。**

        ⚠️ **丸めてから門へ渡す。** 丸めは送る値そのものを変えるので、
        **門が見るのは丸めた後でなければならない**——**そうでないと、門は
        「出て行かない値」を検査していることになる。**
        """
        elapsed = now - t0
        if elapsed < 0:
            raise ValueError(f"軌道が始まる前である: t0={t0}, now={now}")
        clamped = min(elapsed, self.trajectory.duration)
        k = self._index(clamped)
        sample = self.trajectory.samples[k]

        frames: list[Frame] = []
        for label, value in zip(self.trajectory.labels, sample.position):
            counts = self.axis_map.to_counts(label, value)
            rounded = int(round(counts))
            try:
                frames.append(encode_target(self.axis_map.channels[label].motor, rounded))
            except ProtocolError:
                # ⛔ **2バイトに収まらない。** 門に渡す前に落とす——
                # **門は「送ってよいか」を見る段であり、「送れる形か」ではない。**
                raise
        verdict = self.gate.submit(now, tuple(frames))
        return FrameSet(verdict=verdict, sample_t=sample.t, at=now,
                        stale_by=now - t0 - sample.t)

    def done(self, t0: float, now: float) -> bool:
        """⚠️ **軌道の終わりに着いたか。** **「機体が止まった」ではない。**"""
        return now - t0 >= self.trajectory.duration
