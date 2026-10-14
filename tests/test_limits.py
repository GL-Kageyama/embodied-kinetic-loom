# -*- coding: utf-8 -*-
"""検査 #2（制限の非超過）——**軸ごとに見て、終わりにしない。**

⛔ **このファイルの中心は `test_composite_is_exceeded_while_every_axis_is_inside` である。**
[02_調査/02] §4.2 の逐語——**「各軸をクランプすれば安全」は成り立たない。**
"""
from __future__ import annotations

import ast
import math
from pathlib import Path

import pytest

from engine.backend.protocol import DOF_REALITY_ENVELOPE
from engine.trajectory.limits import (
    ChannelLimits, Envelope, check_targets, check_trajectory,
)
from engine.trajectory.plan import Sample, Trajectory, plan

# min-jerk の正規化した最高速度。**この1つの数が、下の計算の全部に効く。**
V_PEAK = 1.875

#: ⚠️ **枠を外した枠である。** `None` は「無い」ではなく「外した」である——
#: **ゆえにこれも、書いた者の判断が1行に残る形である**（`limits.py` を見よ）。
_OPEN = Envelope(None, None)


def _trajectory(distance, *, duration=1.0, channels=2, **kw):
    starts = tuple(0.0 for _ in range(channels))
    ends = tuple(distance for _ in range(channels))
    return plan(starts, ends, duration, **kw)


# --------------------------------------------------------------------------
# ⛔ 合成——ここが本体である
# --------------------------------------------------------------------------


def test_composite_is_exceeded_while_every_axis_is_inside():
    """**各軸は上限の 0.8 ずつ。それでも合成は 1.13 で、超える。**

    `0.8² + 0.8² = 1.28`、`√1.28 = 1.131`。
    ⚠️ **軸ごとの検査は、ここで1つも鳴らない。**
    """
    distance = 0.8 * 1.0 / V_PEAK          # 各軸の最高速度をちょうど 0.8 にする
    traj = _trajectory(distance, channels=2)
    limits = (ChannelLimits(velocity=1.0), ChannelLimits(velocity=1.0))

    violations = check_trajectory(traj, limits, _OPEN)
    kinds = {v.kind for v in violations}

    assert "velocity" not in kinds, "軸ごとの検査が鳴ってしまった——この検査の主旨が消える"
    assert "composite-velocity" in kinds

    composite = [v for v in violations if v.kind == "composite-velocity"]
    # ⚠️ **`composite[0]` は「最初に超えた標本」であって、山ではない。**
    # 山は真ん中にあり、端では 0 から立ち上がる。
    assert max(v.value for v in composite) == pytest.approx(math.sqrt(1.28), rel=1e-4)
    assert composite[0].limit == 1.0
    assert composite[0].channel is None, "合成の違反は、1つの軸のせいにできない"
    assert composite[0].t < 0.5 < composite[-1].t, "超えているのは真ん中の区間である"


def test_composite_does_not_fire_when_the_axes_are_small_enough():
    """⚠️ **鳴りっぱなしの検査は、検査ではない。** 0.5 ずつなら `√0.5 = 0.707` で通る。"""
    distance = 0.5 / V_PEAK
    traj = _trajectory(distance, channels=2)
    limits = (ChannelLimits(velocity=1.0), ChannelLimits(velocity=1.0))
    violations = check_trajectory(traj, limits, _OPEN)
    assert violations == ()


def test_composite_needs_two_channels():
    """**1軸では合成は定義されない。** 半径が1つの楕円は、ただの区間である。"""
    distance = 0.99 / V_PEAK
    traj = _trajectory(distance, channels=1)
    violations = check_trajectory(traj, (ChannelLimits(velocity=1.0),),
                                  _OPEN)
    assert violations == ()


def test_composite_can_be_turned_off():
    """⚠️ **切れる。だが切ったことは、呼んだ側の記録に残らない。**（`Envelope` を見よ）"""
    distance = 0.8 / V_PEAK
    traj = _trajectory(distance, channels=2)
    limits = (ChannelLimits(velocity=1.0), ChannelLimits(velocity=1.0))
    off = check_trajectory(traj, limits,
                           Envelope(None, None, composite=False))
    assert off == ()


# --------------------------------------------------------------------------
# 軸ごと
# --------------------------------------------------------------------------


def test_a_single_axis_over_its_limit_fires_with_a_time():
    distance = 1.2 / V_PEAK
    traj = _trajectory(distance, channels=2)
    limits = (ChannelLimits(velocity=1.0), ChannelLimits(velocity=1.0))
    violations = check_trajectory(traj, limits, _OPEN)
    single = [v for v in violations if v.kind == "velocity"]
    assert single, "軸ごとの違反が鳴っていない"
    assert all(0.0 <= v.t <= 1.0 for v in single), "時刻を持っていない違反は、直せない"
    assert all(v.channel in (0, 1) for v in single)


def test_an_unlimited_quantity_is_not_checked():
    """⚠️ **`None` は「制限しない」である。** 既定値で埋めない。"""
    traj = _trajectory(5.0, channels=1)
    assert check_trajectory(traj, (ChannelLimits(),),
                            _OPEN) == ()


