# -*- coding: utf-8 -*-
"""軸の対応——⛔ **このリポジトリは、これを決めない。**

⛔ **このファイルの中心は `test_the_axis_map_will_not_be_built_empty` である。**

**空欄は中立ではない**（`CLAUDE.md` の文書規則）。**既定値を置けば、
誰かがそれを配線の事実として使う**——そしてこの値は、**実機の上でしか測れない。**

⚠️ **このファイルが緑であることは、「対応が正しい」を1つも意味しない。**
**意味するのは「対応を書かずに走らせる道が無い」ことだけである。**
"""
from __future__ import annotations

import pytest

from engine.backend.axis_map import AxisMap, AxisMapError, ChannelCalibration

PITCH = ChannelCalibration(motor=0, sign=1, offset=0.0, scale=1.0)


def test_a_calibration_maps_a_value_to_counts():
    cal = ChannelCalibration(motor=1, sign=-1, offset=500.0, scale=2.0)
    assert cal.to_counts(10.0) == 480.0  # 500 + (−1)(2)(10)


def test_to_counts_does_not_round():
    """⚠️ **丸めるのは門の手前である**（`transmit.py` を見よ）。**ここで丸めると、
    門が見る値と、送る値が別になる。**"""
    assert ChannelCalibration(0, 1, 0.0, 0.5).to_counts(3.0) == 1.5


def test_the_sign_is_only_plus_or_minus_one():
    """⛔ **符号は配線依存である**（[02_調査/01] §3.4）。**0 や 0.5 は符号ではない。**"""
    for bad in (0, 2, 0.5, -0.5, 1.5):
        with pytest.raises(AxisMapError, match="符号"):
            ChannelCalibration(motor=0, sign=bad, offset=0.0, scale=1.0)
    # ⚠️ **`-1.0` は通る**——数として `-1` と同じである。**型ではなく値を検査している。**


def test_a_scale_of_zero_is_refused():
    """⛔ **角度から計算する式は無い**（同 §5.1「原理的に書けない」）。**0 はその放棄である。**"""
    with pytest.raises(AxisMapError, match="動かない自由度"):
        ChannelCalibration(motor=0, sign=1, offset=0.0, scale=0.0)


def test_a_negative_motor_is_refused():
    with pytest.raises(AxisMapError, match="モーターが負"):
        ChannelCalibration(motor=-1, sign=1, offset=0.0, scale=1.0)


# --------------------------------------------------------------------------
# ⛔ 空の対応を作れない
# --------------------------------------------------------------------------


def test_the_axis_map_will_not_be_built_empty():
    """⛔ **ここが中心である。既定の対応は存在しない**（同 §3.3）。"""
    with pytest.raises(AxisMapError, match="正準の対応は存在しない"):
        AxisMap(channels={})


def test_two_degrees_of_freedom_on_one_motor_is_refused():
    """⛔ **同じモーターへ2つ送ると、後が勝つ。** それは計画ではない。"""
    with pytest.raises(AxisMapError, match="後が勝つ"):
        AxisMap(channels={
            "pitch": ChannelCalibration(0, 1, 0.0, 1.0),
            "roll": ChannelCalibration(0, 1, 0.0, 1.0),
        })


def test_an_unknown_degree_of_freedom_is_refused():
    """⚠️ **`pitch`/`roll`/`yaw` は、このリポジトリの名札である。機体の軸ではない。**"""
    with pytest.raises(AxisMapError, match="名札"):
        AxisMap(channels={"pitch": PITCH}).to_counts("yaw", 0.0)


def test_the_mapping_is_a_lookup_not_a_guess():
    amap = AxisMap(channels={
        "pitch": ChannelCalibration(0, 1, 0.0, 1.0),
        "roll": ChannelCalibration(1, -1, 833.0, 1.0),
    })
    assert amap.to_counts("pitch", 100.0) == 100.0
    assert amap.to_counts("roll", 100.0) == 733.0
    assert amap.channels["roll"].motor == 1
