# -*- coding: utf-8 -*-
"""**声の間。**

⚠️ **鳴らしてはいない。** ここが測るのは**文字とミリ秒**であり、
**耳に届いたかどうかではない**——4つの音を耳だけで判定したのと同じ境界である。

⛔ **このファイルは `say` を呼ばない。** 声を作るのは縁（`__main__`）の仕事であり、
規則は音を持たない（`test_pet_purity.py` が同じことを輸入の側から押さえる）。
"""
from __future__ import annotations

import pytest

from projects.stackchan.voice import render
from projects.stackchan.voice.render import PITCH, PAUSE_MS, gap_frames, pitched, segments, spoken


# ---------------------------------------------------------------------------
# 規則。⛔ 音も時計も無い。
# ---------------------------------------------------------------------------


def test_the_pauses_are_the_author_s_choice():
    """⚠️ **著者の裁定（2026-10-21）。** 2案を鳴らし、600/300 が選ばれた。"""
    assert PAUSE_MS == {"。": 600, "、": 300}


def test_a_full_stop_gets_six_hundred():
    assert segments("終わりました。次は") == [
        ("終わりました。", 600),
        ("次は", 0),
    ]


def test_a_comma_gets_three_hundred():
    assert segments("書く、実行する") == [
        ("書く、", 300),
        ("実行する", 0),
    ]


def test_the_mark_stays_in_the_piece():
    """⛔ **記号を落とすと、`say` は文の終わりを知らない**——間だけ足して抑揚を奪う。"""
    for piece, _ in segments("終わりました。次は、走ります。"):
        assert piece


def test_the_last_piece_gets_no_silence():
    """⛔ **文末の無音は、間ではなく空白である。**"""
    assert segments("終わりました。") == [("終わりました。", 0)]


def test_the_last_piece_gets_no_silence_without_a_final_mark():
    assert segments("終わりました") == [("終わりました", 0)]


def test_exclamation_and_question_are_left_alone():
    """⚠️ **数は2つの記号にしか無い。** 強さをミリ秒で決める根拠は無い。"""
    assert segments("本当ですか？すごい！") == [("本当ですか？すごい！", 0)]


def test_a_text_without_marks_is_one_piece():
    assert segments("そのまま") == [("そのまま", 0)]


def test_empty_text_has_no_pieces():
    assert segments("") == []


# ---------------------------------------------------------------------------
# `say` へ渡す本文。
# ---------------------------------------------------------------------------


def test_the_command_is_written_where_the_pause_is():
    said = spoken("終わりました。次は、走ります。")
    assert said == "終わりました。[[slnc 600]]次は、[[slnc 300]]走ります。"


def test_no_command_at_the_end():
    assert "[[slnc" not in spoken("終わりました。")


def test_the_text_is_otherwise_untouched():
    """⚠️ **間を足しても、語は1字も変わらない。**"""
    text = "長いターンでした。そのうち25回、書くが続いていました。"
    assert render.spoken(text).replace("[[slnc 600]]", "").replace(
        "[[slnc 300]]", ""
    ) == text


# ---------------------------------------------------------------------------
# 断片を焼くときの無音。
# ---------------------------------------------------------------------------


def test_frames_are_the_rate_times_the_milliseconds():
    assert gap_frames(600, 24000) == 14400
    assert gap_frames(300, 24000) == 7200


def test_frames_round_down():
    """⚠️ **足りない側へ倒す**——長い無音は間であり、短い無音は間である。"""
    assert gap_frames(1, 1000) == 1
    assert gap_frames(1, 999) == 0


def test_a_negative_pause_is_named():
    with pytest.raises(ValueError):
        gap_frames(-1, 24000)


def test_a_zero_rate_is_named():
    with pytest.raises(ValueError):
        gap_frames(600, 0)


# ---------------------------------------------------------------------------
# 声の高さ。⚠️ **著者の言葉は「もうちょっと可愛らしい声で喋って」である。**
# ---------------------------------------------------------------------------


def test_the_pitch_is_the_author_s_choice():
    """⚠️ **+6 は著者の耳が選ぶまでの値である。** 実測で F0 218 → 276 Hz。"""
    assert PITCH == 6


def test_the_pitch_is_written_before_the_text():
    """⛔ **`say` の命令であり、SSML ではない。** 綴りが違えば記号のまま読まれる。"""
    assert pitched("終わりました。", 6) == "[[pbas +6]]終わりました。"


def test_the_pitch_keeps_its_sign():
    """⚠️ **負の高さも書ける形にしておく**——符号を落とすと、+3 と -3 が同じ文字列になる。"""
    assert pitched("あ", -3) == "[[pbas -3]]あ"
    assert pitched("あ", 3) == "[[pbas +3]]あ"


# ---------------------------------------------------------------------------
# つなぎ。⛔ **`say` に間を任せない**——設計 §22.3 が選んだ形はこちらである。
# ---------------------------------------------------------------------------


def test_the_ends_are_cut_and_the_middle_is_not():
    """⛔ **中の無音は語と語の間である。** 切るのは端だけ。"""
    from projects.stackchan.voice.wav import trim

    assert trim([0, 5, 900, 0, 0, 900, 5, 0]) == [900, 0, 0, 900]


def test_a_quiet_piece_is_empty():
    """⚠️ **閾値より静かな断片は、空になる**——無音を「間」として数えないため。"""
    from projects.stackchan.voice.wav import trim

    assert trim([0, 100, -199]) == []


def test_the_join_puts_exactly_the_rule_s_between_the_pieces():
    from projects.stackchan.voice.wav import join

    out = join([[1, 2], [3]], [600, 0], 24000)
    assert out[:2] == [1, 2]
    assert out[2:2 + 14400] == [0] * 14400
    assert out[-1] == 3


def test_a_missing_pause_is_named():
    """⛔ **足りない間を 0 で埋めない**——「間なし」は規則の不在であって、既定ではない。"""
    from projects.stackchan.voice.wav import join

    with pytest.raises(ValueError):
        join([[1]], [], 24000)
