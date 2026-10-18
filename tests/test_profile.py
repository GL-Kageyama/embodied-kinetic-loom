# -*- coding: utf-8 -*-
"""検査 #1（端の条件）と #3（可到達性）——**プロファイルの側から。**

⛔ **このファイルの主な仕事は、`trapezoid` が #1 で落ちることを記録することである。**
計画は台形を「フォールバック」として残すと書いている（[02_調査/02] §9.1）。
**だが台形は、両端で加速度がゼロでない。そして角でジャークが定義されない。**
⇒ **「フォールバック」は、検査を1つ外すことを意味する。**
**ここに書いておかないと、その1つは黙って外れる。**
"""
from __future__ import annotations

import math

import pytest

from engine.trajectory.profile import (
    MinJerk, Spring, Trapezoid, min_duration, profile_of, segments,
    trapezoid_for_velocity,
)


# --------------------------------------------------------------------------
# #1 端の条件
# --------------------------------------------------------------------------


def test_min_jerk_has_zero_position_velocity_acceleration_at_both_ends():
    """**位置・速度・加速度の3つが、両端でゼロ。** ⚠️ ジャークは入らない。"""
    p = MinJerk()
    for u in (0.0, 1.0):
        s = p.shape(u)
        assert s.velocity == 0.0
        assert s.acceleration == 0.0
    assert p.shape(0.0).position == 0.0
    assert p.shape(1.0).position == 1.0


def test_min_jerk_jerk_is_not_zero_at_the_ends():
    """⛔ **端でゼロなのは3つであって、4つではない。** ジャークは端で 60 を取る。"""
    p = MinJerk()
    assert p.shape(0.0).jerk == pytest.approx(60.0)
    assert p.shape(1.0).jerk == pytest.approx(60.0)
    assert p.shape(0.5).jerk == pytest.approx(-30.0)


def test_min_jerk_peaks_match_the_closed_form():
    """`peak()` の4つの数は、**式から出したものである。** 標本で確かめる。"""
    p = MinJerk()
    vs = [p.shape(i / 20000).velocity for i in range(20001)]
    assert max(vs) == pytest.approx(p.peak().velocity, rel=1e-6)
    assert min(vs) >= 0.0

    accs = [abs(p.shape(i / 20000).acceleration) for i in range(20001)]
    assert max(accs) == pytest.approx(p.peak().acceleration, rel=1e-4)
    assert max(accs) == pytest.approx(10.0 / math.sqrt(3.0), rel=1e-4)

    jerks = [abs(p.shape(i / 20000).jerk) for i in range(20001)]
    assert max(jerks) == pytest.approx(p.peak().jerk, rel=1e-9)


def test_min_jerk_position_is_monotone():
    """⚠️ **行き過ぎない。** 5次多項式は単調である（端で戻らない）。"""
    p = MinJerk()
    ps = [p.shape(i / 1000).position for i in range(1001)]
    assert all(b >= a for a, b in zip(ps, ps[1:]))


# --------------------------------------------------------------------------
# ⛔ 台形は #1 で落ちる
# --------------------------------------------------------------------------


def test_trapezoid_velocity_is_zero_at_both_ends():
    """速度だけは、端でゼロである。**それは台形の定義そのものである。**"""
    t = Trapezoid(0.5)
    assert t.shape(0.0).velocity == 0.0
    assert t.shape(1.0).velocity == 0.0


def test_trapezoid_acceleration_is_NOT_zero_at_the_ends():
    """⛔ **#1 の加速度の項で落ちる。** 端で ±a が立ち上がっている。"""
    t = Trapezoid(0.5)
    assert t.shape(0.0).acceleration != 0.0
    assert t.shape(1.0).acceleration != 0.0
    assert t.shape(0.0).acceleration == pytest.approx(-t.shape(1.0).acceleration)


def test_trapezoid_jerk_is_infinite_at_the_corners():
    """⛔ **#2 のジャークの項で落ちる。** 角が3つ（r=1 なら2つ）ある。

    ⚠️ **ここで `0.0` を返したら、検査は鳴らない。**
    """
    t = Trapezoid(0.5)
    t_a, t_c, t_d = segments(t)
    for u in (0.0, t_a, t_a + t_c, 1.0):
        assert t.shape(u).jerk == math.inf, u
    assert t.shape(t_a / 2.0).jerk == 0.0
    assert t.peak().jerk == math.inf


