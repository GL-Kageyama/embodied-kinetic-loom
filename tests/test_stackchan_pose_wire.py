# -*- coding: utf-8 -*-
"""**機体2の2本目の線——姿勢が、刻みごとに1行で渡る。**

⚠️ **2つに分かれている。** 符号化と復号は純粋な関数であり、プロセスもソケットも
時計も要らない。モックはその2つを順に呼ぶだけの器である。

⛔ **このファイルが確かめないこと:** 機体2へ届くこと、伝送路、**20 ms ごとに目標を
書き換え続けることがこの個体で生き延びること**、そして**焼いたファームがその行を読むこと**
——**基板の側はまだ1行も書かれていない。** ここが確かめるのは、行の形と、契約との一致である。
"""
from __future__ import annotations

import ast
import json
import pathlib
import re

import pytest

from engine.backend import protocol_stackchan_pose as pose
from engine.backend.mock_stackchan import MockStackchanPose
from engine.backend.protocol_stackchan import FrameRefused
from engine.backend.wire import Command

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = REPO_ROOT / "schemas" / "stackchan-pose.schema.json"

#: ⚠️ **7 × 7 ＝ 49 の姿勢。** 端（±1800）を両方の欄に入れてある。
YAW = (-1800, -200, -50, 0, 50, 200, 1800)
PITCH = (-1800, -10, 0, 30, 894, 1700, 1800)


# ---------------------------------------------------------------------------
# 中核。⛔ プロセスもソケットも時計も無い。
# ---------------------------------------------------------------------------


def test_every_pose_round_trips():
    """⚠️ **7 × 7 ＝ 49 の姿勢が、すべて戻る。** 端も含めて。"""
    for yaw in YAW:
        for pitch in PITCH:
            one = pose.Pose(yaw_tenths=yaw, pitch_tenths=pitch)
            assert pose.decode(pose.encode(one)) == one


def test_a_pose_is_one_ascii_line():
    """⚠️ **1姿勢＝1行、ASCII。** 改行は最後の1つだけである。"""
    line = pose.encode(pose.Pose(50, 894))
    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1
    line.decode("ascii")
    assert line.startswith(b"pose ")


def test_the_checksum_is_hand_computable():
    """⚠️ **和は、手で数えられる。** `pose 50 894` の全バイトの和は 769、下位8ビットは 1。

    ⛔ **この数を手で確かめてあることが、基板の側の C++ を同じ3行で書ける根拠である。**
    """
    assert pose.checksum(b"pose 50 894") == "01"
    assert pose.encode(pose.Pose(50, 894)) == b"pose 50 894*01\n"


def test_a_corrupted_byte_is_refused():
    """⛔ **1バイトの化けは、和が捕まえる。** 12.5° の誤りが、そのまま動く前に。"""
    with pytest.raises(FrameRefused) as caught:
        pose.decode(b"pose 90 894*01\n")
    assert caught.value.code == "bad-checksum"


def test_a_transposed_digit_is_caught_by_the_spelling_not_the_checksum():
    """⚠️ **`50` → `05` は和が同じである。** 捕まえるのは**正準形の規則**のほうである。

    ⛔ **これは和の限界を閉じるのではなく、閉じられる範囲だけを閉じている**——
    `123` → `321` は、和も正準形も通る（下の `test_the_sum_does_not_catch_every_transposition`）。
    """
    with pytest.raises(FrameRefused) as caught:
        pose.decode(b"pose 05 894*01\n")
    assert caught.value.code == "malformed"
    assert caught.value.field == "value"


def test_the_sum_does_not_catch_every_transposition():
    """⛔ **明記された限界である。** 桁の入れ替えが先頭の0を作らなければ、和は通す。

    ⚠️ **これを性質だと思わないこと。** CRC にしなかった理由は `protocol_stackchan_pose.py`
    の但し書きにある——**基板の側の行数である。**
    """
    line = b"pose 132 894*" + pose.checksum(b"pose 123 894").encode() + b"\n"
    assert pose.decode(line) == pose.Pose(132, 894)


def test_a_line_of_the_other_kind_is_refused():
    """⛔ **遷移の枠は、この線の行ではない。** 2本は最初の語で分かれる。"""
    frame = b'{"face":null,"light":"dim","gesture":null}\n'
    with pytest.raises(FrameRefused) as caught:
        pose.decode(frame)
    assert caught.value.code == "not-pose"
    assert caught.value.value.startswith("{")


