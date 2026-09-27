# -*- coding: utf-8 -*-
"""機体へ降ろす速度プロファイル——**端の速度がゼロの族だけ**を、ここに置く。

⛔ **ここに在るのは「機体の族」である。表現の族（CSS）は `easing.py` にあり、機体へは通さない。**
根拠は [02_調査/02] §2.3・§9.2——
**Back / Elastic / Bounce は開始時に逆走する。画面では「ため」に見えるが、機体では逆向きの加速度である。**

    正規化してある。変位 1・時間 1 の形だけを持ち、実際の値は呼ぶ側が掛ける。
        position = start + Δ · p(u)
        velocity =        Δ/d · v(u)
        acceleration =    Δ/d² · a(u)
        jerk =            Δ/d³ · j(u)      u = t/d

⚠️ **そして2つは、同じ「機体の族」ではない。**

| | 端の速度 | 端の加速度 | ジャーク |
|---|---|---|---|
| `min-jerk` | **ゼロ** | **ゼロ** | ⚠️ **端でゼロでない**（最大 60） |
| `trapezoid` | **ゼロ** | ⛔ **ゼロでない**（±a） | ⛔ **角で無限大** |

⇒ **`trapezoid` は、[02_調査/02] §9.6 の検査のうち
#1（端の条件）の加速度の項と、#2（制限の非超過）のジャークの項で落ちる。**
**それは隠すものではなく、検査が言うべきことである**（`tests/test_profile.py`）。
⇒ **ゆえに「フォールバック」は、検査を1つ外すことを意味する。** ⚠️ **この実装は、それを黙って外さない。**

⚠️ **ジャークの上限は、ここに無い。** [02_調査/02] §1.4 の
**1.2 m/s³ は ISO 8100-34 への帰属が支持されていない**（同 §8）。**定数として置かない。**
すべて `Limits` として外から渡す。
"""
from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["MinJerk", "Trapezoid", "PROFILES", "profile_of", "segments"]


# --------------------------------------------------------------------------
# 5次多項式（最小ジャーク）
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Shape:
    """1つの標本点の、正規化された位置・速度・加速度・ジャーク。"""

    position: float
    velocity: float
    acceleration: float
    jerk: float


@dataclass(frozen=True)
class MinJerk:
    """5次多項式（最小ジャーク）——**基幹である。**

    出典は Flash & Hogan (1985) の最小ジャーク軌道で、式そのものは
    [02_調査/02] §2.2 が引いている:

        p(u) = 10u³ − 15u⁴ + 6u⁵

    ⚠️ **これは「ヒトの運動のモデル」としてではなく「ヒトが滑らかだと感じる族」として採る**——
    同 §2.2 が生理学的な批判（ヒトは5階微分を知覚できない）を併記している。

    ⚠️ **端でゼロなのは位置・速度・加速度の3つであって、ジャークではない。**
    **ジャークは両端で 60 を取り、中央で −30 を取る**（下の `peak`。導出は `tests/test_profile.py`）。
    """

    name: str = "min-jerk"

    def shape(self, u: float) -> _Shape:
        if not 0.0 <= u <= 1.0:
            raise ValueError(f"u は [0,1] である: {u!r}")
        return _Shape(
            position=u * u * u * (10.0 - 15.0 * u + 6.0 * u * u),
            velocity=30.0 * u * u * (1.0 - u) * (1.0 - u),
            acceleration=60.0 * u * (1.0 - u) * (1.0 - 2.0 * u),
            jerk=60.0 - 360.0 * u + 360.0 * u * u,
        )

    def peak(self) -> _Shape:
        """正規化した最大値。**解析的に決まる**（`tests/test_profile.py` が数値で確かめる）。"""
        return _Shape(
            position=1.0,
            velocity=1.875,  # 30·(1/2)²·(1/2)²
            acceleration=10.0 / math.sqrt(3.0),  # 60·max u(1−u)(1−2u)
            jerk=60.0,  # 両端
        )


