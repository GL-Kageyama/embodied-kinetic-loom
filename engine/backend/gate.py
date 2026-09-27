# -*- coding: utf-8 -*-
"""門——**実際に出て行く1フレームを見る。**

⛔ **これが、いままで無かった段である。**
`engine/trajectory/admit.py` は**計画時**に検査する。**だが計画と、出て行くフレームは別物である。**
`README.md` の「まだ無いもの」の1行目が、そのままこのモジュールの仕事である——
**「制限の検査は計画時に走る——実際に出て行くものを門で見る段は、まだ無い。」**

**計画時には見えず、ここでだけ見えるもの:**

| 何 | なぜ計画時に見えないか |
|---|---|
| **1フレームごとの段差** | ⛔ **上流ファームにソフトスタート/ストップが無い**（[02_調査/01] §2.6）。**段差指令は段差のまま入る。** 段差になるかどうかは、**送る時刻の刻みで決まる**——計画は時刻を持たない |
| **送る時刻そのもの** | 計画は軌道の関数であり、`now` を知らない。**門は `now` を受け取る** |
| **モーターの対応** | ⛔ **軸とモーターの対応に正準は無い**（同 §3.3）。**ゆえに門はそれを決めない**——呼ぶ側が `limits_by_motor` として渡す |

⛔ **そして、このモジュールのいちばん重い決定は「拒否の形」である。**

**「送らない」は「止まる」ではない。**
> **送信をやめると、15秒でトルクがおよそ 1/4 になる——そして、モーターは止まらない。**
> **接続が切れたことは、機体が止まったことではない。**（`CLAUDE.md` の安全の節）

⇒ **ゆえに門は、弾いたときに「何も送らない」を返さない。**
**最後に通した組を、そのまま送り続ける**——**それが、止まっている状態にいちばん近い。**
⚠️ **そして、それが「止める」でないことも、同時に真である**——
**この機体に停止コマンドは無い**（同 §2.5）。**門は「止められない」ことを直せない。**
**門にできるのは、悪い1フレームを出さないことだけである。**

⚠️ **判断は「組ごと」である。** 1モーターずつ通すと、
**誰も計画していない組み合わせ**が機体の上に現れる。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..trajectory.limits import ChannelLimits, Envelope, Violation
from .protocol import Frame

__all__ = ["Gate", "Verdict"]


@dataclass(frozen=True)
class Verdict:
    """門の答え。**`frames` は「実際に送ってよいもの」である。**

    ⚠️ **`frames` が空になることは無い**（構築時に初期位置を渡している以上）。
    ⛔ **`held` が真なら、それは「弾いた」ではなく「前の組を保っている」である。**
    """

    allowed: bool
    frames: tuple[Frame, ...]
    violations: tuple[Violation, ...] = ()
    held: bool = False


@dataclass
class Gate:
    """**出て行く1フレームを見る。**

    ⚠️ **`starts_by_motor` は必須である。** 既定値を持たない——
    **初期位置を知らずに最初の1フレームを出すことは、いちばん危ない段差を盲撃ちで送ることである。**
    どこに居るかを知っている側（フィードバック、または利用者）が渡す。

    ⛔ **`Envelope` は写しではなく、`engine/trajectory/limits.py` のものをそのまま受け取る。**
    **同じ数を2箇所に持つと、2つが食い違う。**
    """

    starts_by_motor: tuple[float, ...]
    limits_by_motor: tuple[ChannelLimits, ...]
    envelope: Envelope = field(default_factory=Envelope)
    _last: tuple[Frame, ...] | None = None
    _last_t: float | None = None
    _last_values: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        n = len(self.starts_by_motor)
        if n == 0:
            raise ValueError("モーターが1つも無い")
        if len(self.limits_by_motor) != n:
            raise ValueError(
                f"開始位置が {n} 個、上限が {len(self.limits_by_motor)} 個"
                "——**モーターごとに1つずつ要る**"
            )
        self._last_values = tuple(float(v) for v in self.starts_by_motor)

    def _target_violation(self, motor: int, value: int) -> Violation | None:
        env = self.envelope
        if env.target_min is not None and value < env.target_min:
            return Violation("target", motor, 0.0, float(value), env.target_min)
        if env.target_max is not None and value > env.target_max:
            return Violation("target", motor, 0.0, float(value), env.target_max)
        return None

    def _step_violation(self, motor: int, value: float, elapsed: float) -> Violation | None:
        """⛔ **ここが門の固有の仕事である。**

        **届く速さを超える1フレームは、機体の上では段差になる**——
        ファームに補間が無いので、**段差は段差のまま入る。**

        許す大きさは `velocity_limit × elapsed` である。⚠️ **`elapsed` は実測の刻み**——
        **計画の `duration` ではない。** ここが計画と門の違いである。
        """
        limit = self.limits_by_motor[motor].velocity
        if limit is None:
            return None  # ⚠️ **`None` は「制限しない」である**（`limits.py`）
        allowed = limit * elapsed
        delta = abs(value - self._last_values[motor])
        if delta > allowed:
            return Violation("step", motor, elapsed, delta, allowed)
        return None

    def submit(self, now: float, proposed: tuple[Frame, ...]) -> Verdict:
        """**この組を送ってよいか。** ⛔ **弾いたら、前の組を返す。**

        `now` は呼ぶ側の時計である（`engine/` は `time` を import しない）。
        ⚠️ **単調でなければ落ちる**——**戻る時計の上では、刻みが負になる。**
        """
        if self._last_t is not None and now <= self._last_t:
            raise ValueError(
                f"時計が戻った: {self._last_t} → {now}"
                "——**刻みが負になると、段差の検査が意味を失う**"
            )
        elapsed = 0.0 if self._last_t is None else now - self._last_t

        violations: list[Violation] = []
        seen: set[int] = set()
        for frame in proposed:
            try:
                motor = frame.motor()
            except Exception:
                violations.append(Violation("unknown-command", None, elapsed, 0.0, 0.0))
                continue
            if motor in seen:
                # ⛔ **同じモーターへ2つ送ると、後が勝つ。** それは「計画」ではない。
                violations.append(Violation("duplicate-motor", motor, elapsed, 0.0, 1.0))
                continue
            seen.add(motor)
            if motor >= len(self.starts_by_motor):
                violations.append(Violation("unknown-motor", motor, elapsed, 0.0,
                                            float(len(self.starts_by_motor))))
                continue
            tv = self._target_violation(motor, frame.value)
            if tv is not None:
                violations.append(tv)
                continue
            if self._last_t is not None:
                sv = self._step_violation(motor, float(frame.value), elapsed)
                if sv is not None:
                    violations.append(sv)

        if violations:
            held = self._last if self._last is not None else ()
            # ⛔ **時計だけは進める。** 弾いた回も、保った組を**送っている**からである。
            # ⇒ **次に許す量の基準は、その送信からの経過時間になる。**
            # ⚠️ **値を進めないのは、機体が実際にそこに居るからである**——
            # **拒否された値は、どこにも行っていない。**
            self._last_t = now
            return Verdict(allowed=False, frames=held, violations=tuple(violations), held=True)

        self._last = proposed
        self._last_t = now
        for frame in proposed:
            self._last_values = (
                self._last_values[:frame.motor()]
                + (float(frame.value),)
                + self._last_values[frame.motor() + 1:]
            )
        return Verdict(allowed=True, frames=proposed)

    def hold(self) -> tuple[Frame, ...]:
        """⚠️ **最後に通した組。** まだ1つも通していなければ空である。

        **これは「止める」ではない**——**保つことだけができる**（モジュールを見よ）。
        """
        return self._last if self._last is not None else ()
