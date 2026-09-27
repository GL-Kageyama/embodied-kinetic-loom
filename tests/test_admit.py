# -*- coding: utf-8 -*-
"""検査 #5（Safety の拒否）——**通すか、弾くか。**

⛔ **このファイルの中心は `test_the_fallback_needs_one_check_turned_off` である。**
計画は台形を「フォールバック」として残すと書いている（[02_調査/02] §9.1）。
**だが台形は、角でジャークが定義されない。**
⇒ **台形を選ぶことは、#2 のジャークの項を外すことである。**
**ここに書いておかないと、その1つは黙って外れる。**
"""
from __future__ import annotations

import pytest

from engine.intent import load
from engine.trajectory.admit import Admission, Rejection, admit
from engine.trajectory.limits import ChannelLimits, Envelope
from engine.trajectory.profile import Trapezoid


def _intent(*moves):
    base = {"dof": "pitch", "target": 512, "duration_ms": 800, "group": 0}
    out = []
    for m in moves or ({},):
        merged = dict(base)
        merged.update(m)
        out.append(merged)
    return load({"moves": out})


GENEROUS = ChannelLimits(velocity=1000.0, acceleration=5000.0, jerk=100000.0)


# --------------------------------------------------------------------------
# 通る
# --------------------------------------------------------------------------


def test_a_move_inside_the_limits_is_admitted():
    result = admit(_intent(), {"pitch": 400.0}, {"pitch": GENEROUS})
    assert isinstance(result, Admission)
    assert len(result.trajectories) == 1
    assert result.trajectories[0].labels == ("pitch",)


def test_one_trajectory_per_group():
    result = admit(
        _intent({"group": 0}, {"dof": "roll", "target": 600, "group": 0},
                {"dof": "yaw", "target": 500, "duration_ms": 300, "group": 1}),
        {"pitch": 400.0, "roll": 500.0, "yaw": 500.0},
        {"pitch": GENEROUS, "roll": GENEROUS, "yaw": GENEROUS},
    )
    assert isinstance(result, Admission)
    assert len(result.trajectories) == 2
    assert result.trajectories[0].labels == ("pitch", "roll")
    assert result.trajectories[1].duration == 0.3


def test_an_axis_that_does_not_move_does_not_break_anything():
    """⚠️ **動かない軸も、組には入っている。** ジャークの `inf` に潰されないこと。"""
    result = admit(
        _intent({"group": 0}, {"dof": "roll", "target": 500, "group": 0}),
        {"pitch": 400.0, "roll": 500.0},
        {"pitch": GENEROUS, "roll": GENEROUS},
    )
    assert isinstance(result, Admission)
    assert {s.jerk[1] for s in result.trajectories[0].samples} == {0.0}


def test_admitting_twice_gives_the_same_trajectory():
    """**関門も決定論的である。**"""
    args = (_intent(), {"pitch": 400.0}, {"pitch": GENEROUS})
    assert admit(*args).trajectories[0].samples == admit(*args).trajectories[0].samples


# --------------------------------------------------------------------------
# ⛔ 弾く
# --------------------------------------------------------------------------


def test_an_unknown_degree_of_freedom_is_refused():
    result = admit(_intent({"dof": "roll"}), {"pitch": 400.0}, {"pitch": GENEROUS})
    assert isinstance(result, Rejection)
    assert "現在位置" in result.reason or "上限" in result.reason


