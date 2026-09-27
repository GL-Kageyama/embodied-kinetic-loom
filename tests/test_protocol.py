# -*- coding: utf-8 -*-
"""フレーム——**5バイト、チェックサム無し。**

⛔ **このファイルの中心は `test_a_bracket_inside_the_payload_does_not_split_the_frame` である。**
目標 347 = `0x015B` の下位バイトが `0x5B`＝`[` である。
**「`[` を探して切る」パーサは、ここで静かに壊れる**——**そして壊れ方が、
「フレームが1つずれる」である。** ずれたフレームは、**別のモーターへの段差になる。**
"""
from __future__ import annotations

import pytest

from engine.backend.protocol import (
    END, FRAME_LEN, MAX_TARGET, START,
    ProtocolError, decode_frames, encode_target, feedback_div4,
)


# --------------------------------------------------------------------------
# 組む
# --------------------------------------------------------------------------


def test_a_frame_is_five_bytes_bracketed():
    frame = encode_target(0, 512)
    assert len(frame.raw) == FRAME_LEN
    assert frame.raw == bytes((START, ord("A"), 0x02, 0x00, END))


def test_the_position_is_big_endian():
    assert encode_target(1, 0x015B).raw[2:4] == bytes((0x01, 0x5B))
    assert encode_target(1, 0x015B).value == 347


def test_the_motor_letter_maps_to_a_number():
    assert encode_target(2, 190).motor() == 2
    assert encode_target(2, 190).command == "C"


def test_out_of_range_is_refused_rather_than_rounded():
    """⛔ **丸めない。** 丸めると、呼ぶ側は枠を出たことを知らないまま進む。"""
    with pytest.raises(ProtocolError, match="収まらない"):
        encode_target(0, MAX_TARGET + 1)
    with pytest.raises(ProtocolError, match="収まらない"):
        encode_target(0, -1)


def test_a_boolean_is_not_a_position():
    """⚠️ **`True` は `1` である。** 黙って通すと、位置1へ飛ぶ。"""
    with pytest.raises(ProtocolError, match="整数"):
        encode_target(0, True)


# --------------------------------------------------------------------------
# 切る
# --------------------------------------------------------------------------


def test_a_whole_frame_round_trips():
    raw = encode_target(1, 700).raw
    frames, rest = decode_frames(raw)
    assert len(frames) == 1
    assert frames[0].value == 700
    assert rest == b""


def test_a_bracket_inside_the_payload_does_not_split_the_frame():
    """⛔ **`0x5B` は payload に現れる。** 目標347の下位バイトである。"""
    raw = encode_target(1, 347).raw
    assert raw[3] == START, "前提: この目標の下位バイトが `[` であること"
    frames, rest = decode_frames(raw)
    assert len(frames) == 1 and frames[0].value == 347 and rest == b""


def test_a_partial_frame_is_kept_not_consumed():
    """⚠️ **まだ足りない分は、次へ渡す。** ここで切ると、次に来た `]` を飲み込む。"""
    raw = encode_target(0, 512).raw
    frames, rest = decode_frames(raw[:3])
    assert frames == () and rest == raw[:3]
    frames, rest = decode_frames(rest + raw[3:])
    assert len(frames) == 1 and rest == b""


def test_garbage_before_a_frame_is_skipped():
    raw = encode_target(0, 512).raw
    frames, rest = decode_frames(b"\x00\xff" + raw)
    assert len(frames) == 1 and rest == b""


def test_a_bad_end_byte_does_not_swallow_the_next_frame():
    """⛔ **捨てて1バイト進める。** 5バイト捨てると、**次のフレームの頭を食う。**"""
    raw = encode_target(0, 512).raw
    broken = bytes((START, ord("A"), 0x00, 0x00, 0x5B, 0x7F))  # 終端が `]` でない
    frames, rest = decode_frames(broken + raw)
    assert len(frames) == 1, "壊れたフレームの後ろの、正しいフレームが消えた"
    assert frames[0].value == 512 and rest == b""


def test_two_frames_in_one_read():
    raw = encode_target(0, 512).raw + encode_target(2, 300).raw
    frames, rest = decode_frames(raw)
    assert [f.value for f in frames] == [512, 300] and rest == b""


def test_an_empty_list_command_does_not_exist():
    """⛔ **`[]` は2バイトなので、パーサは後続3バイトを飲み込む**（§1.1）。"""
    frames, rest = decode_frames(b"[]" + encode_target(0, 512).raw)
    assert len(frames) == 1 and frames[0].value == 512


# --------------------------------------------------------------------------
# 読む——⛔ 単位が違う
# --------------------------------------------------------------------------


def test_a_read_reading_is_one_byte_not_two():
    """⛔ **送る側の 0〜1024 と混ぜない。** 読む側は `0〜255`＝位置の4分の1である。"""
    with pytest.raises(ProtocolError, match="混ぜない"):
        feedback_div4(0, 300, 0)
    reading = feedback_div4(0, 128, 127)
    assert (reading.feedback, reading.target) == (128, 127)
