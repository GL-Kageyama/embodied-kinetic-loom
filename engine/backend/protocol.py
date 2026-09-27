# -*- coding: utf-8 -*-
"""フレーム——**5バイト、チェックサム無し。**

[02_調査/01] §1.1 の実測を、そのまま写す:
**総長5バイト。`[`(0x5B) で始まり `]`(0x5D) で終わる。位置は2バイト big-endian。**
`[A xx]` `[B xx]` `[C xx]` が Motor 1/2/3 の目標位置（`SMC3.ino` の `ParseCommand()`）。

⚠️ **この層が検査するのは「2バイトに入るか」だけである。**
**ホストが既定で送れる 190〜833 は、ここではなく門（`gate.py`）の話である**——
`schemas/motion-intent.schema.json` が値域を型に書かないのと同じ理由で、
**同じ数を2箇所に持つと、2つが食い違う。**

⛔ **そして、この層は危ない3つを知っている:**

1. **相手は受け取った値を検査しない。** ベンダーの参照コード自身がそう書いている。
   ゆえに **`encode_target` は 0〜1024 の外を拒む**——**送る前に落とすのは、ホストの仕事である。**
2. **応答は「送る値」と刻みが違う。** 位置は**送るとき 0〜1024（2バイト）**だが、
   **読むときは `Feedback/4` `Target/4` で 0〜255（1バイト）**（同 §1.3）。
   ⇒ ⛔ **読んだ位置をそのまま送り返すと、4分の1の位置へ飛ぶ。**
   ⇒ **ゆえにこの層は、掛け算をしない。** `FeedbackDiv4` という**名前に単位を書いた型**で返す——
   **掛けるのは、どちらの向きが正しいかを実機で確かめた後の話である。**
3. **`[]` というコマンドは存在しない。** ヘッダコメントには在るが、
   `[]` は2バイトなのでパーサは後続3バイトを飲み込み、**フレームがずれる**（同 §1.1）。
   ⇒ **ここは `[]` を組み立てない。そして、それは「停止」ではない**（同 §2.5）。

⚠️ **payload の中に `[` が現れうる。** 目標 347 = `0x015B` の下位バイトが `0x5B` である。
⇒ **ゆえに「`[` を探して切る」パーサは誤る。** `decode_frames` は
**`[` の後ちょうど4バイトを取り、5バイト目が `]` でなければ1バイト進めて再試行する**——
ファームの規則（「4バイト目が `]` でなければ捨てる」）と同じ形である。
⛔ **ただし、捨てたあとの再同期の位置は上流ソースで確かめていない。** ここは**こちらの定義**である。

⛔ **そして、この層は1つを「書かない」。**
**箱 → host の位置報告の形が、2つの出典で食い違っている。**
[02_調査/01] §1.2 は `[rdA..C]` という形だと要約する。だが §1.3 が全行を読んだ
第三者コードは `SendTwoValues('A', Feedback1/4, Target1/4, ComPort)` だと言い、
**さらに pysmc3 は `args[0]` を target として扱っている**——**つまりラベルが入れ替わっている。**
⇒ **ゆえに `decode_feedback` は書かない。** 確かめていない形を読む関数を置くと、
**Mock が「正しい形で喋っている」という主張を、誰も検証できないまま作ってしまう。**
**書けるのは「送る」側だけである。**
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "START", "END", "FRAME_LEN", "MAX_TARGET", "MOTOR_LETTERS", "READ_DIVISOR",
    "ProtocolError", "Frame", "FeedbackDiv4",
    "encode_target", "encode_text", "decode_frames", "feedback_div4",
]

START = 0x5B  # `[`
END = 0x5D    # `]`
FRAME_LEN = 5
MAX_TARGET = 1024
MOTOR_LETTERS = ("A", "B", "C")  # Motor 1 / 2 / 3

#: ⛔ **読むときだけ 4 で割られている**（§1.3）。**送る側は割らない。**
READ_DIVISOR = 4


class ProtocolError(ValueError):
    """組めない、または読めない。**黙って丸めない。**"""


@dataclass(frozen=True)
class Frame:
    """切れた1フレーム。**生バイトと、位置の意味を両方持つ。**"""

    command: str   # 1文字（例 `A`）
    value: int     # 2バイト big-endian の値
    raw: bytes     # ⚠️ **5バイト。** 門はこれをそのまま渡す

    def motor(self) -> int:
        """`A`/`B`/`C` → 0/1/2。⚠️ **モーターの番号であって、軸の名前ではない。**"""
        try:
            return MOTOR_LETTERS.index(self.command)
        except ValueError as exc:
            raise ProtocolError(f"目標位置の命令ではない: {self.command!r}") from exc

    @property
    def token(self) -> str:
        """**`[` の次の3バイト**——`[mo0]` `[sav]` `[ena]` のような語である。

        ⛔ **`command` は1文字なので、この語とは比較できない。**
        実測（`decode_frames` に `[mo0]` を食わせた）:
        **`command` は `'m'`、`value` は 28464 になる。**
        ⇒ **`frame.command == "mo"` は、決して真にならない。**

        ⚠️ **この版の最初の `mock.py` が、まさにそれを書いていた。**
        **`[mo0]`（報告をやめる）と `[sav]`（EEPROM 保存）の分岐が、
        到達しないコードだった**——**この機体の安全について、いちばん重要な2つの命令が。**

        ⛔ **位置の命令では `""` を返す**（`[A xx]` の3バイトは `A`＋2バイトの値で、
        語ではない）。**ゆえに `motor()` を先に見るのが正しい順である。**
        ⚠️ **`A`/`B`/`C` で始まる語が在るかは、確かめていない**——
        **在れば、この順序でも取り違える。** 実機で確かめるまで、これを書かない。
        """
        body = self.raw[1:4]
        if len(body) != 3 or not all(0x20 <= b < 0x7F for b in body):
            return ""
        return body.decode("ascii")


@dataclass(frozen=True)
class FeedbackDiv4:
    """⚠️ **箱から来た値。単位は「位置の4分の1」である。**

    ⛔ **この型を作った理由は、掛け算を禁じるためである。**
    **そのまま送り返すと、4分の1の位置へ飛ぶ**（§1.3）。
    掛け算は、どちらの向きが正しいかを実機で確かめた後に、1箇所でやる。

    ⛔ **そして、これを組み立てる関数すら、この版には無い。** 上のモジュール docstring を見よ——
    **形が2つの出典で食い違っているので、Mock 側も「正しい形で喋っている」と主張しない。**
    """

    motor: int
    feedback: int
    target: int


def encode_target(motor: int, value: int) -> Frame:
    """`[A xx]` を組む。⛔ **0〜1024 の外は、ここで落ちる。**

    ⚠️ **`value` は丸めない。** 丸めると、呼ぶ側は自分が枠を出たことを知らないまま進む。
    """
    if not 0 <= motor < len(MOTOR_LETTERS):
        raise ProtocolError(f"モーターは 0〜{len(MOTOR_LETTERS) - 1}: {motor}")
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError(f"目標は整数でなければならない: {value!r}")
    if not 0 <= value <= MAX_TARGET:
        raise ProtocolError(
            f"目標が2バイトの位置に収まらない: {value}（0〜{MAX_TARGET}）"
            "——⛔ **相手は受け取った値を検査しない。落とすのはホストの仕事である**"
        )
    letter = MOTOR_LETTERS[motor]
    raw = bytes((START, ord(letter), (value >> 8) & 0xFF, value & 0xFF, END))
    return Frame(command=letter, value=value, raw=raw)


def encode_text(token: str) -> Frame:
    """`[mo0]` `[sav]` `[ena]`——**3文字の語のフレームを組む。**

    ⚠️ **この関数が在る理由は、試験のためである**（Mock に食わせる）。
    **運動の経路はこの形を組み立てない**——§2.5 のとおり、**ここに停止は無い。**

    ⛔ **`A`/`B`/`C` で始まる語は拒む。** `motor()` が位置の命令だと主張するからである——
    **境界を曖昧なまま残さない。** ⚠️ **そういう語が実在するかは、確かめていない**（`Frame.token`）。
    """
    if len(token) != 3 or not all(0x20 <= ord(ch) < 0x7F for ch in token):
        raise ProtocolError(f"語は3文字の ASCII である: {token!r}")
    if token[0] in MOTOR_LETTERS:
        raise ProtocolError(
            f"{token[0]!r} で始まる語は組めない——**位置の命令と区別がつかない**"
            f"（`A`/`B`/`C` はモーターの記号である）"
        )
    raw = bytes((START,)) + token.encode("ascii") + bytes((END,))
    return Frame(command=chr(raw[1]), value=(raw[2] << 8) | raw[3], raw=raw)


def feedback_div4(motor: int, feedback: int, target: int) -> FeedbackDiv4:
    """⚠️ **箱から来た値を、そのまま束ねるだけである。** 掛け算も、割り算もしない。

    ⛔ **`0〜255` の外は落とす**——**読む側は1バイトだからである**（§1.2）。
    """
    for name, v in (("feedback", feedback), ("target", target)):
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 255:
            raise ProtocolError(
                f"{name} は読む側では1バイト（0〜255）: {v!r}"
                "——⛔ **送る側の 0〜1024 と混ぜない。** 単位が違う"
            )
    if not 0 <= motor < len(MOTOR_LETTERS):
        raise ProtocolError(f"モーターは 0〜{len(MOTOR_LETTERS) - 1}: {motor}")
    return FeedbackDiv4(motor=motor, feedback=feedback, target=target)


def decode_frames(buffer: bytes) -> tuple[tuple[Frame, ...], bytes]:
    """貯まったバイトから、**切れるだけ切る。** 残りは次へ渡す。

    ⚠️ **戻り値の2つ目は「まだ足りない分」である。** 捨てた分は含まない——
    **ゆえに呼ぶ側は、捨てたことを数えたいなら戻り値ではなく生バイトを見る。**

    ⛔ **再同期は1バイトずつ進める。** payload に `[` が現れうるからである（モジュールを見よ）。
    """
    frames: list[Frame] = []
    i = 0
    n = len(buffer)
    while i < n:
        if buffer[i] != START:
            i += 1
            continue
        if i + FRAME_LEN > n:
            break  # ⚠️ **まだ足りない。** ここで切ると、次に来た `]` を飲み込む
        candidate = buffer[i:i + FRAME_LEN]
        if candidate[-1] != END:
            i += 1  # ⛔ **捨てて、1バイト進める**
            continue
        value = (candidate[2] << 8) | candidate[3]
        frames.append(Frame(command=chr(candidate[1]), value=value, raw=bytes(candidate)))
        i += FRAME_LEN
    return tuple(frames), bytes(buffer[i:])
