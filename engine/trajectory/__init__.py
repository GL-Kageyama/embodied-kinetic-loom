# -*- coding: utf-8 -*-
"""決定論的な核心——**補間・イージング・平滑化・制限。**

⚠️ **このパッケージは LLM を呼ばない。乱数を使わない。時刻を読まない。**
`CLAUDE.md` の「このリポジトリのコードは LLM を呼ばない」は、ここで効いている。
**同じ入力なら、同じビット列が出る。**

    族
      profile.py   機体へ降ろす族——端の速度がゼロのものだけ（min-jerk / 台形）
      easing.py    表現の族——CSS の cubic-bezier。⛔ **機体へは通さない**

    操作
      smooth.py    平滑化——両端を動かさず、単調さを壊さない
      limits.py    制限と、その非超過（軸ごと＋合成）
      plan.py      軌道と標本

    関門
      admit.py     通すか弾くか（**計画時の側だけ。実行時の門はまだ無い**）

⚠️ **そして `plan` という名前は、このパッケージの中で2つを指す。**
**関数 `plan()`（再輸出）と、モジュール `plan.py` である。** **そして再輸出が勝つ。**

⇒ **`from engine.trajectory.plan import plan` は通る**（試験は全部この形である）。
⛔ **だが `import engine.trajectory.plan as m` は、モジュールではなく関数を束縛する**——
**`m.DEFAULT_SAMPLES` は `AttributeError` になる。** **これは実測済みである**（2026-09-27）。
**モジュールが要るなら `from engine.trajectory import plan as m` ではなく、
`from engine.trajectory.plan import DEFAULT_SAMPLES` の形で名指しすること。**
"""
from .admit import Admission, Rejection, admit
from .easing import CURVES, MAPPING_TO_MACHINE, cubic_bezier
from .limits import ChannelLimits, Envelope, Violation, check_targets, check_trajectory
from .plan import Sample, Trajectory, plan
from .profile import MinJerk, Trapezoid, profile_of
from .smooth import moving_average, smooth, smooth_channels

__all__ = [
    "Admission", "Rejection", "admit",
    "CURVES", "MAPPING_TO_MACHINE", "cubic_bezier",
    "ChannelLimits", "Envelope", "Violation", "check_targets", "check_trajectory",
    "Sample", "Trajectory", "plan",
    "MinJerk", "Trapezoid", "profile_of",
    "moving_average", "smooth", "smooth_channels",
]
