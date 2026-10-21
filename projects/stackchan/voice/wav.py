# -*- coding: utf-8 -*-
"""**断片をつなぐ。** ⚠️ **設計 §22.3 が選んだ形は、これである。**

⛔ **`say` に `[[slnc N]]` を上乗せしてはならない。** `say` は句読点に自分で間を入れるので、
**規則が二重に効き、上乗せの分は文によって揺れる**——実測で 600 ms のつもりが 816.3 ms。

⇒ **断片ごとに合成し、端の無音を切り、規則どおりの無音でつなぐ。**
**間は文の性質ではなく、記号の性質になる**（`render.PAUSE_MS`）。

⚠️ **閾値は 200（16ビット、全振幅 32768）。** `検証/voice_pauses.py` と同じ切り方である——
**測る道具と作る道具が違う切り方を持てば、数は合わない。**
"""
from __future__ import annotations

from .render import gap_frames

#: ⚠️ **これを動かせば、間の実測も動く。** `検証/voice_pauses.py` の `THRESHOLD` と同じ値。
SILENCE = 200


def trim(samples: list[int], threshold: int = SILENCE) -> list[int]:
    """**端の無音を落とす。** ⛔ **中の無音は落とさない**——それは語と語の間である。

    ⚠️ **全部が閾値より静かなら、空を返す。** 無音を「間」として数えないためである。
    """
    head, tail = 0, len(samples)
    while head < tail and abs(samples[head]) < threshold:
        head += 1
    while tail > head and abs(samples[tail - 1]) < threshold:
        tail -= 1
    return samples[head:tail]


def join(parts: list[list[int]], pauses: list[int], rate: int) -> list[int]:
    """**断片を、規則どおりの無音でつなぐ。**

    ⛔ **`pauses` の長さは `parts` と同じでなければならない。** 足りない分を 0 で埋めれば、
    **足りないことは黙って「間なし」になる**——それは規則の不在であり、既定ではない。
    """
    if len(parts) != len(pauses):
        raise ValueError(f"断片 {len(parts)} に間 {len(pauses)}")
    out: list[int] = []
    for part, pause in zip(parts, pauses):
        out.extend(part)
        out.extend([0] * gap_frames(pause, rate))
    return out


__all__ = ["SILENCE", "trim", "join"]
