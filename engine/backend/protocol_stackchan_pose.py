# -*- coding: utf-8 -*-
"""機体2の、**2本目の電線——姿勢を、tick ごとに1行で運ぶ。**

⛔ **遷移の枠（`protocol_stackchan.py`）とは別の行種である。** あちらは
**機体の見せるものが変わったとき**に1行、こちらは**刻みごと**に1行——頻度が2桁違う。
**同じ行に混ぜないのは、混ぜると、遷移の行が姿勢の行に埋もれるからである。**

⚠️ **運ぶのは度の10倍の整数**であって、サーボの生カウントではない。
⇒ **ゼロ点とスケールは基板の側に残る。** この機体のゼロ点は**NVS にあり、固体差である**
——**ホストがそれを焼き込めば、機体の数が機体の外へ出る**（`main/servo.cpp` の
`RawFromAngle` が、基板が持つ側の仕事をする）。⛔ **ゆえに、その数はここに写さない**——
**値は記録（`records/2026-10-18-first-arrival.md`）にだけ在り、ここに在るときは写しである。**

⚠️ **なぜチェックサムを持つか。** ⛔ **これは運動であり、起きたことは取り消せない。**
`pose 50` が1バイト化けて `pose 90` になっても、**機体の枠の内側なので clamp では捕まらない**
——12.5° の誤りが、そのまま動く。**遷移の枠（JSON）がチェックサムを持たないのは、
あちらが状態の変化であって、運動ではないからである。**

⛔ **そして、和は何を捕まえないかを、ここに書く。** 1バイトの化けは捕まえるが、
**同じ桁を入れ替えた `50` → `05` は、和が同じなので捕まらない。**
⇒ **綴りを正準形に縛ることで、その一部を先に落とす**——`05` も `-0` も `+5` も読まない。
**残りは捕まらない。CRC にしなかったのは、基板の側の行数が増えるからである**——
**この線の誤りは、1行が短いことと、次の行が20 ms 後に来ることの両方が減らす。**

⚠️ **このモジュールは輸入を持たない**（`dataclasses` と `typing`、そして同じ層の2つだけ）。
時計も、ソケットも、環境も読まない——**純粋な関数である。**

## 決まっていて、まだ1行も書かれていないこと

⚠️ **この節は方針であり、実装ではない。** 基板の側（`projects/stackchan-firmware/`）は
**この行をまだ1つも読まない**——**ゆえに、以下の3つはどれも、まだ何も守っていない。**

- ⚠️ **刻みは 20 ms（50 Hz）である。** エンジンの既存の周期（`projects/pet/motion.py`）に
  合わせた——⛔ **そこに「測定ではない」と書いてあるのが、そのままここにも掛かる。**
  **機体2がこの周期に耐えるかは、測られていない。**
- ⛔ **姿勢を流している間、基板は `bench` を拒む。** `bench` はコンソールの仕事を
  数秒ふさぐので、**その間の姿勢は遅れて届く**——**遅れて届いた姿勢は、姿勢ではない。**
- ⛔ **500 ms 黙れば、基板はトルクを放して1行を出す。** 文は
  `pose: stream lost after 500 ms — torque released` であり、**「機械が止まった」ではない**
  ——**止まったことと、力を放したことは、別である**（`CLAUDE.md` の安全の節）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .protocol_stackchan import FrameRefused
from .wire import Command

__all__ = [
    "MAX_LINE",
    "Pose",
    "StackChanPoseWire",
    "checksum",
    "decode",
    "encode",
]

#: ⚠️ **1行の上限である。** 最長の行は `pose -1800 -1800*XX\n` の 20 バイトで、
#: **64 は桁が違う側の余裕である。** ⛔ **これは機体の測定ではない。**
MAX_LINE = 64

#: ⛔ **プロトコルの健全性の枠であって、機体の枠ではない。**
#: 機体の枠（yaw ±20°、pitch 3〜87°）は**基板の側にあり**、ここには来ない——
#: **ここで落とすのは、桁が壊れた行だけである。**
_LIMIT_TENTHS = 1800

_FIRST_WORD = b"pose"


@dataclass(frozen=True)
class Pose:
    """**機体2へ向かう、1つの姿勢。** 度の10倍の整数で、yaw は符号つき。

    ⛔ **欄は2つとも常に在る。** 欠けた欄は受け取る側が前の値で埋めてしまう——
    **「変えない」を表したいなら、前の値を書く。**
    """

    yaw_tenths: int
    pitch_tenths: int


def checksum(body: bytes) -> str:
    """**本文の全バイトの和の下位8ビットを、2桁の16進で。** ⚠️ `*` は含めない。

    和を選ぶのは、**基板の側で1行で書けるから**である——C++ でも同じ3行になる。
    """
    return f"{sum(body) & 0xFF:02X}"


def _parse_tenths(text: str) -> int:
    """⚠️ **厳密に読む。** 符号は先頭の1つだけ、数字は1〜4桁、**そして正準形だけ**。

    ⛔ **`int()` に任せない**——`+5` も ` 5` も `５` も通してしまい、
    **両端で規則がずれる**（読む側と書く側が別々の規則を持つと、片方だけが直る）。

    ⚠️ **正準形に縛るのは、1つの姿勢に1つの綴りしか無いようにするためである**——
    `05` と `5` が同じ姿勢の2つの綴りなら、**和はその2つを区別しない**（上の但し書き）。
    """
    body = text[1:] if text.startswith("-") else text
    if not body or len(body) > 4 or not body.isdigit():
        raise FrameRefused("malformed", "value", text)
    value = int(text)
    if str(value) != text:
        raise FrameRefused("malformed", "value", text)
    if abs(value) > _LIMIT_TENTHS:
        raise FrameRefused("out-of-range", "value", value)
    return value


def encode(pose: Pose) -> bytes:
    """**1つの姿勢を、1行にする。** ⚠️ **改行で終わる。** 欄は2つとも書く。

    ⛔ **バイト列にするのは、ここだけである**——`Pose` は行を持たない。
    """
    if not isinstance(pose, Pose):
        raise FrameRefused("bad-type", "pose", type(pose).__name__)
    for name, value in (("yaw_tenths", pose.yaw_tenths),
                        ("pitch_tenths", pose.pitch_tenths)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise FrameRefused("bad-type", name, type(value).__name__)
        if abs(value) > _LIMIT_TENTHS:
            raise FrameRefused("out-of-range", name, value)
    body = f"{_FIRST_WORD.decode()} {pose.yaw_tenths} {pose.pitch_tenths}".encode("ascii")
    return body + b"*" + checksum(body).encode("ascii") + b"\n"


def decode(line: bytes) -> Pose:
    """**1行を、1つの姿勢に戻す。** ⛔ **知らない行種は、黙って捨てずに拒む。**

    ⚠️ **拒む理由を、コードで返す。** 文は、機械にも表にも届かない
    （`FrameRefused` の但し書きと同じ）。
    """
    if not isinstance(line, (bytes, bytearray)):
        raise FrameRefused("bad-type", "line", type(line).__name__)
    if len(line) > MAX_LINE:
        raise FrameRefused("too-long", None, len(line))
    text = bytes(line)
    try:
        text.decode("ascii")
    except UnicodeDecodeError:
        raise FrameRefused("malformed") from None
    if text.endswith(b"\n"):
        text = text[:-1]
    if b"\n" in text or b"\r" in text:
        raise FrameRefused("malformed")
    if not text.startswith(_FIRST_WORD + b" "):
        raise FrameRefused("not-pose", None, text.split(b" ", 1)[0].decode("ascii", "replace"))
    body, star, given = text.rpartition(b"*")
    if not star or len(given) != 2:
        raise FrameRefused("malformed")
    if given.decode("ascii", "replace") != checksum(body):
        raise FrameRefused("bad-checksum")
    fields = body.split(b" ")
    if len(fields) != 3:
        raise FrameRefused("malformed")
    return Pose(
        yaw_tenths=_parse_tenths(fields[1].decode("ascii")),
        pitch_tenths=_parse_tenths(fields[2].decode("ascii")),
    )


@dataclass(frozen=True)
class StackChanPoseWire:
    """**`Wire` の形をした、機体2の姿勢の電線。**

    ⚠️ **軸は、この線の上の順序である**——軸0が1欄目（yaw）、軸1が2欄目（pitch）。
    ⛔ **モーターの番号ではない。** どのサーボがどちらかは基板が知っており、
    **この型は知らない**（`wire.py` の但し書きと同じ規則）。

    ⛔ **半分の姿勢は表せない。** 欄は2つとも常に在るので、片方だけの組は拒む——
    **欠けた欄を前の値で埋めるのは、受け取る側の仕事ではなく、ここで止めるべきことである。**
    """

    def axis_count(self) -> int:
        """**この線が運ぶ軸の数。** yaw と pitch の2つである。"""
        return 2

    def quantize(self, value: float) -> float:
        """**度を、0.1° に丸める。** この線は 0.1° より細かい値を表せない。

        ⚠️ **丸めは、送る値そのものを変える。** ゆえに門が見るのは丸めた後である
        （`wire.py` の但し書きと同じ）。
        """
        return round(value * 10) / 10

    def encode(self, commands: Sequence[Command]) -> bytes:
        """**1刻みの組を、1行にする。** ⚠️ **空の組は空のバイト列である。**

        ⛔ **2軸そろっていない組は拒む。** 1行は常に両方を書く。
        """
        if not commands:
            return b""
        values: dict[int, float] = {}
        for command in commands:
            if not isinstance(command, Command):
                raise FrameRefused("bad-type", "command", type(command).__name__)
            if command.axis in values:
                raise FrameRefused("duplicate-axis", "axis", command.axis)
            if command.axis not in (0, 1):
                raise FrameRefused("unknown-axis", "axis", command.axis)
            values[command.axis] = command.value
        if len(values) != 2:
            missing = [axis for axis in (0, 1) if axis not in values]
            raise FrameRefused("missing-axis", "axis", missing[0])
        return encode(Pose(
            yaw_tenths=_to_tenths(values[0], "yaw"),
            pitch_tenths=_to_tenths(values[1], "pitch"),
        ))


def _to_tenths(value: float, name: str) -> int:
    """⚠️ **すでに丸められた値を、整数の10分の1度にする。** 丸め直さない。"""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise FrameRefused("bad-type", name, type(value).__name__)
    tenths = round(value * 10)
    if abs(tenths) > _LIMIT_TENTHS:
        raise FrameRefused("out-of-range", name, value)
    return int(tenths)