def test_a_target_outside_the_clip_range_is_refused():
    """⚠️ **箱は、既定で 190〜833 しか受け取らない**（[02_調査/01] §2.2）。

    ⛔ **そして、これは「機械の限界」ではない。** 外すのは著者の判断である。
    """
    result = admit(_intent({"target": 900}), {"pitch": 400.0}, {"pitch": GENEROUS})
    assert isinstance(result, Rejection)
    assert result.reason == "目標が枠の外である"
    assert result.violations[0].kind == "target"

    # ⚠️ **枠を外しても、制限は残る。** 900 へ 0.8 秒で行くには 1172 出る。
    # ⇒ **「枠を外した」と「制限を外した」は別である。** 外すのは著者の判断である。
    opened = Envelope(target_min=None, target_max=None)
    still_limited = admit(_intent({"target": 900}), {"pitch": 400.0},
                          {"pitch": ChannelLimits(velocity=1000.0)}, envelope=opened)
    assert isinstance(still_limited, Rejection)
    assert still_limited.reason == "軌道が上限を超える"

    assert isinstance(
        admit(_intent({"target": 900}), {"pitch": 400.0},
              {"pitch": ChannelLimits(velocity=5000.0, acceleration=50000.0, jerk=1000000.0)},
              envelope=opened),
        Admission,
    )


def test_a_trajectory_that_exceeds_its_limit_is_refused():
    tight = ChannelLimits(velocity=100.0)  # 262.5 出るので超える
    result = admit(_intent(), {"pitch": 400.0}, {"pitch": tight})
    assert isinstance(result, Rejection)
    assert result.reason == "軌道が上限を超える"
    assert any(v.kind == "velocity" for v in result.violations)


def test_too_short_a_time_is_refused_by_the_limits_not_by_a_special_case():
    """⚠️ **「短すぎる」という特別扱いを作らない。** 制限が捕まえる。"""
    result = admit(_intent({"duration_ms": 20}), {"pitch": 400.0}, {"pitch": GENEROUS})
    assert isinstance(result, Rejection)
    assert result.reason == "軌道が上限を超える"


# --------------------------------------------------------------------------
# ⛔ 台形——フォールバックは、検査を1つ外す
# --------------------------------------------------------------------------


def test_the_fallback_needs_one_check_turned_off():
    """⛔ **台形は、ジャークの上限が在ると必ず落ちる。** 角で `inf` だからである。

    ⚠️ **「速いが硬い」の「硬い」は、形容ではない。** 実行するとこうなる。
    """
    with_jerk = admit(_intent(), {"pitch": 400.0}, {"pitch": GENEROUS},
                      profile=Trapezoid(0.5))
    assert isinstance(with_jerk, Rejection)
    assert any(v.kind == "jerk" for v in with_jerk.violations)

    without_jerk = admit(
        _intent(), {"pitch": 400.0},
        {"pitch": ChannelLimits(velocity=1000.0, acceleration=5000.0)},
        profile=Trapezoid(0.5),
    )
    assert isinstance(without_jerk, Admission)


def test_reachability_refuses_when_no_trapezoid_can_honour_the_limit():
    """⚠️ **検査 #3 は「超えた」ではなく「族に無い」と言う。**

    `|Δ| = 112`・`d = 0.8` なので、台形の最高速度は **どの r でも 140 以上**である。
    ⇒ 上限 100 は、**族のどこにも無い。**
    """
    result = admit(_intent(), {"pitch": 400.0},
                   {"pitch": ChannelLimits(velocity=100.0, acceleration=5000.0)},
                   profile=Trapezoid(0.5))
    assert isinstance(result, Rejection)
    assert "可到達性" in result.reason


def test_reachability_is_quiet_when_the_limit_is_above_the_floor():
    """⚠️ **下限より上なら、族に在る。** 鳴りっぱなしの検査にしない。"""
    result = admit(_intent(), {"pitch": 400.0},
                   {"pitch": ChannelLimits(velocity=200.0, acceleration=5000.0)},
                   profile=Trapezoid(0.5))
    assert isinstance(result, Admission)


def test_the_reachability_check_only_runs_for_the_trapezoid():
    """⚠️ **min-jerk は族が1つなので、この問いが立たない。**（`r` が無い）"""
    result = admit(_intent(), {"pitch": 400.0},
                   {"pitch": ChannelLimits(velocity=100.0, acceleration=5000.0)})
    assert isinstance(result, Rejection)
    assert result.reason == "軌道が上限を超える"  # ← #3 ではなく #4 が捕まえている
