# -*- coding: utf-8 -*-
"""周期——**締切は絶対時刻である。**

⛔ **このファイルが、[05] §2.2 の「まだ書いていない検査」を閉じる。**
同節は周期について、書ける検査は2つだけだと書いていた——
**「締切方式で書かれている」（コードの形）**と、**「`sleep(period)` を毎回呼んでいない」（grep）**。
⛔ **`grep` は、その行がソースに在ることを言う。走ったときに成り立つことは言わない。**

⇒ **時計を注入すると、`grep` だった2つが実行時の主張になる。**
**このファイルは、偽の時計でループを本当に走らせ、要求された `sleep` を数える。**

⚠️ **数えているのは `sleep` の呼び出しであって、実時間ではない。**
**実機の上で何 ms で返るかは、この層では測れない**（[02_調査/08] §3.4——
**同じ機械が 5 ms と 10 ms の二状態を取る**）。**だから `period` に既定値が無い。**
"""
from __future__ import annotations

import pytest

from conftest import FakeClock
from engine.backend.cycle import Schedule, Tick, run


# --------------------------------------------------------------------------
# ⛔ 締切は絶対時刻である
# --------------------------------------------------------------------------


def test_the_deadline_is_start_plus_n_times_period():
    """⛔ **`前の締切 + period` ではない。** 遅れが累積しない形である。"""
    clock = FakeClock(overshoot=0.003)  # ⚠️ 毎回 3 ms 余計に眠る
    ticks = run(Schedule(period=0.01), clock, lambda t: None, 20)
    for tick in ticks:
        assert tick.deadline == pytest.approx(tick.n * 0.01, abs=1e-12), (
            f"⛔ 締切が累積している: 刻み {tick.n} の締切が {tick.deadline}"
        )


def test_a_late_tick_does_not_push_the_next_deadline():
    """⛔ **余計に眠ったぶんは、次の締切を動かさない。** 遅れが溜まらないこと。"""
    clock = FakeClock(overshoot=0.003)
    ticks = run(Schedule(period=0.01), clock, lambda t: None, 20)
    assert ticks[-1].deadline == pytest.approx(0.19)
    # ⚠️ 遅れは一定の枠に収まる（スピンの刻みの分だけ）
    assert max(t.lateness for t in ticks) <= 0.0005 + 1e-9
    assert ticks[-1].lateness == pytest.approx(ticks[0].lateness, abs=0.0005 + 1e-9)


# --------------------------------------------------------------------------
# ⛔ grep だった検査が、実行時の主張になる
# --------------------------------------------------------------------------


def test_sleep_is_a_fraction_of_the_period_never_the_whole_period():
    """⛔ **[02_調査/08] §8 の2番を、呼び出しの量として数える。**

    「締切の 50〜70% だけ眠り、残りはスピン」——**`sleep(period)` は、この形の否定である。**
    ⚠️ **この検査は、`grep` では代われない。** `sleep(period)` と書いていないコードでも、
    **`deadline - now` を丸ごと眠れば、同じことになる。**
    """
    clock = FakeClock()
    run(Schedule(period=0.01, sleep_fraction=0.6), clock, lambda t: None, 50)
    assert clock.sleeps, "⛔ **1回も眠っていない。** 検査が空を相手にしている"
    for s in clock.sleeps:
        assert s <= 0.01 * 0.6 + 1e-9, f"⛔ **締切を丸ごと眠っている: {s}**"
    assert clock.spins > 0, "⛔ **スピンしていない。** 2番の後半が実行されていない"


def test_the_sleep_target_is_the_deadline_minus_the_spin_share():
    """⚠️ **眠る長さは、締切から逆算される。** 一定値ではない。"""
    clock = FakeClock()
    run(Schedule(period=0.01, sleep_fraction=0.5), clock, lambda t: None, 5)
    # ⚠️ 1回目は t=0 から眠るので、ちょうど period の 50% である
    assert clock.sleeps[0] == pytest.approx(0.005)


def test_wake_at_returns_a_time_not_a_duration():
    """⛔ **名前が「まで」なら、返すのは時刻である。**

    ⚠️ **この版の最初は、`deadline` を受け取って無視し、「眠る長さ」を返していた。**
    `0.996`（時刻）と `0.006`（長さ）は、**同じ規則の裏表である。**
    """
    sched = Schedule(period=0.01, sleep_fraction=0.6)
    assert sched.wake_at(1.0) == pytest.approx(0.996)
    assert sched.wake_at(2.0) == pytest.approx(1.996)
    assert sched.wake_at(1.0) != pytest.approx(0.006)


