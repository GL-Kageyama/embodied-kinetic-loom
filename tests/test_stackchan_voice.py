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
from projects.stackchan.voice.render import (
    GAIN, PAUSE_MS, PITCH, gap_frames, pitched, segments, spoken,
)


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
    """⚠️ **著者の耳が三度動かした数である**（2026-10-21）。

    +6（私の選択）→ **「もっと声を高く」** → +14 → **「中間がいい」** で
    +6 と +8 を鳴らし **「2回目が良い」** → **+8**。
    """
    assert PITCH == 8


def test_the_voice_is_quieter_than_the_four_sounds():
    """⛔ **声の大きさは、アンプの -10 dB とは別である**（「もう少し声を小さく」）。

    ⚠️ **0.5 で聞いて「少し小さい」と言われ、0.75 へ動いた**（2026-10-21）。
    正規化（天井 32767）の後に掛かるので、これは**天井からの比**である。
    """
    assert GAIN == 0.75


def test_the_gain_clamps_instead_of_wrapping():
    from projects.stackchan.voice.wav import scale

    assert scale([1000, -1000], 0.5) == [500, -500]
    assert scale([32767, -32768], 2.0) == [32767, -32768]


def test_the_loudest_sample_is_put_at_the_ceiling():
    """⛔ **`say` の出力の大きさに任せない**（2026-10-21）。

    ⚠️ 実測: `say -v Kyoko` はピーク **−18.9 dBFS** で返した。掛け算だけで
    大きさを決めると、**声の機嫌が音量になる**。正規化が先である。
    """
    from projects.stackchan.voice.wav import normalize

    out = normalize([100, -200, 50])
    #: ⚠️ **「大きい」は絶対値である**——−200 が最大なので、天井に着くのは負の側。
    assert max(max(out), -min(out)) == 32767
    assert min(out) == -32767
    assert normalize([7, -3, 0], peak=100) == [100, round(-3 * 100 / 7), 0]


def test_silence_cannot_be_normalized():
    """⛔ **0 で割らない。** そして**無音を返さない**——規則の不在を音で埋めない。"""
    from projects.stackchan.voice.wav import normalize

    with pytest.raises(ValueError):
        normalize([0, 0, 0])
    with pytest.raises(ValueError):
        normalize([])


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


# --- リンクへ流す塊（pcm.py）------------------------------------------------
#
# ⛔ **規則は塊の大きさではなく、境目である。** `audio <n>` のあとの n バイトは
# 生の標本であり、**改行で割られない**——標本の1バイトが 0x0A でありうるから。


def test_a_sample_is_two_bytes_little_endian():
    from projects.stackchan.voice.pcm import bytes_of

    assert bytes_of([1, -1, 0]) == b"\x01\x00\xff\xff\x00\x00"


def test_a_sample_outside_the_range_is_clamped():
    """⚠️ **例外にしない。** 割れた標本で音を止めるより、丸めて鳴らす。"""
    from projects.stackchan.voice.pcm import bytes_of

    assert bytes_of([40000, -40000]) == b"\xff\x7f\x00\x80"


def test_the_head_is_spelled_once():
    from projects.stackchan.voice.pcm import head

    assert head(2048) == b"audio 2048\n"


@pytest.mark.parametrize("count", [0, 4098, 8192, -2, 1, 3, 2047])
def test_a_head_that_cannot_be_played_is_refused(count):
    """⛔ **基板が丸ごと拒む頭を、こちらから送らない。**

    ⚠️ **0 は「何もしない」である。** ⛔ **奇数は半端な標本である**——2バイトが
    1標本なので、基板は丸ごと拒む（`audio_line::parse`）。
    """
    from projects.stackchan.voice.pcm import head

    with pytest.raises(ValueError):
        head(count)


def test_the_blocks_rebuild_the_stream_they_were_given():
    """**割って、つなげば、元の16ビットの並びに戻る。** ⚠️ 頭は塊ごとに1つ。

    ⛔ **何も符号化されない**——`rebuilt` は `data` そのものである。µ-law の
    ころはここが `ulaw(samples)` との一致だった。**損失の無い道では、元に戻る
    ことが正しさの形**であり、それは**丸めも表引きも挟まっていない**ことを言う。
    """
    from projects.stackchan.voice.pcm import blocks, bytes_of

    samples = list(range(-100, 100))
    data = bytes_of(samples)
    pieces = blocks(data, chunk=64)
    assert len(pieces) == 7  # 400 バイト = 200 標本、1塊 64 バイト（32標本）で 7 塊
    rebuilt = b""
    for piece in pieces:
        head, _, body = piece.partition(b"\n")
        assert head == b"audio %d" % len(body)
        assert len(body) % 2 == 0
        rebuilt += body
    assert rebuilt == data


def test_no_block_is_bigger_than_the_board_s_buffer():
    """⛔ **これを越える頭は、基板が丸ごと拒む。**"""
    from projects.stackchan.voice.pcm import CHUNK, MAX_BYTES, blocks, bytes_of

    assert CHUNK <= MAX_BYTES
    data = bytes_of([0] * (MAX_BYTES * 3))
    for piece in blocks(data):
        assert len(piece) - piece.index(b"\n") - 1 <= MAX_BYTES


def test_a_half_sample_is_never_sent():
    """⛔ **16ビットの並びが奇数なら、標本として読めない。** 送らずに落とす。

    ⚠️ **塊の側に偶数規則は無い**——1バイトが1標本（µ-law）である。
    """
    from projects.stackchan.voice.pcm import blocks

    with pytest.raises(ValueError):
        blocks(b"\x01\x02\x03")


def test_a_newline_inside_a_sample_is_data():
    """⛔ **これが、頭が在る理由である。**

    0x0A を含む標本は、**行として読まれない**——頭が先に「n バイト」と言うからである。
    ⚠️ ここで確かめるのは、塊がその2バイトを**そのまま**運ぶことだけである。
    """
    from projects.stackchan.voice.pcm import blocks, bytes_of

    data = bytes_of([0x0A0A, 0x0D0A])
    assert data == b"\x0a\x0a\x0a\x0d"
    piece = blocks(data, chunk=4)[0]
    head, _, body = piece.partition(b"\n")
    assert head == b"audio 4"
    assert body == b"\x0a\x0a\x0a\x0d"  # 16ビット線形のまま運ばれる