@pytest.mark.parametrize(
    "line",
    [
        b"",
        b"pose\n",
        b"pose 50 894\n",
        b"pose 50 894*\n",
        b"pose 50 894*0\n",
        b"pose 50 894*001\n",
        b"pose 50 894*0a\n",
        b"pose  50 894*00\n",
        b"pose 50 894 " + b"0" * 64 + b"\n",
        b"pose 50 894*01\npose 50 894*01\n",
        b"\xff\xfe\n",
    ],
)
def test_malformed_lines_are_refused(line):
    """⛔ **読めない行は、読めないと言う。** 黙って飲み込むのは、電線の仕事ではない。"""
    with pytest.raises(FrameRefused):
        pose.decode(line)


def test_both_fields_are_always_present():
    """⛔ **欄は2つとも常に在る。** 欠けた欄は、受け取る側が前の値で埋めてしまう。"""
    body = b"pose 50"
    with pytest.raises(FrameRefused) as caught:
        pose.decode(b"pose 50*" + pose.checksum(body).encode() + b"\n")
    assert caught.value.code == "malformed"
    extra = b"pose 50 894 0"
    with pytest.raises(FrameRefused) as caught:
        pose.decode(b"pose 50 894 0*" + pose.checksum(extra).encode() + b"\n")
    assert caught.value.code == "malformed"


def test_a_long_line_is_refused():
    """⚠️ **上限はプロトコルの縛りであり、機体の測定ではない。**"""
    line = pose.encode(pose.Pose(-1800, -1800))
    assert len(line) <= pose.MAX_LINE
    with pytest.raises(FrameRefused) as caught:
        pose.decode(line + b" " * pose.MAX_LINE + b"\n")
    assert caught.value.code == "too-long"


def test_the_limit_is_the_protocols_and_not_the_machines():
    """⛔ **1800 は桁の健全性であって、機体の可動域ではない。**

    機体の枠（この個体がどこまで回れるか）は**基板の側にあり**、ホストはそれを知らない。
    ⚠️ **ここで 1800 を通すことが、機体が 180° 回れるという主張ではない。**
    """
    assert pose.decode(pose.encode(pose.Pose(1800, -1800))) == pose.Pose(1800, -1800)
    with pytest.raises(FrameRefused) as caught:
        pose.encode(pose.Pose(1801, 0))
    assert caught.value.code == "out-of-range"
    body = b"pose 1801 0"
    with pytest.raises(FrameRefused) as caught:
        pose.decode(b"pose 1801 0*" + pose.checksum(body).encode() + b"\n")
    assert caught.value.code == "out-of-range"


def test_encode_refuses_what_decode_refuses():
    """⛔ **書く側と読む側が、別々の規則を持たないこと。**"""
    for bad in (
        pose.Pose(1801, 0),
        pose.Pose(0, -1801),
        pose.Pose("50", 894),  # type: ignore[arg-type]
        pose.Pose(True, 894),
    ):
        with pytest.raises(FrameRefused):
            pose.encode(bad)


# ---------------------------------------------------------------------------
# 電線。⚠️ `Wire` の3つのメソッドを持つ。
# ---------------------------------------------------------------------------


def test_the_wire_has_two_axes():
    """⚠️ **軸は yaw と pitch の2つである。**"""
    assert pose.StackChanPoseWire().axis_count() == 2


def test_quantize_rounds_to_a_tenth_of_a_degree():
    """⚠️ **この線は 0.1° より細かい値を表せない。** 丸めは送る値を変える。"""
    wire = pose.StackChanPoseWire()
    assert wire.quantize(12.36) == 12.4
    assert wire.quantize(-12.36) == -12.4
    assert wire.quantize(50.0) == 50.0


def test_the_wire_turns_a_pair_into_one_line():
    """⚠️ **軸0が1欄目（yaw）、軸1が2欄目（pitch）である。** 順序はこの線の上の約束である。"""
    wire = pose.StackChanPoseWire()
    commands = [Command(axis=0, value=50.0), Command(axis=1, value=89.4)]
    assert wire.encode(commands) == pose.encode(pose.Pose(500, 894))


def test_an_empty_set_is_empty_bytes():
    """⚠️ **まだ1つも通していない門の `hold()` がこれである。** 空を「停止」と読む機体は無い。"""
    assert pose.StackChanPoseWire().encode([]) == b""


