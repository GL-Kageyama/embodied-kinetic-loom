# -*- coding: utf-8 -*-
"""**姿勢の列を、絶対の期限で1行ずつ出す。** ⛔ **時計は読まない**——`at` は値である。

⚠️ **これは縁のためだけのものではない。** 首の縁（`neck/__main__.py`）とデーモンは
同じ規則で列を追う——**各標本の `Step.t` へ絶対の期限で着き、最後の姿勢を `hold` 秒だけ
書き続け、遅れを数える。** 規則を2つ書かないために、ここに1つ置く。

⛔ **相対の `sleep(period)` を重ねない。** 1行ごとの誤差が積もり、20 ms と言いながら
25 ms で流れる——それは送った列ではなく、**送りたかった列**である。
⚠️ **期限にちょうど着くのは遅刻ではない。** 遅れは半周期を超えた行だけを数える
（2026-10-18、真偽で返す計器が31行すべてを遅刻と数えた）。
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.backend.protocol_stackchan_pose import Pose

from .motion import Motion, Step

__all__ = ["Summary", "Stream"]


@dataclass(frozen=True)
class Summary:
    """**1つの動きの、終わりの1行。** ⚠️ **数は、送った行の数である。**"""

    name: str | None
    applied: int
    late: int
    held: int
    at: float


class Stream:
    """**1つの列を、期限に従って1行ずつ返す。** ⛔ ソケットもポートも知らない。

    ⚠️ **`line(at)` は、期限を過ぎた行を1つだけ返す。** 呼ぶ側は、`None` が返るまで
    呼ぶ——**溜まっていた行は、そうやって追いつく**（遅れとして数えられる）。
    """

    def __init__(self, *, period: float = 0.02, hold: float = 0.6) -> None:
        if period <= 0.0:
            raise ValueError(f"period は正である: {period!r}")
        if hold < 0.0:
            raise ValueError(f"hold は負でない: {hold!r}")
        self._period = period
        self._hold = hold
        self._steps: tuple[Step, ...] = ()
        self._index = 0
        self._start = 0.0
        self._end = 0.0
        self._next = 0.0
        self._running = False
        self._late = 0
        self._held = 0
        self._last: Step | None = None
        self._name: str | None = None
        self._summary: Summary | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def name(self) -> str | None:
        return self._name

    @property
    def last_pose(self) -> Pose | None:
        """**最後に出した姿勢。** ⚠️ **終わった後も残る**——次の動きの始点である。

        ⛔ **予定の終点ではない。** 途中で新しい身振りに割り込まれたら、首は
        **そこまでしか行っていない**——だから始点は、命じた終点ではなく、出した行である。
        """
        return self._last.pose if self._last is not None else None

    @property
    def deadline(self) -> float | None:
        """**次に書くべき時刻。** ⛔ 動いていなければ `None`。"""
        if not self._running:
            return None
        if self._index < len(self._steps):
            return self._start + self._steps[self._index].t
        return min(self._next, self._end)

    def start(self, plan: Motion, at: float, name: str | None = None) -> None:
        """**`at` から列を始める。** ⚠️ **`at` は判定の時刻そのものである。**

        ⛔ **割り込まれた動きの要約は、ここでは捨てない**——呼ぶ側が
        `stop` と `take_summary` で先に取り出す（`Neck.take`）。
        """
        if not plan.steps:
            raise ValueError("空の列は流せない")
        self._steps = plan.steps
        self._index = 0
        self._start = at
        self._end = at + plan.duration + self._hold
        self._next = 0.0
        self._running = True
        self._late = 0
        self._held = 0
        self._last = None
        self._name = name
        self._summary = None

    def line(self, at: float) -> bytes | None:
        """**期限の来た1行。** ⚠️ **無ければ `None`**——**空の行は返さない。**"""
        if not self._running:
            return None

        if self._index < len(self._steps):
            step = self._steps[self._index]
            due = self._start + step.t
            if at < due:
                return None
            # ⚠️ **半周期を超えて遅れた行だけを数える**——期限ちょうどは遅刻ではない。
            if at - due > self._period / 2.0:
                self._late += 1
            self._index += 1
            self._last = step
            if self._index == len(self._steps):
                # ⚠️ **保持の1つ目は、最後の標本の1周期後である。** 同じ瞬間に2度書かない。
                self._next = self._start + step.t + self._period
            return step.line

        if at >= self._end:
            self._stop(at)
            return None
        if at < self._next:
            return None
        self._held += 1
        self._next += self._period
        assert self._last is not None
        return self._last.line

    def stop(self, at: float) -> None:
        """**列を捨てる。** ⚠️ **送った数は、送った数として残る。**"""
        if self._running:
            self._stop(at)

    def take_summary(self) -> Summary | None:
        """**終わりの1行を1度だけ返す。** ⚠️ 2度目は `None` である。"""
        summary, self._summary = self._summary, None
        return summary

    def _stop(self, at: float) -> None:
        self._running = False
        self._summary = Summary(
            name=self._name,
            applied=self._index,
            late=self._late,
            held=self._held,
            at=at,
        )
