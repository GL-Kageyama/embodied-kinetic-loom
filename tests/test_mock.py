# -*- coding: utf-8 -*-
"""Mock——**プロトコルの試験である。安全の試験ではない。**

⛔ **D-16 の逐語**（[02_調査/04] §11.2）:
> **「Mock は『プロトコルの試験』と割り切り、Mock が緑でも実機の安全は保証されないと
> 設計文書に明記する。」**

⇒ **ゆえにこのファイルは、「安全になった」を1つも主張しない。**
**主張するのは「箱が何を飲み込むか」だけである。**

⛔ **中心は `test_mo0_stops_the_reporting_and_does_not_stop_the_motor` である。**
**この機体の安全について、いちばん誤解されやすい1点が、そこに在る。**
⚠️ **そして、このファイルを書いた最初の版は、その検査を書けなかった**——
**Mock の側が `[mo0]` を見ていなかったからである**（`test_the_mock_can_see_a_text_command` を見よ）。
"""
from __future__ import annotations

import pytest

from engine.backend.mock import TORQUE_DECAY_SECONDS, MockBox
from engine.backend.protocol import ProtocolError, encode_target, encode_text


# --------------------------------------------------------------------------
# ⛔ ここが中心である
# --------------------------------------------------------------------------


def test_mo0_stops_the_reporting_and_does_not_stop_the_motor():
    """⛔ **`[mo0]` は「報告をやめる」である。モーターは止まらない。**

    [02_調査/01] §2.5 の逐語——**「プロトコルには、ホストから運動を止める手段が無い。」**
    ⚠️ **`pysmc3` の例が `KeyboardInterrupt` で `disable_feedback()` を呼んで終わるのは、
    止まっているのではなく黙っているだけである。**
    """
    box = MockBox()
    box.feed(encode_target(0, 512).raw, 0.0)
    assert box.positions[0] == 512.0

    box.feed(encode_text("mo0").raw, 0.1)

    assert box.reporting is False, "⚠️ 報告は止まる"
    assert box.positions[0] == 512.0, "⛔ **モーターは止まらない。位置は動いていない**"
    assert box.steps[-1].after == 512.0


def test_sav_does_not_stop_the_motor():
    """⛔ **`[sav]` は EEPROM への保存である。** 動きと無関係（§2.5）。"""
    box = MockBox()
    box.feed(encode_target(1, 400).raw, 0.0)
    before = box.positions
    box.feed(encode_text("sav").raw, 0.1)
    assert box.positions == before
    assert box.reporting is True  # ⚠️ 保存は報告にも触らない


def test_ena_does_not_stop_either():
    """⛔ **`[ena]` は「強制停止から戻す」である。止める方ではない**（§2.5）。"""
    box = MockBox()
    box.feed(encode_target(2, 300).raw, 0.0)
    box.feed(encode_text("ena").raw, 0.1)
    assert box.positions[2] == 300.0


def test_silence_decays_the_torque_and_does_not_stop_the_motor():
    """⛔ **送るのをやめると、15秒でトルクがおよそ 1/4 になる——そして、止まらない。**

    **接続が切れたことは、機体が止まったことではない**（`CLAUDE.md` の安全の節）。
    ⚠️ **Mock は位置を持っているので、「動いていない」と言いたくなる。**
    **だが、それは Mock が位置しか模型していないからである。**
    """
    box = MockBox()
    box.feed(encode_target(0, 512).raw, 0.0)
    assert not box.torque_decayed(14.9)
    assert box.torque_decayed(TORQUE_DECAY_SECONDS)
    assert box.torque_decayed(60.0)
    assert box.positions[0] == 512.0, "⛔ **沈黙は停止ではない**"


def test_silent_for_measures_from_the_last_frame():
    """⚠️ **1つも受け取っていなければ 0 である**——「ずっと沈黙していた」ではない。"""
    box = MockBox()
    assert box.silent_for(100.0) == 0.0
    box.feed(encode_target(0, 500).raw, 10.0)
    assert box.silent_for(12.5) == pytest.approx(2.5)


# --------------------------------------------------------------------------
# ⛔ 語は3文字である（この版が最初に間違えたところ）
# --------------------------------------------------------------------------


def test_the_mock_can_see_a_text_command():
    """⛔ **`frame.command` は1文字である。だから `"mo"` とは比較できない。**

    **この版の最初の `mock.py` は `frame.command == "mo"` と書いていた。**
    実測: `[mo0]` を食わせると `command` は `'m'`、`value` は 28464 になる。
    ⇒ **その分岐は到達不能だった**——**この機体の安全について、いちばん重要な2つの命令が。**
    ⚠️ **検査が空を相手にしていた**（`CLAUDE.md`「空の検査は OK と言う」）。
    """
    box = MockBox()
    frames = box.feed(encode_text("mo0").raw, 0.0)
    assert frames[0].token == "mo0"
    assert box.commands == ["mo0"]
    assert box.reporting is False