@pytest.mark.parametrize(
    "commands, code",
    [
        ([Command(axis=0, value=50.0)], "missing-axis"),
        ([Command(axis=2, value=50.0), Command(axis=1, value=89.4)], "unknown-axis"),
        ([Command(axis=0, value=50.0), Command(axis=0, value=60.0)], "duplicate-axis"),
    ],
)
def test_half_or_confused_poses_are_refused(commands, code):
    """⛔ **半分の姿勢は表せない。** 欄は2つとも常に書く。"""
    with pytest.raises(FrameRefused) as caught:
        pose.StackChanPoseWire().encode(commands)
    assert caught.value.code == code


# ---------------------------------------------------------------------------
# 契約。⚠️ 形は契約が、和は符号器が見る。⛔ 互いを覆わない。
# ---------------------------------------------------------------------------


def _schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_the_contract_accepts_every_line_the_codec_writes():
    """⚠️ **契約の正規表現は、符号器が出しうる行をすべて受け取る。**"""
    pattern = re.compile(_schema()["pattern"])
    for yaw in YAW:
        for pitch in PITCH:
            line = pose.encode(pose.Pose(yaw, pitch)).decode("ascii")
            assert pattern.fullmatch(line), line


@pytest.mark.parametrize(
    "line",
    [
        "pose 50 894\n",
        "pose 50 894*\n",
        "pose 50 894*0\n",
        "pose 50 894*0a\n",
        "pose  50 894*0A\n",
        "pose 50 894*0A\r\n",
        "turn 50 894*0A\n",
    ],
)
def test_the_contract_refuses_what_is_not_a_pose_line(line):
    """⛔ **契約は形だけを見る。** 和が正しいかは見ない——それは符号器の仕事である。"""
    assert re.fullmatch(_schema()["pattern"], line) is None


def test_the_contract_and_the_codec_word_the_line_the_same_way():
    """⚠️ **同じ行を2か所が綴っている。** 写しは、食い違うまで無害である。"""
    schema = _schema()
    assert schema["type"] == "string"
    assert schema["maxLength"] == pose.MAX_LINE
    assert "pose" in schema["pattern"]
    assert "yaw" in schema["description"]
    assert "pitch" in schema["description"]


# ---------------------------------------------------------------------------
# 機体1の数を、1つも持ち込まない。
# ---------------------------------------------------------------------------


def test_the_module_imports_nothing_but_the_two_layers():
    """⚠️ **時計も、ソケットも、環境も読まない。** ゆえに純粋である。

    ⛔ **機体1の `protocol` を輸入しないこと**——2台目は、あの数も軸も共有しない。
    """
    tree = ast.parse(
        (REPO_ROOT / "engine" / "backend" / "protocol_stackchan_pose.py").read_text(
            encoding="utf-8"
        )
    )
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    assert names == {"__future__", "dataclasses", "typing"}


def test_no_number_of_machine_1_or_of_this_unit_appears():
    """⛔ **機体1の数も、この個体のゼロ点も、このソースには無い。**

    ⚠️ **ゼロ点がここに在るとき、それは写しである**——正典は機体の NVS と記録である。
    """
    source = (REPO_ROOT / "engine" / "backend" / "protocol_stackchan_pose.py").read_text(
        encoding="utf-8"
    )
    for number in ("190", "512", "833", "460", "620", "DofReality"):
        assert number not in source


# ---------------------------------------------------------------------------
# モック。⚠️ 緑はプロトコルの緑であり、機体の緑ではない。
# ---------------------------------------------------------------------------


def test_the_mock_records_and_answers_nothing():
    """⛔ **返事を返さないことが、この型の正しい振る舞いである。**"""
    mock = MockStackchanPose()
    assert mock.last() is None
    assert mock.count() == 0
    first = pose.Pose(50, 894)
    second = pose.Pose(60, 894)
    assert mock.send(pose.encode(first)) is None
    assert mock.send(pose.encode(second)) is None
    assert mock.count() == 2
    assert mock.sent == [first, second]
    assert mock.last() == second


def test_the_mock_refuses_what_the_wire_refuses():
    """⚠️ **モックの厳しさは、ホスト側の符号化を試すためのものである。**"""
    mock = MockStackchanPose()
    with pytest.raises(FrameRefused):
        mock.send(b"pose 90 894*01\n")
    assert mock.count() == 0
