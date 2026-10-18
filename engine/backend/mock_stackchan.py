# -*- coding: utf-8 -*-
"""機体2の Mock——**プロトコルの試験である。**

⛔ **機体1の `mock.py` の但し書きが、そのままここにも掛かる:**
**Mock はプロトコルの試験であり、Mock が緑でも実機の安全は保証されない。**

⛔ **そして、機体1の Mock から数を持ち込まない。** `mock.py` は
「15秒でトルクがおよそ1/4になる」という機体1の数を1つ持っているが、
**2台目には、その数の出典が1つも無い**——だからこのファイルには無い。
**機体2の振る舞いについては、このリポジトリはまだ何も測っていない。**

⚠️ **この Mock は、返事を1つも返さない。** `send` の戻り値は `None` であり、
**それは「届いた」の証明ではない**——**機体は自分が何をしたかを報告しない**
（`CLAUDE.md` の固定方針）。ここが記録するのは**送った側の行だけ**である。

⚠️ **ポートも、ソケットも、時計も開かない。** ゆえに「Mock が緑」は、
**電線について何も言わない**——まして、焼いたファームについても。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .protocol_stackchan import Command, decode
from .protocol_stackchan_pose import Pose, decode as decode_pose

__all__ = ["MockStackchan", "MockStackchanPose"]


@dataclass
class MockStackchan:
    """⚠️ **受け取った枠を、順に積むだけの器である。**

    ⛔ **答えないことが、この型の正しい振る舞いである。** 本物の機体は、
    **受け取った値が正しいかを検査しない**——それは機体1について文書化された性質であり、
    **機体2については何も分かっていない。** ⇒ **この Mock の厳しさは、ホスト側の
    符号化を試すためのものであって、機体の性質の主張ではない。**
    """

    sent: list[Command] = field(default_factory=list)

    def send(self, line: bytes) -> None:
        """**1行を受け取り、読めたら積む。** ⛔ **返事は無い。**

        ⚠️ **読めない行は `FrameRefused` を投げる。** 本物が黙って飲み込むかどうかは、
        この機体では測られていない——**だから、ここで黙る真似はしない。**
        """
        self.sent.append(decode(line))

    def last(self) -> Command | None:
        """**最後に届いた枠。** まだ何も届いていなければ `None`。"""
        return self.sent[-1] if self.sent else None

    def count(self) -> int:
        """**届いた枠の数。** ⚠️ **これは「動いた回数」ではない。**"""
        return len(self.sent)


@dataclass
class MockStackchanPose:
    """⚠️ **2本目の線の Mock——姿勢を、順に積むだけの器である。**

    ⛔ **1つ目の Mock と同じ性格であり、同じ但し書きが掛かる:**
    **緑はプロトコルの緑であり、機体の緑ではない。** そして、**20 ms ごとに目標を
    書き換え続けることが、この個体で生き延びるかは、まだ測られていない**——
    `MOVE_SETTLE = 1.0` は、走っている最中に次の指令が来ると両軸を落とした
    （`docs/construction-memo.md` の罠）。⛔ **この Mock は、その罠について何も言わない。**
    """

    sent: list[Pose] = field(default_factory=list)

    def send(self, line: bytes) -> None:
        """**1行を受け取り、読めたら積む。** ⛔ **返事は無い。**"""
        self.sent.append(decode_pose(line))

    def last(self) -> Pose | None:
        """**最後に届いた姿勢。** まだ何も届いていなければ `None`。"""
        return self.sent[-1] if self.sent else None

    def count(self) -> int:
        """**届いた行の数。** ⚠️ **これは「動いた回数」ではない。**"""
        return len(self.sent)
