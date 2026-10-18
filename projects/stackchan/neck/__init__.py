# -*- coding: utf-8 -*-
"""**首の動き。** エンジンの軌道から、機体2へ送る姿勢の列を作る。

⚠️ **この包みは数を1つも持たない**——始点と終点は呼ぶ側が名指しし、
刻みと長さは呼ぶ側のものである。`motion.py` が純粋な半分、`__main__.py` が縁である。
"""
from __future__ import annotations

from .motion import Motion, Step, motion

__all__ = ["Motion", "Step", "motion"]