def test_the_limit_count_must_match_the_channel_count():
    traj = _trajectory(1.0, channels=2)
    with pytest.raises(ValueError):
        check_trajectory(traj, (ChannelLimits(velocity=1.0),), _OPEN)


# --------------------------------------------------------------------------
# 枠（目標の範囲）
# --------------------------------------------------------------------------


def test_the_envelope_holds_no_numbers_of_its_own():
    """⛔ **`Envelope` は、数を1つも持たない**（2026-10-15）。

    ⚠️ **かつては `190.0` / `833.0` が既定値であった。**
    ⛔ **削除した理由は「機械が2台になったから」である**——
    **既定値は、どの機体の数かを言えない。**
    ⇒ **ここで見ているのは、その既定が消えたことである。**
    """
    with pytest.raises(TypeError):
        Envelope()
    with pytest.raises(TypeError):
        Envelope(target_min=190.0)
    assert Envelope(None, None).target_min is None


def test_the_vendor_clip_range_is_named_once_and_passed_by_name():
    """✅ **190〜833 は実測である**（[02_調査/01] §2.2）。**機械の限界ではない。**

    ⚠️ **消えたのは数ではなく、既定である**——
    **いまは `DOF_REALITY_ENVELOPE` という名前を持ち、門と `admit` へ名前で渡される。**
    """
    e = DOF_REALITY_ENVELOPE
    assert (e.target_min, e.target_max) == (190.0, 833.0)
    assert check_targets((190.0, 833.0, 500.0), e) == ()
    assert len(check_targets((189.0,), e)) == 1
    assert len(check_targets((834.0,), e)) == 1


def _counted_envelopes() -> list[str]:
    """⚠️ **数を書いてある `Envelope(...)` を、`engine/` から全部拾う。**

    ⛔ **原文を探さない。** `Envelope(` は散文にも現れる——
    **AST で、実際に数を渡している呼び出しだけを見る**（`tools/purity.py` と同じ理由）。
    """
    root = Path(__file__).resolve().parents[1] / "engine"
    out = []
    for path in sorted(root.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text("utf-8"))):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "Envelope"):
                continue
            given = list(node.args) + [kw.value for kw in node.keywords]
            if any(isinstance(a, ast.Constant) and isinstance(a.value, (int, float))
                   and not isinstance(a.value, bool) for a in given):
                out.append(f"{path.relative_to(root).as_posix()}:{node.lineno}")
    return out


def test_the_envelope_numbers_live_in_one_file():
    """⛔ **枠の数が書いてある場所は、1つでなければならない。**

    **同じ数を2箇所に持つと、2つが食い違う**（`protocol.py` の docstring）。
    ⚠️ **`engine/` の中で数を書いて `Envelope` を組んでよいのは、機体1の定義だけである。**

    ⚠️ **行番号は主張しない。** 数えるのは**場所と回数**である——
    **行番号を書けば、その上の1行を直すたびに、この検査が別の理由で赤くなる。**
    """
    built = _counted_envelopes()
    where = {b.split(":")[0] for b in built}
    assert where == {"backend/protocol.py"}, (
        f"⛔ **枠の数が散っている: {built}**"
        "——**門も `admit` も `Rig` も、名前で受け取るだけである**"
    )
    assert len(built) == 1, (
        f"⛔ **枠の数が2箇所に書いてある: {built}**——**片方だけが直る形である**"
    )


def test_envelope_can_be_opened_explicitly():
    """⛔ **外すのは著者の判断である。** `None` は「無い」ではなく「外した」である。"""
    e = _OPEN
    assert check_targets((-1e9, 1e9), e) == ()


def test_targets_are_checked_even_when_the_move_is_a_no_op():
    """**動かない move でも、行き先が枠の外なら弾く。**"""
    assert len(check_targets((0.0,), DOF_REALITY_ENVELOPE)) == 1


# --------------------------------------------------------------------------
# ⛔ nan は、通さない
# --------------------------------------------------------------------------


def test_a_nan_does_not_slip_through_the_limit_check():
    """⛔ **`nan > limit` は `False` である。** 比較に任せれば、`nan` は静かに通る。

    ⚠️ **`plan` は `nan` を作らない**（`plan.py` の `_scale`）。だが**この検査は、
    手で組まれた軌道にも当たる**——そして**空の検査は OK と言う**ので、
    **鳴ることを、ここで1回鳴らしておく。**
    """
    traj = plan((0.0,), (1.0,), 1.0, count=3)
    poisoned = Trajectory(
        duration=traj.duration, starts=traj.starts, ends=traj.ends,
        profile=traj.profile, labels=traj.labels,
        samples=tuple(
            Sample(t=s.t, position=s.position, velocity=(float("nan"),),
                   acceleration=s.acceleration, jerk=s.jerk)
            for s in traj.samples
        ),
    )
    violations = check_trajectory(poisoned, (ChannelLimits(velocity=1e9),), _OPEN)
    assert violations, "nan が検査を通り抜けた"
    assert all(math.isnan(v.value) for v in violations if v.kind == "velocity")
