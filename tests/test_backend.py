# -*- coding: utf-8 -*-
"""端から端まで——**周期ループが、門を通して、Mock へ送る。**

⛔ **これが、このリポジトリで初めて「機体の代わりに何かが動く」段である。**
⚠️ **そして、動いているのは箱のふりをした Python である。**
**`CLAUDE.md` の「Mock はプロトコルの試験である」は、ここでも真である。**

**繋がっているもの**（[05] §3.2 の「機体が要らない」側）:

| 層 | モジュール | 何を決めるか |
|---|---|---|
| 周期 | `cycle.py` | **いつ**呼ぶか（締切は絶対時刻） |
| 送信 | `transmit.py` | **どの標本**を送るか（壁時計にいちばん近いもの） |
| 門 | `gate.py` | **送ってよいか**（枠と段差） |
| 軸の対応 | `axis_map.py` | **どのモーターへ**（実測の数。既定は無い） |
| 箱 | `mock.py` | **何が届いたか**（そして、届かなかったこと） |

⚠️ **足りない1本がある**——**シリアル層である。** 制御箱には2世代あり、
**プロトコルがその間で違う**ので、このリポジトリはまだ書かない（`engine/backend/__init__.py`）。
**ゆえに、ここで動いているものは、1バイトも機体へ行っていない。**
"""
from __future__ import annotations

import pytest

from conftest import FakeClock
from engine.backend.axis_map import AxisMap, ChannelCalibration
from engine.backend.cycle import Schedule, run
from engine.backend.gate import Gate
from engine.backend.mock import MockBox
from engine.backend.transmit import Transmitter
from engine.trajectory.limits import ChannelLimits
from engine.trajectory.plan import plan

DURATION = 0.5
COUNT = 6  # ⚠️ 標本の刻みは 0.1 秒である
PERIOD = 0.02  # ⚠️ 周期は 20 ms（**この数は既定値ではない。呼ぶ側が決める**）


def _rig(limits=None):
    traj = plan(starts=(500.0,), ends=(600.0,), duration=DURATION,
                labels=("pitch",), count=COUNT)
    amap = AxisMap(channels={
        "pitch": ChannelCalibration(motor=0, sign=1, offset=0.0, scale=1.0),
    })
    gate = Gate(starts_by_motor=(500.0,),
                limits_by_motor=(limits or ChannelLimits(),))
    return Transmitter(trajectory=traj, axis_map=amap, gate=gate)


def _clock():
    return FakeClock(overshoot=0.0005)  # ⚠️ **実機では、余計に眠るのが普通である**


# --------------------------------------------------------------------------
# ✅ まっすぐな道
# --------------------------------------------------------------------------


def test_the_loop_drives_the_whole_trajectory_into_the_mock():
    """**周期 → 送信 → 門 → 箱。** ⛔ **そして、端に着く。**

    ⚠️ **ここで緑になることは「機体が正しく動く」ではない。**
    **「この経路が、指示されたとおりに計算した」だけである。**
    """
    tx = _rig()
    box = MockBox()
    clock = _clock()
    sent = []

    def body(tick):
        frames = tx.frames_at(0.0, tick.started)
        sent.append(frames)
        for frame in frames.verdict.frames:
            box.feed(frame.raw, tick.started)

    ticks = run(Schedule(PERIOD), clock, body, 25)  # 25 × 20 ms = 0.5 秒

    assert len(ticks) == 25
    assert box.positions[0] == 600.0, "⛔ **端に着いていない**"
    assert sent[-1].sample_t == pytest.approx(DURATION)


def test_the_value_never_goes_backwards_on_a_monotone_trajectory():
    """⚠️ **単調な軌道は、単調に届く。** 門も送信も、順序を入れ替えない。"""
    tx = _rig()
    box = MockBox()
    clock = _clock()

    def body(tick):
        frames = tx.frames_at(0.0, tick.started)
        for frame in frames.verdict.frames:
            box.feed(frame.raw, tick.started)

    run(Schedule(PERIOD), clock, body, 25)
    after = [step.after for step in box.steps]
    assert after == sorted(after)
    assert after[0] == 500.0 and after[-1] == 600.0


