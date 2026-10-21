# -*- coding: utf-8 -*-
"""**声。** 間の規則（`render`）と、それを音にする縁（`__main__`）。

⚠️ **ここは音を作らない。** `render` は文字とミリ秒を扱うだけで、
**標本化周波数も、`say` も、マイクも知らない。**
"""
from __future__ import annotations

from .render import PAUSE_MS, gap_frames, segments, spoken

__all__ = ["PAUSE_MS", "gap_frames", "segments", "spoken"]