def test_trapezoid_shape_is_continuous_and_hits_both_ends():
    """**位置は連続で、0 から 1 へ行く。** 区間の継ぎ目で飛ばない。"""
    t = Trapezoid(0.4)
    assert t.shape(0.0).position == 0.0
    assert t.shape(1.0).position == 1.0

    ps = [t.shape(i / 20000).position for i in range(20001)]
    assert all(b >= a for a, b in zip(ps, ps[1:]))
    assert max(abs(b - a) for a, b in zip(ps, ps[1:])) < 1e-3  # 飛んでいない


def test_trapezoid_area_is_one_for_every_accel_fraction():
    """⚠️ **正規化の意味は、面積が 1 であること。** r を振って確かめる。"""
    for r in (0.1, 0.25, 0.5, 0.75, 1.0):
        t = Trapezoid(r)
        n = 20000
        area = sum(t.shape((i + 0.5) / n).velocity for i in range(n)) / n
        assert area == pytest.approx(1.0, rel=1e-4), r


# --------------------------------------------------------------------------
# ばね——機体2の純正ファームウェアが使っていた形（2026-10-18 に読んだ）
# --------------------------------------------------------------------------


def test_spring_hits_both_ends_with_zero_velocity():
    """⛔ **切り取ったばねは、そのままでは端で速度ゼロにならない。** 補正がそれを消す。

    ⚠️ **生のばねが `u = 1` でどれだけ動いているか**を、独立に計算して先に置く。
    """
    s = Spring(5.0)
    raw_residual = 25.0 * math.exp(-5.0) / (1.0 - 6.0 * math.exp(-5.0))
    assert s._residual() == pytest.approx(raw_residual)
    assert raw_residual > 0.1  # ⚠️ 生のばねは、切り取り点でもこれを動いている

    assert s.shape(0.0).position == pytest.approx(0.0)
    assert s.shape(1.0).position == pytest.approx(1.0)
    assert s.shape(0.0).velocity == pytest.approx(0.0, abs=1e-12)
    assert s.shape(1.0).velocity == pytest.approx(0.0, abs=1e-12)


def test_spring_position_is_monotone_and_velocity_never_negative():
    """⛔ **補正は形を支配しない。** どの sharpness でも、戻らない・逆走しない。"""
    for a in (1.5, 5.0, 12.0):
        s = Spring(a)
        ps, vs = [], []
        for i in range(4001):
            shape = s.shape(i / 4000)
            ps.append(shape.position)
            vs.append(shape.velocity)
        assert all(b >= a_ for a_, b in zip(ps, ps[1:])), a
        assert min(vs) >= 0.0, a


def test_spring_area_is_one():
    """⚠️ **正規化の意味は、面積が 1 であること。** 速度を積分して、距離になる。"""
    s = Spring(5.0)
    n = 40000
    area = sum(s.shape((i + 0.5) / n).velocity for i in range(n)) / n
    assert area == pytest.approx(1.0, rel=1e-6)


def test_spring_peak_is_an_upper_bound_and_close():
    """⚠️ **制限の検査に使う値だから、下から押さえてはいけない。**"""
    s = Spring(5.0)
    n = 20000
    shapes = [s.shape(i / n) for i in range(n + 1)]
    peak = s.peak()

    assert max(x.velocity for x in shapes) <= peak.velocity + 1e-12
    assert max(x.velocity for x in shapes) >= peak.velocity * 0.99

    assert max(abs(x.acceleration) for x in shapes) <= peak.acceleration + 1e-12
    assert max(abs(x.jerk) for x in shapes) <= peak.jerk + 1e-9


