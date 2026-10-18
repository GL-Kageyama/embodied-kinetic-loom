# -*- coding: utf-8 -*-
"""**機体2の電線——記号だけが渡り、数は1つも渡らない。**

⚠️ **2つに分かれている。** 符号化と復号は純粋な関数であり、プロセスもソケットも
要らない。モックはその2つを順に呼ぶだけの器である。

⛔ **このファイルが確かめないこと:** 機体2へ届くこと、ボーレート、伝送路、そして
**焼いたファームが動くこと**。**`sent` は依然 `False` であり、電線はまだ何にも
繋がっていない**——ここが確かめるのは、行の形と、契約との一致だけである。
"""
from __future__ import annotations

import ast
import json
import pathlib

import pytest

from engine.backend import protocol_stackchan as wire
from engine.backend.mock_stackchan import MockStackchan

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "schemas" / "stackchan-command.schema.json"
FIRMWARE = REPO_ROOT / "projects" / "stackchan-firmware"


# ---------------------------------------------------------------------------
# 中核。⛔ プロセスもソケットも無い。
# ---------------------------------------------------------------------------


def test_every_symbol_round_trips():
    """⚠️ **6 × 6 × 6 × 5 ＝ 1,080 の枠**（顔6・光6・身振り6・音5、うち `null` を
    1つも持たないものが5×5×5＝125）。**すべてが戻る。**"""
    for face in (None, *wire.FACES):
        for light in wire.LIGHTS:
            for gesture in (None, *wire.GESTURES):
                for sound in (None, *wire.SOUNDS):
                    command = wire.Command(
                        light=light, face=face, gesture=gesture, sound=sound
                    )
                    assert wire.decode(wire.encode(command)) == command


def test_a_frame_is_one_ascii_line():
    """⚠️ **1枠＝1行。** 改行は最後の1つだけで、中身は ASCII である。"""
    line = wire.encode(
        wire.Command(light="warm", face="happy", gesture="nod", sound="chime")
    )
    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1
    line.decode("ascii")


def test_null_is_a_value_not_a_missing_field():
    """⛔ **欄は4つとも常に在る。** 欠けた欄は、受け取る側が前の値で埋めてしまう。"""
    body = json.loads(wire.encode(wire.Command(light="dim")))
    assert set(body) == {"face", "light", "gesture", "sound"}
    assert body["face"] is None
    assert body["gesture"] is None
    assert body["sound"] is None


def test_an_unknown_key_is_refused():
    """⛔ **プロンプトは、この電線を渡らない。** 無視される欄は同乗できる。"""
    line = b'{"face":null,"light":"dim","gesture":null,"sound":null,"prompt":"secret"}\n'
    with pytest.raises(wire.FrameRefused) as caught:
        wire.decode(line)
    assert caught.value.code == "unknown-key"
    assert caught.value.field == "prompt"


@pytest.mark.parametrize(
    "field, value",
    [
        ("face", "proud"),
        ("light", "rainbow"),
        ("gesture", "bow"),
        ("sound", "horn"),
    ],
)
def test_an_unknown_value_is_refused(field, value):
    """⛔ **表の外の語は、語彙の外である**（`references/README.md`）。"""
    body = {"face": None, "light": "dim", "gesture": None, "sound": None}
    body[field] = value
    with pytest.raises(wire.FrameRefused) as caught:
        wire.decode((json.dumps(body) + "\n").encode())
    assert caught.value.code == "unknown-value"
    assert caught.value.field == field


def test_light_is_required_and_never_null():
    """⚠️ **光は常時チャンネルである。** `null` は「変えない」ではなく、欠けた値である。"""
    with pytest.raises(wire.FrameRefused) as caught:
        wire.decode(b'{"face":"happy","light":null,"gesture":"nod","sound":null}\n')
    assert caught.value.code == "missing-key"
    with pytest.raises(wire.FrameRefused) as caught:
        wire.decode(b'{"face":"happy","gesture":"nod","sound":null}\n')
    assert caught.value.code == "missing-key"


def test_sound_is_required_and_may_be_null():
    """⚠️ **音は事象である。** `null` は「この枠は鳴らない」であり、
    **欠けた欄ではない**——欠けた欄は、受け取る側が前の値で埋めてしまう。"""
    with pytest.raises(wire.FrameRefused) as caught:
        wire.decode(b'{"face":"happy","light":"warm","gesture":"nod"}\n')
    assert caught.value.code == "missing-key"
    assert caught.value.field == "sound"

    command = wire.decode(
        b'{"face":null,"light":"dim","gesture":null,"sound":"pip"}\n'
    )
    assert command.sound == "pip"


def test_a_sound_is_a_word_and_not_a_number():
    """⛔ **周波数も長さも、この電線を通らない。** 語から音への表はファームに在る。"""
    body = json.loads(wire.encode(wire.Command(light="warm", sound="chime")))
    assert isinstance(body["sound"], str)
    assert all(word.isalpha() for word in wire.SOUNDS)


@pytest.mark.parametrize(
    "line",
    [
        b"",
        b"[]\n",
        b'"frame"\n',
        b'{"face":"happy","light":"dim","gesture":"nod"}\n{"face":null,"light":"off","gesture":null}\n',
        b'{"face":"happy","light":"dim","gesture":"nod"',
        b'\xff\xfe\n',
    ],
)
def test_malformed_lines_are_refused(line):
    """⛔ **読めない行は、読めないと言う。** 黙って飲み込むのは、電線の仕事ではない。"""
    with pytest.raises(wire.FrameRefused):
        wire.decode(line)


