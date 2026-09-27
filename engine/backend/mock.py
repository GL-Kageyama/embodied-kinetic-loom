# -*- coding: utf-8 -*-
"""Mock——**プロトコルの試験である。**

⛔ **D-16 の逐語を、ここに写す**（[02_調査/04] §11.2）:
> **「Mock は『プロトコルの試験』と割り切り、Mock が緑でも実機の安全は保証されないと
> 設計文書に明記する。」**

⇒ **このモジュールは、安全を主張しない。** そして**主張しないために、できることが1つある**——
**機体が黙って飲み込むものを、数えることである。**

⛔ **本物の箱は、段差を受け取っても何も言わない。**
上流ファームにソフトスタート/ストップが無く（[02_調査/01] §2.6）、
**値域チェックもしない**（同 §2.1）。**ゆえに段差は、黙って段差のまま入る。**

⚠️ **Mock はそれを記録する**（`steps`）。
**これは「安全である」の代わりではない**——**「何を送ったか」を、送った側に返すだけである。**
**そしてそれは、実機では決して得られない情報である**——
**この機体は、自分が何をしたかを報告してこない**（`CLAUDE.md` の固定方針）。

⚠️ **Mock と実機が最も食い違う場所は、シリアル層である**（`CLAUDE.md`）——
`flush()` が macOS の pty で無限にブロックすることが実測されている。
⛔ **この Mock はバイト列を渡されるだけなので、シリアル層を1行も持たない。**
**ゆえに「Mock が緑」は、シリアル層について何も言わない。**
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .protocol import MAX_TARGET, MOTOR_LETTERS, Frame, decode_frames

__all__ = ["Step", "MockBox", "TORQUE_DECAY_SECONDS"]

#: ⛔ **ホストが黙ると、この秒数でトルクがおよそ 1/4 になる**（[02_調査/01] §2.4）。
#: ⚠️ **そして、モーターは止まらない。**
TORQUE_DECAY_SECONDS = 15.0


@dataclass(frozen=True)
class Step:
    """⚠️ **箱の位置が、1フレームで動いた量である。**

    ⛔ **「届く速さを超えた」ではない。** `MockBox` は上限を1つも知らないので、
    **その変化が速すぎるかどうかを、この型は判定できない**——
    **段差かどうかを決めるのは門である**（`engine/backend/gate.py` の `_step_violation`）。
    **ここが記録するのは「動いた」という事実だけである。**

    ⚠️ **この版の最初は「届く速さを超えて動いた量」と書いていた。**
    **それは `feed` の実装と食い違っている**——`feed` は `after != before` の回を全部積む
    （小さな変化も、そうでない変化も同じに）。**実測 2026-09-28。**
    ⛔ **型の説明と実装が食い違うと、読む側は説明のほうを信じる。**

    **本物の箱は、これを記録しない。** **この型は Mock にしか無い。**
    """

    motor: int
    before: float
    after: float
    at: float

    @property
    def delta(self) -> float:
        return self.after - self.before


@dataclass
class MockBox:
    """**箱のふりをする。** ⛔ **安全の主張はしない。**

    ⚠️ **`locked` は `one motor locks all` の模型である**（ベンダー自身の言葉）。
    **1本が強制停止に入ると、残る2本も操作できない**——`locked` の間、命令は届かない。
    """

    motors: int = len(MOTOR_LETTERS)
    positions: tuple[float, ...] = ()
    locked: bool = False
    reporting: bool = True
    received: list[Frame] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    last_heard: float | None = None

    def __post_init__(self) -> None:
        if not self.positions:
            self.positions = tuple(0.0 for _ in range(self.motors))

    def feed(self, data: bytes, now: float) -> tuple[Frame, ...]:
        """バイト列を食わせる。**切れたフレームだけを反映する。**

        ⛔ **未知の命令は、黙って無視される**（`SMC3.ino` の `switch` に `default` が無い）。
        **ここが、実機と Mock が一致している数少ない点である**——**箱はエラーを返さない。**

        ⛔ **⚠️ 語は `frame.token` で見る。`frame.command` ではない。**
        `command` は1文字である（`[mo0]` → `'m'`）。**`protocol.py` の `Frame.token` を見よ**——
        **この関数の最初の版は `command == "mo"` と書いていて、その分岐が到達不能だった。**
        """
        frames, _rest = decode_frames(data)
        for frame in frames:
            self.commands.append(frame.token or frame.command)
            if frame.command in MOTOR_LETTERS:
                motor = MOTOR_LETTERS.index(frame.command)
                if motor >= self.motors:
                    continue
                if self.locked:
                    continue  # ⛔ **one motor locks all**
                before = self.positions[motor]
                after = float(frame.value)
                if after != before:
                    self.steps.append(Step(motor=motor, before=before, after=after, at=now))
                self.positions = (
                    self.positions[:motor] + (after,) + self.positions[motor + 1:]
                )
                self.received.append(frame)
                continue
            token = frame.token
            if token.startswith("mo") and len(token) == 3 and token[2].isdigit():
                # ⛔ **`[mo0]` は「報告をやめる」である。モーターは止まらない。**
                # ⚠️ **`[mo1..3]` は「報告を始める」側である**（同 §1.1 の表）。
                self.reporting = token[2] != "0"
            elif token == "sav":
                # ⛔ **`[sav]` は EEPROM への保存である。モーターは止まらない。**
                pass
            elif token.startswith("en"):
                # ⛔ **`[ena]` は「強制停止から戻す」である。止める方ではない**（§2.5）。
                pass
            # ⚠️ それ以外は、**黙って無視**（実機と同じ）
        if frames:
            self.last_heard = now
        return frames

    def silent_for(self, now: float) -> float:
        """⛔ **「送るのをやめてからの秒数」である。そして、それは停止ではない。**

        **これが 15 を超えたら、トルクはおよそ 1/4 になっている**——
        **そして機体は、まだ動いているかもしれない。**
        """
        if self.last_heard is None:
            return 0.0
        return now - self.last_heard

    def torque_decayed(self, now: float) -> bool:
        """⚠️ **止まっていることの証拠ではない。**"""
        return self.silent_for(now) >= TORQUE_DECAY_SECONDS

    def frames_within_2bytes(self) -> bool:
        """⛔ **この検査は「送れる形だったか」しか言わない。**

        **`MAX_TARGET` はプロトコルの2バイトの話であって、**
        **ホストが既定で送れる 190〜833 の話ではない**——**それは門の仕事である。**
        """
        return all(0 <= f.value <= MAX_TARGET for f in self.received)
