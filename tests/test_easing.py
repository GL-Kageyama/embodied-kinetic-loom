# -*- coding: utf-8 -*-
"""**表現の族は、機体へ通さない。**

⛔ このファイルの仕事は、[02_調査/02] §2.3・§9.2 の分離が**コードの上で成り立っていること**を
確かめることである——**族が2つ在り、その間の写像が無い。**
"""
from __future__ import annotations

import pytest

from engine.trajectory import easing
from engine.trajectory.easing import CURVES, cubic_bezier, curve
from engine.trajectory.profile import PROFILES, MinJerk, Trapezoid, profile_of


def test_the_five_curves_are_the_ones_with_published_numbers():
    """⚠️ **数値の出典は [02_調査/02] §2.1 だけである。** 30族のうち、数値が在るのは5つ。

    ⚠️ **数を足すなら、出典を足すこと。** 思い出しで書けば、出典の無い定数が入る。
    """
    assert set(CURVES) == {"linear", "ease", "ease-in", "ease-out", "ease-in-out"}
    assert CURVES["linear"] == (0.0, 0.0, 1.0, 1.0)
    assert CURVES["ease"] == (0.25, 0.1, 0.25, 1.0)
    assert CURVES["ease-in"] == (0.42, 0.0, 1.0, 1.0)
    assert CURVES["ease-out"] == (0.0, 0.0, 0.58, 1.0)
    assert CURVES["ease-in-out"] == (0.42, 0.0, 0.58, 1.0)


def test_every_curve_starts_at_zero_and_ends_at_one():
    for name in CURVES:
        c = curve(name)
        assert c.at(0.0) == pytest.approx(0.0, abs=1e-9), name
        assert c.at(1.0) == pytest.approx(1.0, abs=1e-9), name


def test_the_evaluator_is_deterministic():
    """⚠️ **二分法の回数を固定してある。** 収束判定にすれば、結果が入力の関数でなくなる。"""
    c = cubic_bezier(0.25, 0.1, 0.25, 1.0)
    first = [c.at(i / 100) for i in range(101)]
    second = [c.at(i / 100) for i in range(101)]
    assert first == second


def test_linear_is_the_identity():
    c = cubic_bezier(*CURVES["linear"])
    for i in range(11):
        assert c.at(i / 10) == pytest.approx(i / 10, abs=1e-6)


def test_ease_in_out_is_slow_at_both_ends():
    """⚠️ **5つのうち、両端で勾配がゼロなのはこれだけである。** 実行して確かめる。

    ⛔ **だが、それでも機体の族ではない。** 曲線であって速度プロファイルではなく、
    **端で加速度がゼロとは限らない**（`profile.MinJerk` はそこまで保証する）。
    """
    c = curve("ease-in-out")
    near_start = (c.at(0.01) - c.at(0.0)) / 0.01
    middle = (c.at(0.51) - c.at(0.50)) / 0.01
    near_end = (c.at(1.0) - c.at(0.99)) / 0.01
    assert near_start < middle
    assert near_end < middle
    assert min(near_start, near_end) < 0.2 * middle  # ほぼゼロ


def test_the_machine_family_does_not_contain_a_screen_curve():
    """⛔ **`bounce` も `elastic` も、機体の族ではない。** 名前で弾かれる。"""
    assert PROFILES == ("min-jerk", "trapezoid")
    for name in ("bounce", "elastic", "back", "ease-in-out", "ease"):
        with pytest.raises(ValueError):
            profile_of(name)


def test_the_two_families_live_in_two_modules():
    """⚠️ **分離は、名前の付け方ではなくファイルの分け方である。**

    `easing` はプロファイルを1つも持たず、`profile` は曲線を1つも持たない。
    """
    assert not hasattr(easing, "MinJerk")
    assert not hasattr(easing, "Trapezoid")
    assert not hasattr(MinJerk, "cubic_bezier")
    assert Trapezoid.__module__.endswith("profile")


def test_the_mapping_to_the_machine_does_not_exist():
    """⛔ **写像は `None` である。** 「まだ書いていない」ではなく「書けない」。

    [02_調査/02] §9.2 が自ら「**この写像の設計は存在しない。初稿の提案である**」と書いている。
    ⚠️ **この検査は、写像が書かれた日に赤くなる**——そしてその日は、
    **`references/` の「語→値」写像（D-02 / D-12）が閉じた日**である。
    **赤くなること自体が合図である**: この検査を書き換える人は、そのとき何を決めたかを書く。
    """
    assert easing.MAPPING_TO_MACHINE is None
