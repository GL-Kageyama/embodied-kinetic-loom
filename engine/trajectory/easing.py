# -*- coding: utf-8 -*-
"""**表現の族**——CSS の cubic-bezier と、その5つの名前。

⛔ **ここは機体の族ではない。** 機体へ降ろすのは `profile.py` の族だけである。
理由は [02_調査/02] §2.3——
**Back / Elastic / Bounce は開始時に逆走する。** 画面では「ため」に見えるが、
機体では**逆向きの加速度**である。同 §9.2 がそう書いている。

⚠️ **そして「表現の語 → 機体の族」の写像は、存在しない。**
同 §9.2 が自ら「**この写像の設計は存在しない。初稿の提案である**」と書いている。
⇒ **この実装は、その写像を作らない。** 作れば、私が設計したことになる。
⇒ 代わりに `MAPPING_TO_MACHINE` を **`None` のまま置く**——**空欄ではなく、名前のある未決である**
（[08_語彙と日本語] の「語→値」写像と同じ場所である）。
⚠️ **但し 2026-09-28、隣は動いた**——**D-12 と D-02 が決まり、`references/` に表が1行入った。**
⛔ **それでもこの写像は書けない。** **止めているのは決定ではなく、設計が存在しないことである**——
**表の1行は「small forward tilt → pitch」であって、「ease-out → 機体の族」ではない。**

⚠️ **実装してあるのは5つだけである。** `easings.net` の30（10族 × In/Out/InOut）のうち、
**ベジェの数値が同 §2.1 に在るのはこの5つだけ**である。**残り25は、書かない**——
**数値を思い出しで書けば、出典の無い定数が入る**（`CLAUDE.md` の「数を書く前に数える」）。
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = ["CURVES", "cubic_bezier", "curve", "MAPPING_TO_MACHINE"]

#: ⛔ **表現の族 → 機体の族の写像。** **未決である**（[08_語彙と日本語] の「語→値」写像）。
#: `None` は「まだ書いていない」ではなく「**書けない**」である——根拠は上の docstring。
#: ⚠️ **2026-09-28、D-12 と D-02 が決まり `references/` は書かれたが、この行は変わらない。**
MAPPING_TO_MACHINE = None

#: CSS の名前つきベジェ。**数値は [02_調査/02] §2.1 に在るものだけである。**
CURVES = {
    "linear": (0.0, 0.0, 1.0, 1.0),
    "ease": (0.25, 0.1, 0.25, 1.0),
    "ease-in": (0.42, 0.0, 1.0, 1.0),
    "ease-out": (0.0, 0.0, 0.58, 1.0),
    "ease-in-out": (0.42, 0.0, 0.58, 1.0),
}

_BISECTIONS = 64  # ⛔ **固定回数である。** 収束判定にすると、結果が入力の関数でなくなる。


@dataclass(frozen=True)
class _Bezier:
    """3次ベジェ（制御点 P1・P2 だけを持つ。P0=(0,0)・P3=(1,1) に固定）。"""

    x1: float
    y1: float
    x2: float
    y2: float

    def _x(self, t: float) -> float:
        w = 1.0 - t
        return 3.0 * w * w * t * self.x1 + 3.0 * w * t * t * self.x2 + t * t * t

    def _y(self, t: float) -> float:
        w = 1.0 - t
        return 3.0 * w * w * t * self.y1 + 3.0 * w * t * t * self.y2 + t * t * t

    def at(self, u: float) -> float:
        """`u = x` となる媒介変数を二分法で解き、その `y` を返す。

        ⚠️ **二分法の回数を固定してある。** **同じ入力なら、同じビット列が出る**——
        これが「決定論的」の意味である（[02_調査/02] §9.6 の検査 #4）。
        """
        if not 0.0 <= u <= 1.0:
            raise ValueError(f"u は [0,1] である: {u!r}")
        lo, hi = 0.0, 1.0
        for _ in range(_BISECTIONS):
            mid = 0.5 * (lo + hi)
            if self._x(mid) < u:
                lo = mid
            else:
                hi = mid
        return self._y(0.5 * (lo + hi))


def cubic_bezier(x1: float, y1: float, x2: float, y2: float) -> _Bezier:
    """CSS の `cubic-bezier(x1, y1, x2, y2)` と同じ引数。"""
    return _Bezier(x1, y1, x2, y2)


def curve(name: str):
    """名前から曲線を引く。**名前は閉じている。**"""
    if name not in CURVES:
        raise ValueError(f"知らない曲線である: {name!r}（在るのは {sorted(CURVES)}）")
    return cubic_bezier(*CURVES[name])