def test_a_position_frame_has_no_token():
    """⚠️ **`[A xx]` の3バイトは「語」ではない**（`A` ＋ 2バイトの値である）。"""
    box = MockBox()
    frames = box.feed(encode_target(0, 512).raw, 0.0)
    assert frames[0].token == ""
    assert box.commands == ["A"], "⚠️ 語が無いときは、1文字の方を記録する"


def test_a_word_starting_with_a_motor_letter_cannot_be_built():
    """⛔ **境界を曖昧なまま残さない。** `A`/`B`/`C` で始まる語は組めない。

    ⚠️ **そういう語が実在するかは、確かめていない**（`Frame.token`）。
    **在れば、Mock はそれを位置の命令として読む。実機で確かめるまで、これを書かない。**
    """
    with pytest.raises(ProtocolError, match="区別がつかない"):
        encode_text("A12")
    with pytest.raises(ProtocolError, match="3文字"):
        encode_text("mo00")
    with pytest.raises(ProtocolError, match="3文字"):
        encode_text("mo")


# --------------------------------------------------------------------------
# 箱が黙って飲み込むもの
# --------------------------------------------------------------------------


def test_an_unknown_command_is_swallowed_in_silence():
    """⛔ **箱はエラーを返さない**（`SMC3.ino` の `switch` に `default` が無い）。

    ⚠️ **ここが、実機と Mock が一致している数少ない点である。**
    ⇒ **「エラーが出なかった」は「正しい値を送った」ではない。**
    """
    box = MockBox()
    frames = box.feed(encode_text("zzz").raw, 0.0)
    assert len(frames) == 1, "⚠️ 切れてはいる"
    assert box.positions == (0.0, 0.0, 0.0)
    assert box.received == []


def test_a_value_the_box_cannot_use_is_not_reported_as_an_error():
    """⛔ **相手は受け取った値を検査しない。** ベンダーの参照コード自身がそう書いている。"""
    box = MockBox()
    box.feed(encode_target(0, 1024).raw, 0.0)  # 2バイトの上限。**箱は何も言わない**
    assert box.positions[0] == 1024.0


def test_a_bracket_inside_the_payload_does_not_confuse_the_box():
    """⛔ **目標 347 の下位バイトは `[` である**（`test_protocol.py` を見よ）。"""
    box = MockBox()
    box.feed(encode_target(1, 347).raw, 0.0)
    assert box.positions[1] == 347.0
    assert len(box.received) == 1


def test_an_unknown_motor_letter_for_this_box_is_ignored():
    """⚠️ **3軸に満たない箱**（試験用）では、余った記号は黙って落ちる。"""
    box = MockBox(motors=2)
    box.feed(encode_target(2, 500).raw, 0.0)
    assert box.positions == (0.0, 0.0)
    assert box.received == []


# --------------------------------------------------------------------------
# ⛔ one motor locks all
# --------------------------------------------------------------------------


def test_one_motor_locks_all():
    """⛔ **ベンダー自身の言葉である。** 1本が強制停止に入ると、残る2本も操作できない。"""
    box = MockBox()
    box.feed(encode_target(0, 500).raw, 0.0)
    box.locked = True
    box.feed(encode_target(1, 700).raw, 0.1)
    assert box.positions == (500.0, 0.0, 0.0), "⛔ **他の軸が動いてしまっている**"
    # ⚠️ **700 が届いていない。** 届いたのは、施錠の前の1つだけである
    assert [f.value for f in box.received] == [500]
    # ⚠️ **届かなかったことは、どこにも報告されない**（箱はエラーを返さない）
    assert len(box.steps) == 1


# --------------------------------------------------------------------------
# Mock にしか無い情報
# --------------------------------------------------------------------------


def test_a_step_is_recorded_because_the_real_box_never_records_it():
    """⛔ **上流ファームにソフトスタート/ストップが無い**（[02_調査/01] §2.6）。

    **段差指令は段差のまま入る。** そして**本物の箱は、それを記録しない。**
    ⇒ **`steps` は Mock にしか無い**——**「何を送ったか」を送った側に返すだけである。**
    **「安全である」の代わりではない。**
    """
    box = MockBox()
    box.feed(encode_target(0, 500).raw, 0.0)
    box.feed(encode_target(0, 900).raw, 0.001)  # ⛔ **1 ms で 400 カウント**
    assert len(box.steps) == 2
    step = box.steps[-1]
    assert (step.before, step.after, step.at) == (500.0, 900.0, 0.001)
    assert step.delta == 400.0


def test_the_two_byte_check_is_not_the_190_to_833_check():
    """⛔ **2つの層を混ぜない。**

    `frames_within_2bytes` が見るのは「2バイトに収まるか」だけである。
    **ホストが既定で送れる 190〜833 は、門（`gate.py`）の仕事である**——
    **1000 は前者を通り、後者で落ちる。**
    """
    box = MockBox()
    box.feed(encode_target(0, 1000).raw, 0.0)
    assert box.frames_within_2bytes(), "⛔ 2バイトには収まっている"
    # ⚠️ そして、これは 833 の外である。**その検査はここには無い**
    assert box.positions[0] == 1000.0
