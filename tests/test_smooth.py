# -*- coding: utf-8 -*-
"""平滑化——**両端を動かさず、単調さを壊さない。**

⚠️ **この2つは、両立しないやり方がある。**
[02_調査/02] §9 の検査には「端の条件」が入っているので、
**平滑化が端を動かせば、それだけで #1 が落ちる。**
そして**平滑化が後退を作れば、機械はその場で1回逆走する。**
"""
from __future__ import annotations

import pytest

from engine.trajectory.profile import MinJerk
from engine.trajectory.smooth import moving_average, smooth, smooth_channels


def _ramp(n=65):
    p = MinJerk()
    return [p.shape(i / (n - 1)).position for i in range(n)]


def test_the_ends_are_untouched():
    values = _ramp()
    out = smooth(values, 3)
    assert out[0] == values[0]
    assert out[-1] == values[-1]


def test_a_monotone_input_stays_monotone():
    """⛔ **平滑化が、後退を作らない。** 400点で確かめる。"""
    values = _ramp()
    out = smooth(values, 5)
    assert all(b >= a for a, b in zip(out, out[1:]))


def test_a_step_becomes_a_ramp():
    """**平滑化が、実際に何かをしているか。** 段差が、坂になる。"""
    step = [0.0] * 5 + [1.0] * 5
    out = smooth(step, 1)
    assert out[0] == 0.0 and out[-1] == 1.0
    assert 0.0 < out[4] < 1.0, "段差がそのまま残っている——平滑化が効いていない"
    assert max(abs(b - a) for a, b in zip(out, out[1:])) < 1.0


def test_a_constant_input_is_unchanged():
    """⚠️ **増分がすべて 0 のとき、倍率が決まらない。** 黙って 1 にしない。"""
    values = [7.0] * 20
    assert smooth(values, 3) == tuple(values)


def test_smoothing_does_not_overshoot_the_range():
    """⚠️ **行き過ぎない。** 単調さが保たれるので、値域の外へ出ない。"""
    values = _ramp()
    out = smooth(values, 4)
    assert min(out) >= min(values)
    assert max(out) <= max(values)


def test_the_naive_moving_average_does_move_the_ends():
    """⛔ **素朴な移動平均は、端を保存しない。** だから `smooth` は別の道を取った。

    ⚠️ **この検査は「なぜそうしたか」を、実行して残すものである。**
    """
    values = _ramp()
    naive = moving_average(values, 3)
    assert naive[0] != values[0]
    assert naive[-1] != values[-1]


def test_half_width_zero_is_the_identity():
    values = _ramp()
    assert smooth(values, 0) == tuple(values)
    assert moving_average(values, 0) == tuple(values)


def test_smooth_channels_works_per_channel():
    a = _ramp(21)
    b = [1.0 - v for v in a]
    out = smooth_channels(list(zip(a, b)), 2)
    assert len(out) == 21
    assert out[0] == (a[0], b[0])
    assert out[-1] == (a[-1], b[-1])
    assert all(y[0] >= x[0] for x, y in zip(out, out[1:]))
    assert all(y[1] <= x[1] for x, y in zip(out, out[1:]))


def test_bad_input_is_refused():
    with pytest.raises(ValueError):
        smooth([1.0, 2.0], -1)
    with pytest.raises(ValueError):
        smooth_channels([(1.0, 2.0), (3.0,)], 1)