def test_spring_puts_its_speed_at_the_start_not_the_middle():
    """⚠️ **これが「ギュン」の正体である。** 同じ長さ・同じ端で、山の位置だけが違う。

    20%地点で、ばねは min-jerk の4倍以上進んでいる。
    """
    s, m = Spring(5.0), MinJerk()
    assert s.shape(0.2).position > 4.0 * m.shape(0.2).position

    # ⚠️ 山は u = 1/a の近くに来る（min-jerk は u = 0.5）
    assert s.shape(1.0 / s.sharpness).velocity > 0.9 * s.peak().velocity
    assert m.shape(0.5).velocity > m.shape(0.2).velocity
    assert s.shape(0.5).velocity < s.shape(0.2).velocity


def test_spring_acceleration_is_NOT_zero_at_the_ends():
    """⛔ **#1 の加速度の項で落ちる。** 台形と同じ側である——隠さずに書く。"""
    s = Spring(5.0)
    assert s.shape(0.0).acceleration != 0.0
    assert s.shape(1.0).acceleration != 0.0
    assert s.shape(0.0).acceleration > 0.0  # 始点で最大——**飛び出す**


def test_spring_refuses_a_sharpness_at_or_below_one():
    """⛔ **`a ≤ 1` では補正が形を支配する。** ばねではなくなるので、受け取らない。"""
    for bad in (1.0, 0.5, 0.0, -1.0, math.inf, math.nan):
        with pytest.raises(ValueError):
            Spring(bad)


# --------------------------------------------------------------------------
# #3 可到達性——**正しい軌道が存在しない場合**
# --------------------------------------------------------------------------


def test_trapezoid_segments_vanish():
    """**r=1 で定速区間が消える。** ⚠️ 「消えた」は「無い」ではなく「長さゼロ」である。"""
    t_a, t_c, t_d = segments(Trapezoid(1.0))
    assert (t_a, t_c, t_d) == (0.5, 0.0, 0.5)
    assert Trapezoid(1.0).cruise_vanished is True

    t_a, t_c, t_d = segments(Trapezoid(0.5))
    assert (t_a, t_c, t_d) == pytest.approx((0.25, 0.5, 0.25))
    assert Trapezoid(0.5).cruise_vanished is False


def test_trapezoid_peak_velocity_runs_from_one_to_two():
    """**r=1 で 2（上限）、r→0 で 1。** これが可到達性の幅である。"""
    assert Trapezoid(1.0).velocity_ratio() == pytest.approx(2.0)
    assert Trapezoid(0.001).velocity_ratio() == pytest.approx(1.0, abs=1e-3)


def test_trapezoid_for_velocity_vanishes_and_refuses():
    """⚠️ **届く場合と届かない場合を、別々に言う。**

    `|Δ| = 1`・`d = 1` のとき、最低の最高速度は `1/1 = 1`、上限は `2/1 = 2`。
    """
    _, ok = trapezoid_for_velocity(1.0, 1.0, 10.0)      # 速すぎる → 三角で頭打ち
    assert ok is True
    profile, ok = trapezoid_for_velocity(1.0, 1.0, 10.0)
    assert profile.cruise_vanished is True

    _, ok = trapezoid_for_velocity(1.0, 1.0, 1.5)       # 幅の中
    assert ok is True

    _, ok = trapezoid_for_velocity(1.0, 1.0, 0.5)       # ⛔ 遅すぎる → 届かない
    assert ok is False


def test_min_duration_is_the_strictest_limit_not_a_sum():
    """⚠️ **3つの制限のうち、いちばん厳しいものが決める。** 和でも積でもない。"""
    only_v = min_duration(1.0, 1.0, None, None)
    assert only_v == pytest.approx(1.875)

    both = min_duration(1.0, 1.0, 1.0, None)
    assert both == pytest.approx(math.sqrt(10.0 / math.sqrt(3.0)))  # 加速度が厳しい
    assert both > only_v

    with pytest.raises(ValueError):
        min_duration(1.0, None, None, None)  # ⛔ 制限が1つも無ければ、決まらない


def test_unknown_profile_is_refused():
    with pytest.raises(ValueError):
        profile_of("bounce")  # ⛔ 表現の族は、機体の族ではない


def test_trapezoid_rejects_accel_fraction_out_of_range():
    for bad in (0.0, -0.1, 1.5):
        with pytest.raises(ValueError):
            Trapezoid(bad)
