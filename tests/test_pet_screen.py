# -*- coding: utf-8 -*-
"""**画面の主張を、4つに分けて押さえる。**

1. **1フレーム＝1回の write**（[05] §3.3）
2. **同期更新の対が、1つの文字列の中で閉じる**——**開いたまま落ちない**
3. **フレームの形が、状態によって変わらない**——**残像が出ない**
4. **同じ状態なら、同じフレーム**——決定論

⚠️ **端末には1バイトも出していない。** `Writer` は記録するだけの偽物である——
**このファイルが測っているのは文字列であって、端末ではない。**
"""
from __future__ import annotations

import pytest

from projects.pet.expressions import BOX_HEIGHT, BOX_WIDTH, FACES, State
from projects.pet.screen import CLOSE, HOME, SYNC_BEGIN, SYNC_END, Screen, box, frame


class Recorder:
    """⚠️ **書かれた回数と中身を、そのまま覚える。** それだけの偽物である。"""

    def __init__(self) -> None:
        self.writes: list[str] = []

    def write(self, text: str) -> int:
        self.writes.append(text)
        return len(text)


@pytest.mark.parametrize("state", list(State))
def test_a_frame_is_one_write(state):
    out = Recorder()
    Screen(out).draw(state)
    assert len(out.writes) == 1, "⛔ **1フレームは1回である**"


@pytest.mark.parametrize("state", list(State))
def test_a_synchronised_frame_opens_and_closes_the_update(state):
    text = frame(state, synchronised=True)
    assert text.count(SYNC_BEGIN) == 1
    assert text.count(SYNC_END) == 1
    assert text.index(SYNC_BEGIN) < text.index(SYNC_END)


@pytest.mark.parametrize("state", list(State))
def test_a_plain_frame_carries_no_update_sequences(state):
    """⚠️ **既定は使わない側である。** 対応を測っていない端末に、既定で入れない。"""
    text = frame(state)
    assert SYNC_BEGIN not in text and SYNC_END not in text


@pytest.mark.parametrize("state", list(State))
def test_every_frame_has_the_same_shape(state):
    """⛔ **眠い顔だけ4行なので、これが無いと4行目が残る。**"""
    lines = frame(state, synchronised=False).removeprefix(HOME).split("\r\n")
    assert len(lines) == BOX_HEIGHT
    assert all(len(line) == BOX_WIDTH for line in lines)


def test_the_sleepy_face_does_not_leave_its_fourth_line_behind():
    """⚠️ **前のフレームより背が低い顔を出したとき、行が余らないこと。**"""
    for state in State:
        assert len(box(state)) == len(box(State.SLEEPY)) == BOX_HEIGHT


@pytest.mark.parametrize("state", list(State))
def test_no_frame_contains_a_wide_character(state):
    """⛔ **`len()` が表示幅と一致すること。**

    ⚠️ **この工房の文書は CJK である。** 顔に1文字でも日本語が混じれば、
    **ずれるのは端末の上だけで、`len()` は何も言わない。**
    """
    for char in frame(state, synchronised=True):
        assert ord(char) < 128, f"ASCII でない文字が入っている: {char!r}"


@pytest.mark.parametrize("state", list(State))
def test_the_same_state_gives_the_same_frame(state):
    assert frame(state) == frame(state)


def test_a_line_wider_than_the_box_is_refused_not_truncated(monkeypatch):
    """⛔ **切ると、ずれたことに誰も気づかない。** ゆえに落ちる。"""
    monkeypatch.setitem(FACES, State.HAPPY, ("  /\\_/\\", " ( ^.^^.^ )", "  > ^ <"))
    with pytest.raises(ValueError, match="箱より広い"):
        box(State.HAPPY)


def test_close_returns_the_terminal():
    out = Recorder()
    Screen(out, synchronised=True).close()
    assert out.writes == [SYNC_END + CLOSE]
    assert CLOSE.endswith("\r\n"), "⚠️ これが無いと、プロンプトが猫に重なる"


def test_close_rescues_an_update_that_a_torn_write_left_open():
    """⛔ **フレームは自分で対を閉じる。それでも `l` をもう一度出すのは、救助である。**

    **`frame()` が `h` と `l` を同じ文字列に持っていても、write が途中で切れれば
    `l` は端末に届かない。** そのとき、**この2回目が無ければ端末は止まったままになる。**
    ⇒ **ゆえに「同期更新つきの走行で `l` は2回」は、期待された姿である。**
    """
    out = Recorder()
    screen = Screen(out, synchronised=True)
    screen.draw(State.HAPPY)
    screen.close()

    joined = "".join(out.writes)
    assert joined.count(SYNC_BEGIN) == 1
    assert joined.count(SYNC_END) == 2, "⛔ **1回目はフレームの中、2回目が救助である**"


def test_close_does_not_close_an_update_that_was_never_opened():
    """⛔ **実測で見つけた欠陥である**（2026-09-28、`--state sleepy` を走らせて）。

    **同期更新を使っていない画面が、閉じるときに `l` を出していた**——
    **しなかった借りを返していた。** ⚠️ **当時の検査は、この欠陥に同意していた。**
    """
    out = Recorder()
    Screen(out).close()
    assert out.writes == [CLOSE]
    assert SYNC_END not in out.writes[0]


def test_the_screen_passes_its_own_synchronised_flag(monkeypatch):
    """⚠️ **`Screen` と `frame` の既定がずれていないこと。**"""
    out = Recorder()
    Screen(out, synchronised=True).draw(State.HAPPY)
    assert SYNC_BEGIN in out.writes[0]

    out = Recorder()
    Screen(out).draw(State.HAPPY)
    assert SYNC_BEGIN not in out.writes[0]