def test_two_lines_are_refused():
    """⚠️ **1つの枠は1行である。** 行をまたぐ状態は、この層に無い。"""
    one = wire.encode(wire.Command(light="dim"))
    with pytest.raises(wire.FrameRefused) as caught:
        wire.decode(one + one)
    assert caught.value.code == "malformed"


def test_a_long_line_is_refused():
    """⚠️ **上限はプロトコルの縛りであり、機体の測定ではない。**"""
    line = b'{"face":null,"light":"dim","gesture":null}' + b" " * wire.MAX_LINE + b"\n"
    with pytest.raises(wire.FrameRefused) as caught:
        wire.decode(line)
    assert caught.value.code == "too-long"


def test_encode_refuses_what_decode_refuses():
    """⛔ **書く側と読む側が、別々の規則を持たないこと。**"""
    for bad in (
        wire.Command(light="rainbow"),
        wire.Command(light="dim", face="proud"),
        wire.Command(light="dim", gesture="bow"),
        wire.Command(light="dim", sound="horn"),
    ):
        with pytest.raises(wire.FrameRefused) as caught:
            wire.encode(bad)
        assert caught.value.code == "unknown-value"


# ---------------------------------------------------------------------------
# 契約。⚠️ 3か所が同じ語を綴るので、食い違った日に赤くなる。
# ---------------------------------------------------------------------------


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_the_contract_and_the_codec_agree():
    """⚠️ **契約と符号器は、同じ語を2回綴っている。** 写しは、食い違うまで無害である。"""
    properties = _schema()["properties"]
    assert set(properties["face"]["enum"]) == {None, *wire.FACES}
    assert set(properties["light"]["enum"]) == set(wire.LIGHTS)
    assert set(properties["gesture"]["enum"]) == {None, *wire.GESTURES}
    assert set(properties["sound"]["enum"]) == {None, *wire.SOUNDS}


def test_the_contract_is_closed():
    """⛔ **開いた契約は、誰かが欄を足したことに気づかない形である。**"""
    schema = _schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"face", "light", "gesture", "sound"}


def test_no_sound_field_is_missing_from_the_contract():
    """⛔ **音の欄は、契約・符号器・モックの3か所に同時に在る。**

    ⚠️ 2026-10-18 まで、この検査は「`sound` がどこにも無いこと」を確かめていた——
    **欄が着いた日、同じ検査が反対を向く。** 無いことを守る検査ではなく、
    **在ることを守る検査**に書き換えたのは、欄が先に着いて検査が後を追う形を作らないためである。
    """
    assert set(_schema()["properties"]) == {"face", "light", "gesture", "sound"}
    assert "sound" in wire.Command.__dataclass_fields__
    assert "sound" in json.loads(wire.encode(wire.Command(light="dim")))


def test_the_firmware_names_the_same_words():
    """⛔ **ファームの綴りは写しである。** 写しが食い違った日に赤くなる。"""
    source = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(FIRMWARE.glob("command_frame.*"))
    )
    for word in (*wire.FACES, *wire.LIGHTS, *wire.GESTURES, *wire.SOUNDS):
        assert f'"{word}"' in source


def test_the_firmware_has_no_angle_for_either_machine():
    """⛔ **角度を発明していないこと。** 機体1の数も、機体2の数も、このソースには無い。"""
    source = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted(FIRMWARE.glob("command_frame.*"))
    )
    for number in ("190", "512", "833", "455", "603", "460", "620", "DofReality"):
        assert number not in source


# ---------------------------------------------------------------------------
# 電線は、機体1の数を1つも持ち込まない。
# ---------------------------------------------------------------------------


def test_the_wire_imports_nothing_but_json_and_dataclasses():
    """⚠️ **時計も、ソケットも、環境も読まない。** ゆえに純粋である。

    ⛔ **機体1の `protocol` を輸入しないこと**——2台目は、あの数も軸も共有しない。
    """
    tree = ast.parse(
        (REPO_ROOT / "engine" / "backend" / "protocol_stackchan.py").read_text(
            encoding="utf-8"
        )
    )
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    assert names == {"__future__", "dataclasses", "json"}


# ---------------------------------------------------------------------------
# モック。⚠️ 緑はプロトコルの緑であり、機体の緑ではない。
# ---------------------------------------------------------------------------


def test_the_mock_records_and_answers_nothing():
    """⛔ **返事を返さないことが、この型の正しい振る舞いである。**"""
    mock = MockStackchan()
    assert mock.last() is None
    assert mock.count() == 0
    first = wire.Command(light="warm", face="greeting", gesture="look_up")
    second = wire.Command(light="dim", face="curious")
    assert mock.send(wire.encode(first)) is None
    assert mock.send(wire.encode(second)) is None
    assert mock.count() == 2
    assert mock.sent == [first, second]
    assert mock.last() == second


def test_the_mock_refuses_what_the_wire_refuses():
    """⚠️ **モックの厳しさは、ホスト側の符号化を試すためのものである。**"""
    mock = MockStackchan()
    with pytest.raises(wire.FrameRefused):
        mock.send(b'{"face":null,"light":"dim","gesture":null,"prompt":"secret"}\n')
    assert mock.count() == 0
