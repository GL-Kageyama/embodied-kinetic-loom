# -*- coding: utf-8 -*-
"""**首の動き。** エンジンの軌道から、機体2へ送る姿勢の列を作る。

⚠️ **`motion.py` が純粋な半分である**——両端と長さは呼ぶ側が名指しし、
**このファイル自身は数を1つも持たない**。`__main__.py` が縁である。
⚠️ **`gestures.py` は五つの姿勢の写しを持つ**（正本は基板であり、写しは検査で留める）。
**`stream.py` は列を期限で1行ずつ出す**——縁とデーモンが同じ規則で追うためである。
"""
from __future__ import annotations

from .motion import Motion, Step, chain, motion

__all__ = ["Motion", "Step", "motion", "chain"]
