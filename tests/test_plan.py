# -*- coding: utf-8 -*-
"""検査 #4（決定論）と、標本の端——**同じ入力なら、同じビット列。**

⚠️ **「2回走らせて同じだった」は、決定論の証明ではない。**
だからここでは3つを見る: **同じ入力で同一であること**・**端が厳密であること**・
**`nan` が検査を通り抜けないこと**（`engine/trajectory/plan.py` の `_scale`）。
"""
from __future__ import annotations

import math

import pytest

from engine.trajectory.plan import Sample, Trajectory, plan
from engine.trajectory.profile import MinJerk, Trapezoid


def test_the_same_input_gives_the_same_samples():
    a = plan((100.0, 200.0), (400.0, 150.0), 0.75)
    b = plan((100.0, 200.0), (400.0, 150.0), 0.75)
    assert a.samples == b.samples
    assert a.samples[5].velocity == b.samples[5].velocity  # ビット列として同じ


def test_the_sample_times_are_counted_not_accumulated():
    """⛔ **`t += step` を繰り返さない。** 足し上げれば、誤差が溜まる。"""
    traj = plan((0.0,), (1.0,), 3.0, count=7)
    assert [s.t for s in traj.samples] == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    assert traj.samples[0].t == 0.0
    assert traj.samples[-1].t == 3.0


def test_the_ends_are_exact_to_the_bit():
    """⛔ **端は厳密に置く。** `start + (end - start)` は `end` に一致しないことがある。

    ⚠️ **機械へ送る最後の1つは、目標そのものでなければならない。**
    「丸め誤差で、目標に届かない」という失敗を作らない。
    """
    # ⚠️ **この2組は、探して見つけた実例である**（プロトコルのカウントと同じ桁で）。
    # 素朴に `start + (end - start)` を計算すると、**1 ULP 足りない。**
    starts = (-479.0153792160812, -522.7681427695596, 0.0)
    ends = (610.0556540260447, 935.0805005802868, 0.0)
    traj = plan(starts, ends, 1.0)
    assert traj.samples[0].position == starts
    assert traj.samples[-1].position == ends

    # ⚠️ **素朴な掛け算だと、一致しないことを見せる**（この検査が空を回っていないこと）
    naive = tuple(s + (e - s) * 1.0 for s, e in zip(starts, ends))
    assert naive != ends
    assert naive[0] != ends[0] and naive[1] != ends[1]


def test_the_ends_have_zero_velocity_and_acceleration_for_min_jerk():
    """検査 #1 を、軌道の側から。"""
    traj = plan((0.0, 5.0), (100.0, -5.0), 0.4)
    for k in (0, -1):
        assert traj.samples[k].velocity == (0.0, 0.0)
        assert traj.samples[k].acceleration == (0.0, 0.0)


def test_a_channel_that_does_not_move_never_produces_nan():
    """⛔ **`0.0 * inf` は `nan`。そして `nan > limit` は `False`。**

    台形のジャークは角で `inf` である。**動かない軸が在ると、そこで `nan` が生まれる**——
    そして **`nan` は制限の検査を、静かに通り抜ける。**
    （`CLAUDE.md`「空の検査は OK と言う」／`engine/trajectory/plan.py` の `_scale`）
    """
    traj = plan((10.0, 10.0), (10.0, 90.0), 0.5, profile=Trapezoid(1.0))
    for s in traj.samples:
        for series in (s.position, s.velocity, s.acceleration, s.jerk):
            assert not any(math.isnan(v) for v in series)
    # 動かない軸は、位置も速度も加速度もジャークも 0
    assert {s.jerk[0] for s in traj.samples} == {0.0}
    assert {s.velocity[0] for s in traj.samples} == {0.0}
    # 動く軸のジャークは、角で inf である（**0 に潰していない**）
    assert any(math.isinf(s.jerk[1]) for s in traj.samples)


def test_at_refuses_to_interpolate():
    """⛔ **標本の間に、値をこしらえない。**"""
    traj = plan((0.0,), (1.0,), 1.0, count=5)
    assert traj.at(0.25).t == 0.25
    with pytest.raises(ValueError):
        traj.at(0.3)
    with pytest.raises(ValueError):
        traj.at(1.5)


def test_labels_are_carried_but_are_only_labels():
    """⚠️ **名札は配線ではない。** 自由度とモーターの対応は、この型は持たない。"""
    traj = plan((0.0, 0.0), (1.0, 1.0), 0.5, labels=("pitch", "roll"))
    assert traj.labels == ("pitch", "roll")
    assert traj.channel_count == 2
    assert not hasattr(traj, "motors")


def test_bad_input_is_refused():
    with pytest.raises(ValueError):
        plan((0.0,), (1.0, 2.0), 1.0)
    with pytest.raises(ValueError):
        plan((), (), 1.0)
    with pytest.raises(ValueError):
        plan((0.0,), (1.0,), 0.0)
    with pytest.raises(ValueError):
        plan((0.0,), (1.0,), 1.0, count=1)
    with pytest.raises(ValueError):
        plan((0.0,), (1.0,), 1.0, labels=("a", "b"))
    with pytest.raises(ValueError):
        MinJerk().shape(1.5)
