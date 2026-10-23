# -*- coding: utf-8 -*-
"""機体2の電線——**記号だけを運び、数は1つも運ばない。**

⛔ **ここに機体2の角度は無い。** 身振りは名前であり、名前から角度への表は
**どの記録にも無い**（`docs/first-contact-stackchan.md`）。**表を書けば、それは発明である。**
⇒ **このモジュールができるのは、記号を1行にすることと、その行を読み返すことだけである。**

⚠️ **機体1の `protocol.py` とは、同じ棚に並ぶが、同じものを運ばない。**
機体1は軸と10ビットの数（`[A xx]`）を運ぶ。機体2は `look_up` / `nod` / … を運ぶ。
⛔ **2つを1つの型にまとめないこと**——**機体1の数え方を、2台目に1つも持ち込まない**
（`mock_stackchan.py` の docstring も同じことを書いている）。

⚠️ **1枠＝1行、機体の見せるものが変わったときだけ。** これは20 ms の流れではない。
⛔ **「遷移のとき」を、事象の種類で数えない**——段階は6つの遷移事象のほかでも動く
（`blocked` の中の `PostToolUse` が `working` へ戻す）。**だから枠は、理由ではなく
状態の変化で出る**（`projects/stackchan/outbound.py`）。**身振りは事象であり、
続く状態ではない**——だから、遅れて届いた身振りというものが存在しない
（クールダウンで落ちたものは、`gesture: null` として届く）。

⚠️ **欄は4つとも常に在る。** 省略しないのは、**枠を自己記述にするためである**——
`null` は「変えない」という値であって、欠けた欄ではない。
**欠けた欄は、受け取る側が前の値で埋めてしまう。**

✅ **`sound` は 2026-10-18 に着いた**——⚠️ **語彙が先で、欄が後である。**
この欄が運ぶのは**音の名前**であり、周波数でも長さでもない。語から音への表は
ファームウェアに在り、**この機体の耳で1つずつ決められる**（身振りと同じ規則）。
⛔ **`sound` は状態ではない。** 顔と光は「いま何であるか」だが、音は**事象**である——
だから `null` は「変えない」ではなく、**「この枠は鳴らない」**である。
⚠️ 同じ語が2つの枠に続けて載ることはない（`projects/stackchan/outbound.py`）。

⚠️ **このモジュールは輸入を持たない**（`json` と `dataclasses` だけ）。時計も、ソケットも、
環境も読まない——**純粋な関数である**（`tools/purity.py` の一覧を見よ）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass

__all__ = [
    "FACES",
    "LIGHTS",
    "GESTURES",
    "SOUNDS",
    "MAX_LINE",
    "Command",
    "FrameRefused",
    "encode",
    "decode",
]

#: ⚠️ **8つの顔である。** 先頭5つは Pet のもので（`projects/pet/expressions.py`）、
#: 後ろ3つはこの機体が 2026-10-24 に足した（`projects/stackchan/faces.py`）。
#: ⛔ **この一覧は写しである**——正典は `projects/stackchan/faces.py` の `Face` であり、
#: `tests/test_stackchan_faces.py` が、3つが食い違った日に赤くなる。
#: **写しを持つのは、両端がそれを読むからである**:
#: ここはホスト側、契約は `schemas/stackchan-command.schema.json`、ファームは C++ の綴り。
#: ⚠️ **2026-10-24 まで、この一覧の註は「`tests/test_stackchan_wire.py` が食い違いを
#: 見る」と書いていたが、その検査は存在しなかった**——Pet を輸入する試験は1つも無く、
#: 綴りを比べていたのは**電線・契約・ファームの3つだけ**であった。**規則は書かれ、
#: 検査は無く、緑のままだった。** 足したのは `tests/test_stackchan_faces.py` である。
FACES: tuple[str, ...] = (
    "curious",
    "greeting",
    "happy",
    "angry",
    "sleepy",
    # ⚠️ この機体の3語。⛔ 語は意味に対して付けた——形は目が決める。
    "focused",
    "watching",
    "startled",
)

#: ⚠️ **8つの意味である**（`projects/stackchan/behaviors.py` の `Light`）。
#: ⛔ **色ではない。** 12個の LED への対応はファームの仕事であり、並びも色順も記録に無い。
#: ✅ **`writing` と `busy` は 0.19.47 に足した**——`working` のあいだの光を、
#: 何をしているかで分ける2語である。⚠️ **足したのは、色が決まったからではなく、
#: デーモンがその語を送る日と、基板がそれを解する日を同じにするためである。**
LIGHTS: tuple[str, ...] = (
    "off", "dim", "writing", "busy", "breathe", "warm", "alert", "error",
)

#: ⛔ **候補語であって、語彙の行ではない**（`references/README.md`）。
#: **数になった日に、行が書かれる。**
GESTURES: tuple[str, ...] = ("look_up", "nod", "look_side", "rest", "recoil")

#: ✅ **2026-10-18 の語である。** 音の名前であり、音そのものではない。
#: ⚠️ **4つとも、鳴る理由が1つずつ違う**——挨拶・人を要る瞬間・終わり・失敗である。
#: ⛔ **ここに周波数は無い。** 語から音への表はファームに在り、この機体の耳で決まる。
SOUNDS: tuple[str, ...] = ("hello", "pip", "chime", "fall")

#: ⚠️ **枠の上限である。** 最長の枠は、5文字の顔・6文字の光・6文字の身振り・
#: 5文字の音で、区切りと鍵を足しても120バイトに届かない——**256は、桁が違う側の余裕である。**
#: ⛔ **これは機体の測定ではない**——プロトコルの縛りである。
MAX_LINE = 256

_KEYS = frozenset({"face", "light", "gesture", "sound"})


class FrameRefused(ValueError):
    """⚠️ **読めなかった枠。** **文ではなく、コードと値を返す**（`Rejection.reason` と同じ形）。

    ⛔ **文は、機械にも表にも届かない。** 断りの理由は、コードとして閉じた集合である。
    """

    def __init__(self, code: str, field: str | None = None, value: object = None) -> None:
        self.code = code
        self.field = field
        self.value = value
        where = f"（{field}={value!r}）" if field is not None else ""
        super().__init__(f"{code}{where}")


@dataclass(frozen=True)
class Command:
    """**機体2へ向かう1つの枠。**

    ⛔ **数が1つも無い。** `light` は常にあり、`face` と `gesture` と `sound` は `None` を取りうる——
    `None` は「変えない」（音では「鳴らない」）であり、欠けた欄ではない。
    """

    light: str
    face: str | None = None
    gesture: str | None = None
    sound: str | None = None


def _checked(command: Command) -> dict:
    """⚠️ **符号化の前に、同じ規則で検査する。** 読む側と書く側が別々の規則を持つと、
    片方だけが直る（`tools/purity.py` の言葉）。
    """
    if not isinstance(command, Command):
        raise FrameRefused("bad-type", "command", type(command).__name__)
    if command.light not in LIGHTS:
        raise FrameRefused("unknown-value", "light", command.light)
    if command.face is not None and command.face not in FACES:
        raise FrameRefused("unknown-value", "face", command.face)
    if command.gesture is not None and command.gesture not in GESTURES:
        raise FrameRefused("unknown-value", "gesture", command.gesture)
    if command.sound is not None and command.sound not in SOUNDS:
        raise FrameRefused("unknown-value", "sound", command.sound)
    return {
        "face": command.face,
        "light": command.light,
        "gesture": command.gesture,
        "sound": command.sound,
    }


def encode(command: Command) -> bytes:
    """**1つの枠を、1行にする。** ⚠️ **改行で終わる。** 鍵は常に4つとも書く。

    ⛔ **バイト列にするのは、ここだけである**——`Command` は行を持たない。
    """
    body = json.dumps(
        _checked(command), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return (body + "\n").encode("ascii")


def decode(line: bytes) -> Command:
    """**1行を、1つの枠に戻す。** ⛔ **知らない鍵は、無視せずに拒む。**

    ⚠️ **拒むのは、読めないからではない。** 無視されるだけの欄は同乗できるが、
    拒まれる欄は同乗できない——**プロンプトがこの電線を渡らないのは、構造の性質である**
    （`projects/stackchan/hook/` と `daemon/room.py` が同じ規則を持つ）。

    ⛔ **2行は拒む。** 1つの枠は1行であり、行をまたぐ状態は、この層に無い。
    """
    if len(line) > MAX_LINE:
        raise FrameRefused("too-long", None, len(line))
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError:
        raise FrameRefused("malformed") from None
    if text.endswith("\n"):
        text = text[:-1]
    if "\n" in text or "\r" in text:
        raise FrameRefused("malformed")
    try:
        body = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        raise FrameRefused("malformed") from None
    if not isinstance(body, dict):
        raise FrameRefused("not-an-object", None, type(body).__name__)
    for key in body:
        if key not in _KEYS:
            raise FrameRefused("unknown-key", key, body[key])
    for key in _KEYS:
        if key not in body:
            raise FrameRefused("missing-key", key)
    face = body["face"]
    light = body["light"]
    gesture = body["gesture"]
    sound = body["sound"]
    for name, value in (
        ("face", face), ("light", light), ("gesture", gesture), ("sound", sound)
    ):
        if value is not None and not isinstance(value, str):
            raise FrameRefused("bad-type", name, type(value).__name__)
    if light is None:
        raise FrameRefused("missing-key", "light")
    if light not in LIGHTS:
        raise FrameRefused("unknown-value", "light", light)
    if face is not None and face not in FACES:
        raise FrameRefused("unknown-value", "face", face)
    if gesture is not None and gesture not in GESTURES:
        raise FrameRefused("unknown-value", "gesture", gesture)
    if sound is not None and sound not in SOUNDS:
        raise FrameRefused("unknown-value", "sound", sound)
    return Command(light=light, face=face, gesture=gesture, sound=sound)