# --------------------------------------------------------------------------
# 台形
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Trapezoid:
    """台形速度プロファイル——**「速いが硬い」フォールバックである。**

    ⛔ **これは1つの形ではない。族である。** パラメータは加速度区間の比 `accel_fraction`（r）で、
    区間の長さは正規化時間でこうなる:

        t_a = r/2（加速）・t_c = 1 − r（定速）・t_d = r/2（減速）

    ⚠️ **そして `min-jerk` と違い、この族は尺度不変でない。** `min-jerk` は p(u) が距離と時間に
    よらず1つに決まるが、**台形は r というもう1つの数を持つ。ゆえに「台形で行く」は
    「どの r で行くか」を伴う。**

    **可到達性は、ここで明示的に扱う**（[02_調査/02] §1.2
    「7セグメントは常に7つ揃うわけではない」）:

        r = 1        ⛔ **定速区間が消える**（三角）——正規化した最高速度は 2（上限）
        r → 0        ⛔ **加速区間と減速区間が消える**——加速度が無限大へ向かう
        0 < r < 1    3区間そろう

    ⇒ **要求された最高速度に合う r を解くのが `trapezoid_for_velocity` である。**
    **届かないときは `False` を返す。黙って丸めない。**
    """

    accel_fraction: float = 1.0
    name: str = "trapezoid"

    def __post_init__(self) -> None:
        if not 0.0 < self.accel_fraction <= 1.0:
            raise ValueError(f"accel_fraction は (0,1] である: {self.accel_fraction!r}")

    @property
    def cruise_vanished(self) -> bool:
        """定速区間が消えているか。**r = 1 のとき、長さゼロで「在る」。**"""
        return self.accel_fraction >= 1.0

    def velocity_ratio(self) -> float:
        """正規化した最高速度。**面積が 1 になるように決まる**（`Δ = v_p·(1 − t_a)`）。"""
        return 1.0 / (1.0 - self.accel_fraction / 2.0)

    def peak(self) -> _Shape:
        a = self.acceleration()
        return _Shape(
            position=1.0,
            velocity=self.velocity_ratio(),
            acceleration=a,
            # ⛔ **角が3つある。ジャークはそこで定義されない。**
            jerk=math.inf,
        )

    def acceleration(self) -> float:
        """正規化した加速度の大きさ（加速区間で +a、減速区間で −a）。"""
        return self.velocity_ratio() / (self.accel_fraction / 2.0)

    def shape(self, u: float) -> _Shape:
        if not 0.0 <= u <= 1.0:
            raise ValueError(f"u は [0,1] である: {u!r}")
        r = self.accel_fraction
        t_a = r / 2.0
        a = self.acceleration()
        v_p = self.velocity_ratio()

        # ⛔ **ジャークは角で定義されない。** 0 と答えると、検査が鳴らなくなる。
        corners = (0.0, t_a, 1.0 - t_a, 1.0)
        jerk = math.inf if any(abs(u - c) <= 1e-12 for c in corners) else 0.0

        if u < t_a:
            return _Shape(a * u * u / 2.0, a * u, a, jerk)
        if u <= 1.0 - t_a:
            return _Shape(a * t_a * t_a / 2.0 + v_p * (u - t_a), v_p, 0.0, jerk)
        w = 1.0 - u
        return _Shape(1.0 - a * w * w / 2.0, a * w, -a, jerk)


# --------------------------------------------------------------------------
# 可到達性
# --------------------------------------------------------------------------


def segments(profile) -> tuple[float, float, float]:
    """区間の長さ（正規化時間）を返す——**消えている区間も、長さゼロで返す。**

    ⚠️ **これは台形のためのものである。** `min-jerk` は区間に分かれていない
    （その代わり、どこにも定速区間が無い）。**数える対象を同じ行に書く**——
    「3区間」は台形の話であって、5次多項式の話ではない。
    """
    if isinstance(profile, Trapezoid):
        return (profile.accel_fraction / 2.0, 1.0 - profile.accel_fraction,
                profile.accel_fraction / 2.0)
    return (0.0, 1.0, 0.0)


def min_duration(distance: float, velocity: float | None, acceleration: float | None,
                 jerk: float | None) -> float:
    """`min-jerk` で距離 `distance` を動くのに要る**最短の時間**。

    ⚠️ **3つの制限のうち、いちばん厳しいものが決める**——和でも積でもない
    （[02_調査/02] §4.2）。
    `None` は「その量を制限しない」である。

    ⛔ **ここに既定値は無い。** 制限はすべて外から来る。
    """
    d = abs(distance)
    if d == 0.0:
        return 0.0
    peak = MinJerk().peak()
    candidates = []
    if velocity:
        candidates.append(peak.velocity * d / velocity)
    if acceleration:
        candidates.append(math.sqrt(peak.acceleration * d / acceleration))
    if jerk:
        candidates.append((peak.jerk * d / jerk) ** (1.0 / 3.0))
    if not candidates:
        raise ValueError("制限が1つも無い——最短時間は決まらない")
    return max(candidates)


def trapezoid_for_velocity(distance: float, duration: float,
                           velocity_max: float) -> tuple[Trapezoid, bool]:
    """要求された最高速度に合う台形を返す——**届かなければ `False`。**

    台形の正規化した最高速度は `1/(1 − r/2)` で、**`r → 0` で 1、`r = 1` で 2 である。**
    実速度は `v_p · Δ/d` だから、上限が許す正規化値は `v_max·d/|Δ|` である。

        その値 ≥ 2   ⛔ **定速区間が消える**（r = 1 で頭打ち。**届いてはいる**）
        1 ≤ 値 < 2   r を解く
        値 < 1       ⛔ **届かない**——この時間では、これ以上遅く走れない
                     （両端で速度ゼロの台形の最低速は `|Δ|/d` である）

    ⚠️ **「届かない」を丸めない。** `admit` はこれを見て弾く（`limits.py` の判定と別の入口）。
    ⚠️ **`False` のときも形は返す（`r = 1`）。** **返ってきた形を使わない責任は、呼ぶ側にある**——
    **弾く判断を、黙って `r = 1` に変換しない。**
    """
    d = abs(distance)
    if d == 0.0 or duration <= 0.0:
        return Trapezoid(1.0), True
    ratio = velocity_max * duration / d
    if ratio >= 2.0:
        return Trapezoid(1.0), True
    if ratio < 1.0:
        return Trapezoid(1.0), False
    return Trapezoid(2.0 * (1.0 - 1.0 / ratio)), True


PROFILES = ("min-jerk", "trapezoid")


def profile_of(name: str, **kw):
    """名前からプロファイルを作る。**閉じた族である**（[02_調査/02] §9.1）。"""
    if name == "min-jerk":
        return MinJerk(**kw)
    if name == "trapezoid":
        return Trapezoid(**kw)
    raise ValueError(f"知らないプロファイルである: {name!r}（在るのは {PROFILES}）")
