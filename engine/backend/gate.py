# -*- coding: utf-8 -*-
"""門——**実際に出て行く1組を見る。**

⛔ **これが、いままで無かった段である。**
`engine/trajectory/admit.py` は**計画時**に検査する。**だが計画と、出て行く組は別物である。**
`README.md` の「まだ無いもの」の1行目が、そのままこのモジュールの仕事である——
**「制限の検査は計画時に走る——実際に出て行くものを門で見る段は、まだ無い。」**

⚠️ **この門は「フレーム」を知らない。** 通貨は `(軸, 値)` である（`wire.py`）——
**1モーター1フレームの機体では同じに見えるが、1行に2軸を運ぶ機体では別物になる。**
**門が決めるのは「どの軸に、どの値を送ってよいか」だけであり、
「それが何バイトになるか」は電線（`Wire.encode`）の仕事である。**

**計画時には見えず、ここでだけ見えるもの:**

| 何 | なぜ計画時に見えないか |
|---|---|
| **1刻みごとの段差** | ⛔ **上流ファームにソフトスタート/ストップが無い**（[02_調査/01] §2.6）。**段差指令は段差のまま入る。** 段差になるかどうかは、**送る時刻の刻みで決まる**——計画は時刻を持たない |
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
**門にできるのは、悪い1刻みを出さないことだけである。**

⛔ **そして——「保つ」だけでは、軸が凍る。**（2026-09-27、実装中に見つけた）

**保つ基準が「最後に*通した*値」である一方、送信が提案するのは「*いまの*壁時計の値」である。**
⇒ **提案は先へ進み続けるので、段差は縮まらない。**
⚠️ **そして弾くたびに `_last_t` が進むので、溜まった時間が毎回捨てられる**——
⇒ **1回弾かれると、二度と通らない。** `admit` を通った軌道でも、端に着かない。

**⇒ ゆえに弾かれた軸は、止まるのでなく、届く速さで目標へ寄る**（`_slew`）。
⛔ **そして、これは新しい仮定を1つも足さない**——**寄せる大きさは `limit × elapsed` であり、
門がもともと通す大きさと同じである。** **門が「これは段差だ」と言った大きさの、
いちばん大きいものが、そのまま「寄せてよい大きさ」になる。**

⚠️ **枠（`target_min`／`target_max`）の外へは寄せない。** **保つ。**
**寄せてよいのは、届く先が枠の中にあるときだけである**——**枠の外は、寄る先ではない。**

⚠️ **判断は「組ごと」である。** 1モーターずつ通すと、
**誰も計画していない組み合わせ**が機体の上に現れる。

## ⛔ そして、門は「知っている軸」を黙らせない（2026-10-15）

**提案に無い軸は、かつて出力から消えていた。** 門は `proposed` を回すだけであり、
`out` に入るのは**提案された軸だけ**だった——**が、同じ関数の docstring は
「空を返す軸は1つも無い」と主張していた。**
⚠️ **それは偽であった。** `Transmitter` が毎回すべての軸を提案するので、表に出ていなかっただけである。

⛔ **機体2では、これが表に出る。** **1行が2軸を運ぶ機体では、片方の軸が組から消えると、
`encode` はそこに何を書けばよいか分からない**——**既定を書けば段差であり、
書かなければ別の値になる。どちらも段差である。**
⇒ **提案の後に、門が知っている軸（開始位置を渡された軸）をすべて埋める。**
**これで、この節の主張が初めて真になる。**

⚠️ **埋めることは「弾く」ではない。** 埋まった軸には**いま機体が居る値**が入る——
**それを送ることは、その軸について何もしないことである。**
⇒ **`held` は真にならない。** `held` が言うのは**「提案どおりには通さなかった」**だけである。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..trajectory.limits import ChannelLimits, Envelope, Violation
from .wire import Command, Wire

__all__ = ["Gate", "Verdict"]


@dataclass(frozen=True)
class Verdict:
    """門の答え。**`commands` は「実際に送ってよいもの」である。**

    ⚠️ **`commands` が空になることは無い**（構築時に初期位置を渡している以上）。
    ⛔ **`held` が真なら、それは「弾いた」ではなく「前の組を保っている」である。**
    ⚠️ **ただし `held` は「1つも動かない」ではない**——**弾かれた軸も、届く速さでなら寄る**
    （`_slew` を見よ）。**`held` が言うのは「提案どおりには通さなかった」だけである。**

    ⚠️ **軸の並びは、軸の番号の昇順である**（`sorted`）。**電線はこの並びで書く**——
    **ゆえにこの並びは、決定論の一部である。**
    """

    allowed: bool
    commands: tuple[Command, ...]
    violations: tuple[Violation, ...] = ()
    held: bool = False


@dataclass
class Gate:
    """**出て行く1組を見る。**

    ⚠️ **`starts_by_motor` は必須である。** 既定値を持たない——
    **初期位置を知らずに最初の1組を出すことは、いちばん危ない段差を盲撃ちで送ることである。**
    どこに居るかを知っている側（フィードバック、または利用者）が渡す。

    ⛔ **`envelope` も必須である。** 既定値を持たない——
    ⚠️ **既定を持てば、門は静かに1台目の枠になる。**
    機体1の 190〜833 は `protocol.DOF_REALITY_ENVELOPE` に**1回だけ**現れ、
    **ここへは名前で渡される。** **写しを持たない**——
    **同じ数を2箇所に持つと、2つが食い違う**（`engine/trajectory/limits.py` を見よ）。

    ⛔ **`wire` も必須である。** 門はこの機体の数え方で丸め、この機体の軸の数を知る。
    ⚠️ **門は機体の名前を1つも書かない**——**知っているのは `Wire` という形だけである。**
    """

    starts_by_motor: tuple[float, ...]
    limits_by_motor: tuple[ChannelLimits, ...]
    envelope: Envelope
    wire: Wire
    _last: tuple[Command, ...] | None = None
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
        if n > self.wire.axis_count():
            raise ValueError(
                f"開始位置が {n} 個、電線の軸が {self.wire.axis_count()} 本"
                "——⛔ **電線が表せない軸へ、門は指令を出せない**"
            )
        # ⛔ **開始位置も、この機体の数え方に丸める。**
        # **門が保つ値は、機体へ実際に行った値でなければならない**——
        # **そうでなければ、最初の段差が「行かなかった値」から測られる。**
        # ⚠️ **ここで落ちるのは正しい。** 表せない開始位置を持つ機体は、
        # **そもそも1つも指令を受け取れない**——**組み立てた瞬間に分かる方がよい。**
        self._last_values = tuple(self.wire.quantize(float(v)) for v in self.starts_by_motor)

    def _target_violation(self, motor: int, value: float) -> Violation | None:
        env = self.envelope
        if env.target_min is not None and value < env.target_min:
            return Violation("target", motor, 0.0, value, env.target_min)
        if env.target_max is not None and value > env.target_max:
            return Violation("target", motor, 0.0, value, env.target_max)
        return None

    def _step_violation(self, motor: int, value: float, elapsed: float) -> Violation | None:
        """⛔ **ここが門の固有の仕事である。**

        **届く速さを超える1刻みは、機体の上では段差になる**——
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

    def _slew(self, motor: int, value: float, elapsed: float) -> float:
        """⛔ **弾かれた軸を、止めずに、届く速さで目標へ寄せる。**

        **戻すのは `limit × elapsed` だけ寄せた値である**——
        ⚠️ **これは門がもともと通す大きさと同じである。**
        ⇒ **新しい仮定を1つも足していない。** **門が「段差だ」と言った大きさの、
        いちばん大きいものが、そのまま「寄せてよい大きさ」になる。**

        ⚠️ **`limit` が `None` なら、段差の検査が無い**（`limits.py`）——
        **ゆえにここへは来ない。** 来たなら、寄せる理由が無いので提案をそのまま返す。

        ⛔ **そして、ここは丸めない。** 丸めるのは電線の仕事である（`wire.py`）——
        **門が知っているのは「どれだけ寄せてよいか」であり、
        「この機体が何を表せるか」ではない。** **呼ぶ側（`submit`）が、その値も電線に通す。**
        """
        limit = self.limits_by_motor[motor].velocity
        if limit is None:
            return value
        allowed = limit * elapsed
        last = self._last_values[motor]
        target = float(value)
        if target > last + allowed:
            return last + allowed
        if target < last - allowed:
            return last - allowed
        return target

    def _previous(self, motor: int) -> Command | None:
        """⚠️ **その軸へ最後に送ったもの。** 無ければ `None`。"""
        if self._last is not None:
            for kept in self._last:
                if kept.axis == motor:
                    return kept
        if 0 <= motor < len(self.starts_by_motor):
            # ⚠️ **まだ1つも送っていない軸は、開始位置に居る。** **そこへ「保て」は、
            # そこへ居ろということである**——**これが最初の1組の段差を防ぐ。**
            # ⛔ **`starts_by_motor` ではなく `_last_values` を読む。**
            # **後者は既にこの機体の数え方に丸められており、機体へ行くのはそちらである。**
            return Command(axis=motor, value=self._last_values[motor])
        return None

    def submit(self, now: float, proposed: tuple[Command, ...]) -> Verdict:
        """**この組を送ってよいか。** ⛔ **弾いても、黙らない。**

        `now` は呼ぶ側の時計である（`engine/` は `time` を import しない）。
        ⚠️ **単調でなければ落ちる**——**戻る時計の上では、刻みが負になる。**

        ⚠️ **弾かれた軸にも、必ず何かが返る**——**前の値を保つか、届く速さで寄るかである。**
        **空を返す軸は1つも無い**——**提案に無い軸も、この門が知っている限りは埋める**
        （モジュールの最後の節を見よ）。
        """
        if self._last_t is not None and now <= self._last_t:
            raise ValueError(
                f"時計が戻った: {self._last_t} → {now}"
                "——**刻みが負になると、段差の検査が意味を失う**"
            )
        elapsed = 0.0 if self._last_t is None else now - self._last_t

        violations: list[Violation] = []
        seen: set[int] = set()
        out: dict[int, Command] = {}
        values: dict[int, float] = {}

        def fall_back(motor: int) -> None:
            """⚠️ **その軸について、実際に送るものを決める。**"""
            kept = self._previous(motor)
            if kept is not None:
                out[motor] = kept
                values[motor] = kept.value

        for command in proposed:
            motor = command.axis
            if motor in seen:
                # ⛔ **同じモーターへ2つ送ると、後が勝つ。** それは「計画」ではない。
                violations.append(Violation("duplicate-motor", motor, elapsed, 0.0, 1.0))
                continue
            seen.add(motor)
            if motor < 0 or motor >= len(self.starts_by_motor):
                violations.append(Violation("unknown-motor", motor, elapsed, 0.0,
                                            float(len(self.starts_by_motor))))
                continue
            tv = self._target_violation(motor, command.value)
            if tv is not None:
                # ⛔ **枠の外へは寄せない。** **枠の外は、寄る先ではない。**
                violations.append(tv)
                fall_back(motor)
                continue
            if self._last_t is not None:
                sv = self._step_violation(motor, command.value, elapsed)
                if sv is not None:
                    violations.append(sv)
                    # ⛔ **寄せた値も、電線に通す。** **機体へ行くのは通った後である**——
                    # **ゆえに門が覚えるのも通った後の値になる**（`values` を見よ）。
                    slewed = self.wire.quantize(self._slew(motor, command.value, elapsed))
                    out[motor] = Command(axis=motor, value=slewed)
                    values[motor] = slewed
                    continue
            out[motor] = command
            values[motor] = float(command.value)

        # ⛔ **提案に無い軸を、黙らせない**（モジュールの最後の節を見よ）。
        # ⚠️ **埋まるのは、門が開始位置を渡された軸だけである**——
        # **それ以外の軸は、門が値を知らないので埋めようが無い。**
        for motor in range(len(self.starts_by_motor)):
            if motor not in out:
                fall_back(motor)

        emitted = tuple(out[m] for m in sorted(out))
        # ⛔ **時計は必ず進める。** 弾いた回も、何かを**送っている**からである。
        # ⇒ **次に許す量の基準は、その送信からの経過時間になる。**
        self._last_t = now
        # ⚠️ **値も進める**——**寄せた値は、機体へ行った値である。**
        # **進めなければ、門は永久に同じ段差を見続け、軸は凍る。**
        for motor, value in values.items():
            self._last_values = (
                self._last_values[:motor] + (value,) + self._last_values[motor + 1:]
            )
        self._last = emitted

        if violations:
            return Verdict(allowed=False, commands=emitted, violations=tuple(violations),
                           held=True)
        return Verdict(allowed=True, commands=emitted)

    def hold(self) -> tuple[Command, ...]:
        """⚠️ **最後に送った組。** まだ1つも通していなければ空である。

        **これは「止める」ではない**——**保つことだけができる**（モジュールを見よ）。
        ⚠️ **弾いた回も更新される**——**送ったものが入るのであって、通ったものではない。**
        """
        return self._last if self._last is not None else ()