def test_something_is_sent_on_every_tick():
    """⛔ **1フレームも空が無い。** **「送らない」は「止まる」ではない。**

    ⚠️ **この検査は、門が枠の外の値を1つも作らない前提で通っている。**
    **門が弾いたときも空にはならない**——それは `test_gate.py` が持っている。
    """
    tx = _rig()
    box = MockBox()
    clock = _clock()

    def body(tick):
        frames = tx.frames_at(0.0, tick.started)
        for frame in frames.verdict.frames:
            box.feed(frame.raw, tick.started)

    run(Schedule(PERIOD), clock, body, 25)
    assert len(box.received) == 25, "⛔ **沈黙した刻みが在る**"


# --------------------------------------------------------------------------
# ⛔ 遅れたとき——**そして、ここに限界がある**
# --------------------------------------------------------------------------


def test_a_late_body_skips_ticks_instead_of_bursting_them():
    """⚠️ **飛ばした回は、飛ばしたままである。** 溜まった締切を追いかけない。

    ⛔ **数え方が2つある。** **走った回**（`len(ticks)`）と、**消費した締切**（`tick.n`）である——
    **飛ばした回は、前者に載らず、後者に載る。** その差が、遅れの正体である。
    """
    tx = _rig()
    box = MockBox()
    clock = _clock()

    def body(tick):
        if tick.n == 1:
            clock.advance(0.05)  # ⛔ **2.5 周期かかった**
        frames = tx.frames_at(0.0, tick.started)
        for frame in frames.verdict.frames:
            box.feed(frame.raw, tick.started)

    ticks = run(Schedule(PERIOD), clock, body, 25)
    skipped = sum(t.missed_before for t in ticks)
    assert skipped > 0, "⛔ **連射している**"
    # ⛔ **消費した締切 − 走った回 ＝ 飛ばした回**（厳密に一致する）
    assert ticks[-1].n - (len(ticks) - 1) == skipped
    # ⚠️ **連射していないので、遅れはそのまま残る**（0.5 秒の軌道が 0.52 秒かかる）
    assert ticks[-1].started >= DURATION


def test_a_late_tick_freezes_the_axis_and_the_gate_does_not_recover():
    """⛔ **これは限界であって、設計ではない。** **著者へ返す論点である。**

    飛ばした刻みでは、送信が**標本を飛び越える**（`transmit.py`）。
    その段差を門が弾く。**門は「最後に通した組」を返す**——
    ⇒ **軸はそこで止まる。** ⚠️ **そして、そこから戻る道が、いまの門には無い。**

    理由: 門が保つ基準は「最後に**通した**値」であり、送信が提案するのは
    「**いまの**壁時計の値」である。**提案は先へ進み続けるので、段差は縮まらない。**
    ⇒ **`admit` を通った軌道でも、1回遅れると端に着かない。**

    ⚠️ **止まることは安全側である**（送り続けているのでトルクも保たれる）。
    ⛔ **だが「着かない」は、この機構の目的を果たしていない。**

    **著者への選択肢**（[05] §2.2 の周期の話の続きとして）:
    (a) **いまのまま**——弾いたら保つ。**凍る。**
    (b) **弾いたとき、限界まで寄せた値を組む**——**届く速さで、目標へ向かって進む。**
    (c) **速度の上限を、遅れを見込んだ値にする**（計画側で余裕を取る）。
    """
    tx = _rig(limits=ChannelLimits(velocity=100.0))  # 100 カウント/秒
    box = MockBox()
    clock = _clock()

    def body(tick):
        if tick.n == 1:
            clock.advance(0.05)
        frames = tx.frames_at(0.0, tick.started)
        for frame in frames.verdict.frames:
            box.feed(frame.raw, tick.started)

    run(Schedule(PERIOD), clock, body, 25)

    assert box.positions[0] < 600.0, "⚠️ 前提が変わった: いまは着いている"
    assert 600.0 not in [step.after for step in box.steps], (
        "⚠️ 前提が変わった: 目標が1回でも送られている"
    )
    assert len(box.received) > 20, "⛔ **凍ることと、黙ることは別である**"
