# -*- coding: utf-8 -*-
"""**声。** 間の規則（`render`）と、それを音にする縁（`__main__`）。

⚠️ **ここは音を作らない。** `render` は文字とミリ秒を扱うだけで、
**標本化周波数も、`say` も、マイクも知らない。**
"""
from __future__ import annotations

from .render import PITCH, VOICE, PAUSE_MS, gap_frames, pitched, segments, spoken
from .wav import SILENCE, join, trim

__all__ = ["PAUSE_MS", "PITCH", "VOICE", "gap_frames", "pitched", "segments", "spoken",
           "SILENCE", "join", "trim"]
