# -*- coding: utf-8 -*-
"""送信——**軌道を、実際の時刻で引く。**

⛔ **ここに、このパッケージでいちばん見落としやすい1点がある。**

`Trajectory.at(t)` は**補間しない**——標本点でなければ `ValueError` を投げる（意図である）。
⚠️ **だが、周期ループの `now` は標本点に落ちない。** 遅れるからである。

⇒ **ゆえにここは、標本点で引くのでなく、`now` にいちばん近い標本を選ぶ。**

⛔ **どちらを選ぶかは、機体の上で意味が違う。**

| 選び方 | 遅れた刻みで何が起きるか |
|---|---|
| **標本を1つずつ進める**（時刻を無視） | ⛔ **軌道がゆっくりになる。** 5秒の動作が、遅れたぶんだけ長くかかる |
| **`now` にいちばん近い標本**（ここ） | ✅ **壁時計に追従する。** 遅れた刻みは**標本を飛ばす**——**そして、その段差は門が捕まえる** |

⇒ **門（`gate.py`）と、この選択は組で効く。**
**遅れは消せない。だが「遅れたときに何が機体へ行くか」は選べる。**

⚠️ **そして `stale_by` は、その選び方の代償を記録する**——
**送った値が、どの時刻の値なのか。** 0 ならちょうど、正なら遅れている。
**この数は Mock では意味を持たない。実機でだけ意味を持つ。**

## ⛔ この層は、機体の名前を1つも書かない（2026-10-15）

**かつては書いていた**——`encode_target` を呼び、`Frame` を組み、`ProtocolError` を捕まえていた。
⇒ **いまは `Wire` の3つのメソッドだけを呼ぶ**（`wire.py`）。
**機体1の5バイトも、機体2の1行2軸も、ここには現れない。**

⚠️ **そして、この層の順序そのものが機体非依存である:**

    軸ごとの値 → 電線で丸める → 門 → 電線でバイト列にする
                 ⛔ 門の手前           ⛔ 門の後ろ

⛔ **左の丸めを門の後ろへ動かしてはならない。** 門は通した値で時計と位置を進めるので、
**後ろで落ちると、落ちた組のぶんだけ門が先へ進んでいる**（`gate.py` の `submit` を見よ）。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..trajectory.plan import Trajectory
from .axis_map import AxisMap
from .gate import Gate, Verdict
from .wire import Command, Wire

__all__ = ["FrameSet", "Transmitter"]


@dataclass(frozen=True)
class FrameSet:
    """**1刻みぶんの、実際に送るもの。**

    ⚠️ **名前は機体1の語である**（1モーター1フレーム）。**この型は、もうフレームを持たない**——
    持つのは組（`verdict.commands`）と、その組から出たバイト列（`payload`）である。
    ⛔ **この段では改名しない。** **2台目の電線が着地して初めて、
    一般的な形が「何と呼ばれるべきか」が分かる**——
    **1台しか見ていないうちに付けた名は、2台目で必ず足りなくなる。**
    """

    verdict: Verdict
    sample_t: float   # ⚠️ **送った値が対応する軌道の時刻**
    at: float         # ⚠️ **それを送ろうとした壁時計の時刻**
    stale_by: float   # `at - sample_t`。**0 が理想。正なら遅れている**
    #: ⛔ **この刻みで、実際に電線へ流れるバイト列。** **門を通った後の値から組まれる**——
    #: ゆえに**弾かれた刻みでも空にならない**（`gate.py` を見よ）。
    #: ⚠️ **既定値を持たない。** **空のバイト列は「何も送らない」という主張である**——
    #: **それが無害な刻みは、このエンジンには1つも無い**（`CLAUDE.md` の安全の節）。
    payload: bytes


@dataclass
class Transmitter:
    """⚠️ **1つの軌道に1つ。** 組（`group`）を跨ぐのは呼ぶ側の仕事である。

    **`admit` は組ごとに1つの軌道を返す**（`engine/trajectory/admit.py`）——
    **ゆえに組の数だけ、これを順に走らせる。**

    ⛔ **`wire` は、門のものと同じでなければならない。** 組めなければ落ちる——
    ⚠️ **門に機体1の電線を挿し、ここに機体2の電線を挿すと、
    門が機体1の数え方で丸めた値を、機体2の言葉で書くことになる。**
    **それは2台ぶんの誤りが、1台の上で静かに混ざる形である。**
    ⇒ **ゆえにここで照合する**——**「気をつける」ではなく、組めなくする。**
    ⚠️ **門は `wire` を必須で持っているので、写しを渡す必要は無い**——
    **それでも欄にしているのは、この照合を書くためである。**
    """

    trajectory: Trajectory
    axis_map: AxisMap
    gate: Gate
    wire: Wire

    def __post_init__(self) -> None:
        if self.wire != self.gate.wire:
            raise ValueError(
                "門の電線と、送信の電線が違う——"
                "⛔ **丸めは門の側の電線で起き、バイト列はこちらの電線で組まれる。**"
                "**同じ機体のものでなければならない**"
            )

    def _index(self, elapsed: float) -> int:
        n = len(self.trajectory.samples)
        step = self.trajectory.duration / (n - 1)
        k = round(elapsed / step)
        return min(n - 1, max(0, k))

    def frames_at(self, t0: float, now: float) -> FrameSet:
        """**`now` の時点で送るべき組を組む。** ⛔ **門を通してから、電線へ流す。**

        ⚠️ **丸めてから門へ渡す。** 丸めは送る値そのものを変えるので、
        **門が見るのは丸めた後でなければならない**——**そうでないと、門は
        「出て行かない値」を検査していることになる。**
        """
        elapsed = now - t0
        if elapsed < 0:
            raise ValueError(f"軌道が始まる前である: t0={t0}, now={now}")
        clamped = min(elapsed, self.trajectory.duration)
        k = self._index(clamped)
        sample = self.trajectory.samples[k]

        commands: list[Command] = []
        for label, value in zip(self.trajectory.labels, sample.position):
            counts = self.axis_map.to_counts(label, value)
            # ⛔ **この呼び出しが、この機体に表せない値をここで落とす。**
            # **門は「送ってよいか」を見る段であり、「送れる形か」ではない**——
            # **そして門の後ろに置くと、落ちたときには門が既に進んでいる。**
            quantized = self.wire.quantize(counts)
            commands.append(Command(axis=self.axis_map.channels[label].motor,
                                     value=quantized))
        verdict = self.gate.submit(now, tuple(commands))
        # ⛔ **バイト列は、門を通った組から組む。** **提案からではない**——
        # **弾かれた刻みに送るのは、保った組か、寄せた値である。**
        payload = self.wire.encode(verdict.commands)
        return FrameSet(verdict=verdict, sample_t=sample.t, at=now,
                        stale_by=now - t0 - sample.t, payload=payload)

    def done(self, t0: float, now: float) -> bool:
        """⚠️ **軌道の終わりに着いたか。** **「機体が止まった」ではない。**"""
        return now - t0 >= self.trajectory.duration
