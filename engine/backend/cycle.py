# -*- coding: utf-8 -*-
"""周期——**締切は絶対時刻。`sleep(period)` を毎回呼ばない。**

⛔ **[05] §2.2 は「周期は検査しにくい」と書いた。そして、そのとおりである。**
同節が「書ける検査」として挙げたのは2つだけだった——**「締切方式で書かれている」（コードの形）**と
**「`sleep(period)` を毎回呼んでいない」（grep で鳴る）**。
⛔ **そして 2026-09-27 の時点で、そのどちらも書いていなかった**（送る側が1行も無かったからである）。

⇒ ⛔ **だが、時計を注入すると、この2つは grep ではなく試験になる。**
`engine/` は `time` を import しない（`tests/test_purity.py`）。
**ゆえにこのループは `now()` と `sleep()` を外から受け取る**——**そして、偽の時計で走らせられる。**

**このモジュールが、検査できる形に変えたもの**（[02_調査/08] §8 の番号で言う）:

| # | §8 の提案 | このモジュールでの形 |
|---|---|---|
| **1** | 締切の絶対時刻で持つ | ✅ **`deadline(start, n) = start + n * period`。** 遅れが累積しないことを試験できる |
| **2** | `sleep` は締切の 50〜70%、残りはスピン | ✅ **`sleep_fraction` は範囲外を構築時に拒む**——**規則が、注記ではなく型になった** |
| **3** | 専用スレッドに置く（`asyncio` に置かない） | ⚠️ **このループは宿主を知らない。** thread か asyncio かは、下の層の話である（`Clock` を見よ） |
| **4** | RT ポリシーは現実的な値で申告する | ⛔ **ここには無い。** アダプタの仕事である |
| **5** | `uvloop` を使わない | ⛔ **ここには無い。** 同上 |
| **6** | **この数値をそのまま設計定数にしない** | ⛔ **ゆえに `period` に既定値が無い。** 呼ぶ側が必ず決める |

⚠️ **6番が、このモジュールに既定値を1つも置かない理由である。**
[02_調査/08] §3.4 は、**同じ機械が 5 ms と 10 ms の二状態を取る**ことを実測している。
**その片方を既定値にすると、この工房は「実測」を「定数」に変えたことになる。**
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

__all__ = ["Clock", "Schedule", "Tick", "run"]


class Clock(Protocol):
    """⚠️ **時計は注入される。** `engine/` の中で `time` を import しないためである。

    ⛔ **`sleep(0.0)` は「スピンせよ」の意味である。** 実装側は
    `time.sleep(0)` でも `sched_yield` でもよい——**譲り方は宿主が決める。**
    """

    def now(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...


@dataclass(frozen=True)
class Schedule:
    """⚠️ **`period` に既定値は無い**（[02_調査/08] §8 の6番）。

    ⛔ **`sleep_fraction` は 0.5〜0.7 の外を拒む。**
    §8 の2番が「締切の 50〜70% だけ sleep して、残りはスピン」と書いている——
    **範囲を型で押さえないと、この規則は docstring の中だけに住む。**
    """

    period: float
    sleep_fraction: float = 0.6

    def __post_init__(self) -> None:
        if not self.period > 0:
            raise ValueError(f"周期は正でなければならない: {self.period}")
        if not 0.5 <= self.sleep_fraction <= 0.7:
            raise ValueError(
                f"sleep は締切の 50〜70% である: {self.sleep_fraction}"
                "——⛔ **[02_調査/08] §8 の2番。** ⚠️ **最適な配分は測っていないので、"
                "範囲の中の1点を選ぶのは呼ぶ側である**"
            )

    def deadline(self, start: float, n: int) -> float:
        """⛔ **絶対時刻である。** `前の締切 + period` ではない。

        ⇒ **遅れた回は、遅れたぶんだけ次が詰まる**——**累積しない。**
        """
        return start + n * self.period

    def wake_at(self, deadline: float) -> float:
        """⚠️ **何時まで眠るか**——**時刻である。眠る長さではない。**

        ⛔ **ここが2番の規則の、唯一の実装である。**
        締切の手前 `sleep_fraction` までで眠りをやめ、**残りはスピンで詰める。**

        ⚠️ **この版の最初は `sleep_until(deadline)` という名前で、
        引数の `deadline` を使わずに「眠る長さ」を返していた**——
        **名前が「まで」と言い、中身が「ぶん」を返していた。**
        使う側（`run`）は同じ式をもう一度書いていて、**2箇所に同じ数があった。**
        """
        return deadline - self.period * (1.0 - self.sleep_fraction)


@dataclass(frozen=True)
class Tick:
    """1回の刻み。**遅れを隠さない。**"""

    n: int
    deadline: float
    started: float
    missed_before: int  # ⚠️ **この刻みの前に飛ばした回数**

    @property
    def lateness(self) -> float:
        """⚠️ **負なら早い。** 0 が理想である。"""
        return self.started - self.deadline


def run(schedule: Schedule, clock: Clock, body: Callable[[Tick], None],
        ticks: int) -> tuple[Tick, ...]:
    """**締切で `body` を呼ぶ。** ⛔ **遅れた回は、飛ばして数える。**

    戻り値は**実際に走った刻みである**——**飛ばした回は `missed_before` に載る。**

    ⛔ **飛ばす理由。** 締切を絶対時刻で持つと、`body` が周期より長くかかったとき
    **溜まった締切を追いかけて連射することになる**——100 Hz のつもりが、
    3回ぶんを一息に送る。**それは機体の上では段差である。**
    ⇒ **追いつかないときは、追いつかない方が正しい。**

    ⚠️ **これはこちらの選択である。** [02_調査/08] は「絶対時刻で持つ」とは書くが、
    **追いつけなくなったときにどうするかは書いていない。**
    """
    if ticks < 0:
        raise ValueError(f"刻みの数が負: {ticks}")

    start = clock.now()
    out: list[Tick] = []
    n = 0
    skipped = 0
    while len(out) < ticks:
        deadline = schedule.deadline(start, n)
        now = clock.now()
        if now > deadline + schedule.period:
            # ⛔ **1周期を超えて遅れている。** この回は諦める。
            skipped += 1
            n += 1
            continue
        sleep_target = schedule.wake_at(deadline)
        if now < sleep_target:
            clock.sleep(sleep_target - now)
        while clock.now() < deadline:
            clock.sleep(0.0)  # ⚠️ **スピン。譲り方は `Clock` が決める**
        tick = Tick(n=n, deadline=deadline, started=clock.now(), missed_before=skipped)
        out.append(tick)
        skipped = 0
        n += 1
        # ⛔ **`body` はここで走る。** ⚠️ **`started` は「走り始めた時刻」である**——
        # **`body` の中の時刻ではない**（長くかかれば、`now` は先へ進む）。
        # **この2つを取り違えると、遅れの測り方が変わる。**
        body(tick)
    return tuple(out)