# --------------------------------------------------------------------------
# ⛔ 規則が、注記ではなく型になっている
# --------------------------------------------------------------------------


def test_the_period_has_no_default():
    """⛔ **§8 の6番——実測の数値を、そのまま設計定数にしない。**

    **既定値を置けば、この工房は「実測」を「定数」に変えたことになる。**
    """
    with pytest.raises(TypeError):
        Schedule()  # type: ignore[call-arg]


def test_the_sleep_fraction_is_held_to_the_range():
    """⚠️ **0.5〜0.7 の外は、構築の時点で落ちる。** docstring の中に住ませない。"""
    for frac in (0.0, 0.49, 0.71, 1.0, -0.1):
        with pytest.raises(ValueError, match="50〜70%"):
            Schedule(period=0.01, sleep_fraction=frac)


def test_the_edges_of_the_range_are_allowed():
    assert Schedule(0.01, 0.5).sleep_fraction == 0.5
    assert Schedule(0.01, 0.7).sleep_fraction == 0.7
    assert Schedule(0.01).sleep_fraction == 0.6  # ⚠️ 既定は範囲の中の1点である


def test_a_period_of_zero_is_refused():
    with pytest.raises(ValueError, match="周期は正"):
        Schedule(period=0.0)


# --------------------------------------------------------------------------
# ⛔ 追いつけないときは、追いつかない
# --------------------------------------------------------------------------


def test_a_long_body_causes_a_skip_not_a_burst():
    """⛔ **ここが、遅れたときの選択である。**

    絶対時刻で締切を持つと、`body` が周期より長くかかったとき
    **溜まった締切を追いかけて連射する**——100 Hz のつもりが、3回ぶんを一息に送る。
    **それは機体の上では段差である**（上流ファームに補間が無い、[02_調査/01] §2.6）。

    ⇒ **1周期を超えて遅れた回は、諦める。** そして**諦めたことを数える。**
    """
    clock = FakeClock()
    sched = Schedule(period=0.01)

    def body(tick: Tick) -> None:
        if tick.n == 0:
            clock.advance(4 * sched.period)  # ⛔ **周期の4倍かかった**

    ticks = run(sched, clock, body, 3)
    assert any(t.missed_before > 0 for t in ticks), "⛔ **飛ばしていない。連射している**"
    # ⛔ **どの刻みも、締切から1周期より遅れて始まっていない**
    assert all(t.lateness <= sched.period + 1e-9 for t in ticks), (
        f"⛔ **溜まった締切を追いかけている**: {[t.lateness for t in ticks]}"
    )
    # ⚠️ そして、刻みの番号は飛んでいる（**周期の番号を偽らない**）
    assert [t.n for t in ticks] == sorted(t.n for t in ticks)
    assert [t.n for t in ticks] != list(range(len(ticks)))


def test_skipped_ticks_are_reported_on_the_next_tick():
    """⚠️ **飛ばした回は、次の刻みに載る。** 黙って消えない。"""
    clock = FakeClock()
    sched = Schedule(period=0.01)

    def body(tick: Tick) -> None:
        if tick.n == 0:
            clock.advance(4 * sched.period)

    ticks = run(sched, clock, body, 3)
    assert ticks[0].missed_before == 0
    assert max(t.missed_before for t in ticks) == 2


# --------------------------------------------------------------------------
# 端
# --------------------------------------------------------------------------


def test_zero_ticks_runs_nothing():
    clock = FakeClock()
    assert run(Schedule(period=0.01), clock, lambda t: None, 0) == ()
    assert clock.sleeps == [] and clock.spins == 0


def test_a_negative_tick_count_is_refused():
    with pytest.raises(ValueError, match="刻みの数が負"):
        run(Schedule(period=0.01), FakeClock(), lambda t: None, -1)


def test_the_tick_starts_at_its_deadline_not_after_it():
    """⚠️ **0番目の締切は「いま」である。** 出だしで1周期待たない。"""
    clock = FakeClock()
    ticks = run(Schedule(period=0.01), clock, lambda t: None, 1)
    assert ticks[0].deadline == 0.0 and ticks[0].started == 0.0
