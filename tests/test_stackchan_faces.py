# -*- coding: utf-8 -*-
"""**顔の語は、4つの場所で同じ8語でなければならない。**

⛔ **なぜ要るか。** 語は5か所に書かれている——Pet の `State`（5語）、この体の
`Face`（8語）、電線の `FACES`、契約の `enum`、ファームの C++ の綴り。
⚠️ **写しは黙ってずれる。** そして 2026-10-24 まで、**この突き合わせは
どの検査もしていなかった**——`engine/backend/protocol_stackchan.py` の註と
`schemas/stackchan-command.schema.json` の説明は、そろって
「`tests/test_stackchan_wire.py` が食い違いを見る」と書いていたが、
**その検査は存在しなかった**。⚠️ 規則が書かれ、検査が無く、**緑のまま**だった。

⇒ **このファイルが、その検査である。** 語を1つ足して4か所のどれかを忘れれば、
ここが赤くなる。

## ⛔ このファイルが確かめないこと

- **形。** 語が指す絵は `tests/test_stackchan_face.py` が画素で見る。
- **機械の上で動くこと。** ここは文字列と表だけを読む。
"""
from __future__ import annotations

import json
import pathlib
import re

from engine.backend import protocol_stackchan as wire
from projects.pet.expressions import State
from projects.stackchan.faces import FACES, PET_FACES, Face, art

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE = REPO_ROOT / "projects" / "stackchan-firmware"
SCHEMA = REPO_ROOT / "schemas" / "stackchan-command.schema.json"


def test_the_body_has_eight_words():
    """⚠️ **8語。** 同じ綴りが2度出てこないこと。"""
    words = [face.value for face in Face]
    assert len(words) == 8, f"8語ではない: {words}"
    assert len(set(words)) == 8, f"同じ語が2度ある: {words}"


def test_the_pets_five_are_the_first_five_and_are_the_pets():
    """⚠️ **先頭5語は Pet の5語そのものである**——値は `State` から取っているので、
    綴りが食い違うことは構造上ありえない。**ここが測るのは、顔の集合と並びである。**

    ⛔ **並びは `State` の並びではない**——`State` の宣言順は `happy` から始まり、
    電線の並びは `curious` から始まる。**同じ5語であることと、同じ順であることを
    混ぜない**（2026-10-24、ここで一度混ぜて赤くなった）。
    """
    assert {face.value for face in PET_FACES} == {state.value for state in State}
    assert PET_FACES == FACES[: len(PET_FACES)], "Pet の5語が先頭に無い"


def test_the_body_added_three_words_of_its_own():
    """⛔ **この機体の3語は Pet のものではない**——`State` は増えない。

    ⚠️ 名前は**意味**に対して付けた。形は目の判定で変わるが、語は変わらない。
    """
    own = [face.value for face in FACES if face not in PET_FACES]
    assert own == ["focused", "watching", "startled"]
    assert not ({state.value for state in State} & set(own))


def test_the_wire_names_the_same_eight():
    """⚠️ **電線の `FACES` は `Face` の写しである**——並びまで同じでなければならない。"""
    assert wire.FACES == tuple(face.value for face in Face)


def test_the_contract_names_the_same_eight():
    """⚠️ **契約の `enum` は電線の写しである。**"""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["face"]["enum"] == [*wire.FACES, None]


def test_the_firmware_names_the_same_eight():
    """⚠️ **ファームの綴りは2か所にある**——電線のパーサと、コンソールの `bench face`。

    ⛔ この2つが別々なのは意図である（`bench` は4欄の枠を組まずに図を1つ出す）。
    だから**両方を読む**——片方だけ足した版が、緑のまま焼かれることのないように。
    """
    frame = (FIRMWARE / "command_frame.cpp").read_text(encoding="utf-8")
    for word in wire.FACES:
        assert f'"{word}"' in frame, f"command_frame.cpp に {word} が無い"

    console = (FIRMWARE / "main" / "main.cpp").read_text(encoding="utf-8")
    table = console.split("bool FaceFromName(const char* name, int length, Face* out) {", 1)[
        1
    ].split("\n}", 1)[0]
    named = re.findall(r'\{"([a-z]+)", Face::k[A-Za-z]+\}', table)
    assert named == list(wire.FACES), f"bench face の表が電線と違う: {named}"


def test_the_firmware_can_print_every_face_word():
    """⚠️ **`FaceName` は `main.cpp` に在り、どの検査もコンパイルしない。**

    ⛔ **語を足して名前を忘れれば、受理の行が `?` になる**——そして 0.19.41 から、
    **その行が枠の受理そのものである**（`accepted` は基板の行である）。
    """
    source = (FIRMWARE / "main" / "main.cpp").read_text(encoding="utf-8")
    body = source.split("const char* FaceName(Face face) {", 1)[1].split("\n}", 1)[0]
    for word in wire.FACES:
        assert f'"{word}"' in body, f"FaceName が {word} を綴らない"


def test_the_pets_faces_have_a_drawing_here_and_the_bodys_do_not():
    """⛔ **Pet の5つには ASCII の図が在り、この機体の3つには無い。**

    ⚠️ 図はこのリポジトリの `projects/pet/expressions.py` にあり、この体の3語の図は
    **C++（`face_bitmap.cpp`）にしかない**。⇒ 日誌の読み手が語を図にしようとしたとき、
    **空を返すのが正しい**——無いものを発明しない。
    """
    for face in PET_FACES:
        assert art(face), f"{face.value} の図が無い"
    for face in FACES:
        if face not in PET_FACES:
            assert art(face) == (), f"{face.value} に図があるはずがない"


def test_a_row_from_a_day_can_name_a_body_face():
    """⚠️ **日誌の行は語を持つ**——`Face("focused")` が作れなければ、その行は読めない。

    ⛔ ここが落ちる形は2つある: 語を電線に足して `Face` に足さない日と、
    その逆の日である。**`test_the_wire_names_the_same_eight` が両方を押さえる。**
    """
    for word in wire.FACES:
        assert Face(word).value == word
