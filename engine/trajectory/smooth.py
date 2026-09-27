# -*- coding: utf-8 -*-
"""平滑化——**両端を動かさず、単調さを壊さない**やり方だけを置く。

⛔ **素朴な「窓を両端で縮める」移動平均は、両端を保存しない**（窓が非対称になるので、
端の値は平均に薄まる）。**そして「端を固定して内側だけ平均する」と、今度は単調さが壊れる**——
実例: `hw=2`・`x = [0,1,1,1,1,1,1]` で `y[1] = 1`（固定）・`y[2] = 0.8`。**平滑化が、後退を作る。**

⇒ **増分を平滑化して、積み直す。** こうすると3つが同時に成り立つ:

    1. **両端が厳密に一致する**——総和を元の総和へ戻すから
    2. **単調な入力は単調な出力になる**——増分が非負のままで、正の一様な倍率しか掛からないから
    3. **定数入力は定数のまま**——増分がすべて 0 で、倍率が定義されないので入力をそのまま返す

⚠️ **これは位置の列に対する平滑化である。** **速度や加速度をここで作り直さない**——
**平滑化した列の微分は、機械的な操作ではなく設計である**（どの差分で測るかを決める行為）。
それを決める場所は、まだこのリポジトリに無い。
"""
from __future__ import annotations

__all__ = ["moving_average", "smooth", "smooth_channels"]


def _average(values: list[float], half_width: int) -> list[float]:
    """対称窓の移動平均。**端では窓を縮める**（この関数だけでは端を保存しない）。"""
    n = len(values)
    out = []
    for i in range(n):
        lo = max(0, i - half_width)
        hi = min(n - 1, i + half_width)
        window = values[lo:hi + 1]
        out.append(sum(window) / len(window))
    return out


def moving_average(values, half_width: int):
    """対称窓の移動平均。⚠️ **端を保存しない。** 保存が要るなら `smooth` を使う。"""
    if half_width < 0:
        raise ValueError(f"half_width は 0 以上である: {half_width!r}")
    values = [float(v) for v in values]
    if half_width == 0 or len(values) < 2:
        return tuple(values)
    return tuple(_average(values, half_width))


def smooth(values, half_width: int):
    """増分を平滑化し、総和を戻して積み直す。**両端が厳密に一致する。**

    `half_width` は増分に掛かる窓の半径である（増分は `len(values) - 1` 個）。
    """
    if half_width < 0:
        raise ValueError(f"half_width は 0 以上である: {half_width!r}")
    values = [float(v) for v in values]
    if half_width == 0 or len(values) < 3:
        return tuple(values)

    deltas = [values[i + 1] - values[i] for i in range(len(values) - 1)]
    smoothed = _average(deltas, half_width)

    total = sum(deltas)
    new_total = sum(smoothed)
    # ⛔ **定数入力（総和 0）では倍率が決まらない。** **黙って 1 にしない**——入力をそのまま返す。
    if new_total == 0.0:
        return tuple(values)
    scale = total / new_total

    out = [values[0]]
    for d in smoothed:
        out.append(out[-1] + d * scale)
    # ⚠️ **最後の1つは、厳密に元の終端へ置く**（浮動小数の足し上げで終端がずれるのを防ぐ）。
    out[-1] = values[-1]
    return tuple(out)


def smooth_channels(samples, half_width: int):
    """標本の列（各標本が同じ長さのタプル）を、**チャネルごとに**平滑化する。"""
    samples = [tuple(float(v) for v in s) for s in samples]
    if not samples:
        return ()
    width = len(samples[0])
    if any(len(s) != width for s in samples):
        raise ValueError("標本ごとにチャネル数が違う")
    columns = [smooth([s[c] for s in samples], half_width) for c in range(width)]
    return tuple(tuple(columns[c][i] for c in range(width)) for i in range(len(samples)))
