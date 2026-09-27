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


def test_a_refused_axis_creeps_toward_the_target_instead_of_freezing():
    """⛔ **弾かれた軸は、凍るのでなく、届く速さで目標へ寄る。**

    ⚠️ **この検査は、前は逆を主張していた**——「軸が凍り、門は戻らない」と。
    ⛔ **それは限界であり、著者へ返した論点だった**（[05] §2.2 の周期の話の続き）。
    **3案のうち (b) を採った**——**(a) は凍り、(c) は計画を常に遅くする。**

    **理由**（`engine/backend/gate.py` のモジュールを見よ）:
    門が保つ基準は「最後に**通した**値」であり、送信が提案するのは
    「**いまの**壁時計の値」である。**提案は先へ進み続けるので、段差は縮まらない。**
    ⚠️ **そして弾くたびに `_last_t` が進むので、溜まった時間が毎回捨てられる**——
    ⇒ **1回弾かれると、二度と通らない。**

    ⛔ **寄せる大きさは `limit × elapsed`——門がもともと通す大きさと同じである。**
    ⇒ **新しい仮定を1つも足していない。**

    ⚠️ **そして、この軌道は依然として端に着かない**——**門の上限（100 カウント/秒）が、
    計画の速さの半分だからである。** **寄るという直しは、それを直さない**——
    **計画が門の上限を超えていることを見つけるのは `admit` の仕事である。**
    """
    tx = _rig(limits=ChannelLimits(velocity=100.0))  # 100 カウント/秒
    box = MockBox()
    clock = _clock()

    def body(tick):
        if tick.n == 1:
            clock.advance(0.05)  # ⛔ **刻みが1つ遅れる**
        frames = tx.frames_at(0.0, tick.started)
        for frame in frames.verdict.frames:
            box.feed(frame.raw, tick.started)

    ticks = run(Schedule(PERIOD), clock, body, 25)

    moved = box.positions[0] - 500.0
    allowed = 100.0 * ticks[-1].started  # 門が、この時間に許した総量
    assert moved > 0.0, "⛔ **凍っている**——弾かれた軸が1つも動いていない"
    assert moved <= allowed + 1.0, f"⛔ **門の許す速さを超えて動いた**: {moved} > {allowed}"
    assert moved >= allowed * 0.7, (
        f"⚠️ **溜めた余裕を使い切っていない**: {moved} / {allowed}"
        "——弾くたびに時間を捨てていないか"
    )
    assert box.positions[0] < 600.0, "⚠️ 前提が変わった: いまは着いている"
    assert 600.0 not in [step.after for step in box.steps], (
        "⚠️ 前提が変わった: 目標が1回でも送られている"
    )
    assert len(box.received) > 20, "⛔ **動くことと、黙ることは別である**"


def test_the_gate_never_lets_an_axis_move_faster_than_its_limit():
    """⛔ **寄せた値も、門の上限の中である。**

    ⚠️ **これが (b) を選んでよい理由そのものである**——
    **寄せた値は、門がもともと通す大きさを超えない。**
    """
    tx = _rig(limits=ChannelLimits(velocity=100.0))
    box = MockBox()
    clock = _clock()
    seen = []

    def body(tick):
        if tick.n == 1:
            clock.advance(0.05)
        fs = tx.frames_at(0.0, tick.started)
        seen.append((tick.started, fs.verdict.frames[0].value))
        for frame in fs.verdict.frames:
            box.feed(frame.raw, tick.started)

    run(Schedule(PERIOD), clock, body, 25)

    worst = 0.0
    for (t0, v0), (t1, v1) in zip(seen, seen[1:]):
        if t1 > t0:
            worst = max(worst, abs(v1 - v0) / (t1 - t0))
    assert worst <= 100.0 + 1e-9, f"⛔ **上限を超えた速さで指令した**: {worst} カウント/秒"

