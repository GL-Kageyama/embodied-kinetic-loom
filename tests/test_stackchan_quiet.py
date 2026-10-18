# -*- coding: utf-8 -*-
"""**静かな時間。**

⚠️ **3つの層を、別々に測る。**
`quiet.py` の規則、中核がその真偽で**音の欄だけ**を閉じること、
そして縁が**壁時計の時を読んで**渡すことである。

⛔ **このファイルは機体を開かない。** 音が鳴るかどうかは、ここでは分からない——
**閉じた欄を数えているだけである。**
"""
from __future__ import annotations

import datetime

import pytest

from projects.stackchan import quiet
from projects.stackchan.daemon import __main__ as edge
from projects.stackchan.daemon.room import Room
from projects.stackchan.quiet import QUIET_FROM, QUIET_UNTIL, is_quiet


# ---------------------------------------------------------------------------
# 規則。⛔ 時計もソケットも無い。
# ---------------------------------------------------------------------------


def test_the_rule_is_21_to_5():
    """⚠️ **著者の規則である。** 数は2つだけで、ここに在る。"""
    assert (QUIET_FROM, QUIET_UNTIL) == (21, 5)


@pytest.mark.parametrize(
    "hour, quiet_now",
    [
        (0, True), (1, True), (2, True), (3, True), (4, True),
        (5, False), (6, False), (7, False), (8, False), (9, False),
        (10, False), (11, False), (12, False), (13, False), (14, False),
        (15, False), (16, False), (17, False), (18, False), (19, False),
        (20, False),
        (21, True), (22, True), (23, True),
    ],
)
def test_every_hour_has_an_answer(hour, quiet_now):
    """✅ **24の時すべてを1つずつ数えた。** 端はどちらも静かな側ではない——
    21:00 は静か、05:00 は昼である。"""
    assert is_quiet(hour) is quiet_now


def test_an_hour_that_is_not_an_hour_is_refused():
    """⛔ **黙って別の答えを返さない。** 24 と -1 は時ではなく、読み手の誤りである。"""
    for bad in (24, -1, 100, -100):
        with pytest.raises(ValueError):
            is_quiet(bad)


def test_a_bool_is_not_an_hour():
    """⚠️ **`True` は `1` でもある**（Python では）。1時は静かだが、
    **それは bool が時として読まれてよい理由にならない。**"""
    with pytest.raises(TypeError):
        is_quiet(True)


# ---------------------------------------------------------------------------
# 中核。⚠️ 音の欄だけが閉じる。
# ---------------------------------------------------------------------------


def test_quiet_closes_the_sound_and_nothing_else():
    """⛔ **顔も光も身振りも従わない。** 静かであることは、居ないことではない。"""
    loud = Room(sound=True).offer("main", "SessionStart", 0.0, quiet=False)
    hush = Room(sound=True).offer("main", "SessionStart", 0.0, quiet=True)

    assert loud.sound == "hello"
    assert hush.sound is None
    assert (hush.face, hush.light, hush.gesture, hush.phase) == (
        loud.face, loud.light, loud.gesture, loud.phase,
    )


def test_a_sound_that_was_off_stays_off():
    """⚠️ **2つの門は、どちらも閉じる。** 静かな時間は、切った音を戻さない。"""
    assert Room(sound=False).offer("main", "SessionStart", 0.0, quiet=False).sound is None
    assert Room(sound=False).offer("main", "SessionStart", 0.0, quiet=True).sound is None


def test_the_other_three_words_are_closed_too():
    """⚠️ **4つの語すべてを見た。** 1つだけ閉じる門は、門ではない。"""
    for event in ("PermissionRequest", "Stop", "StopFailure"):
        assert Room(sound=True).offer("main", event, 0.0, quiet=False).sound is not None
        assert Room(sound=True).offer("main", event, 0.0, quiet=True).sound is None


# ---------------------------------------------------------------------------
# 縁。⛔ 時計を読むのは1箇所だけである。
# ---------------------------------------------------------------------------


def test_the_edge_asks_the_rule_with_the_hour_it_was_given():
    """✅ **時を渡せば、境界を時計を止めずに測れる。**"""
    night = edge.decide(Room(sound=True), "main", "SessionStart", 0.0, hour=23)
    day = edge.decide(Room(sound=True), "main", "SessionStart", 0.0, hour=12)
    assert night.sound is None
    assert day.sound == "hello"


def test_without_an_hour_the_edge_reads_the_wall_clock(monkeypatch):
    """⚠️ **既定の道も1度通す。** 壁時計を止めて、読んだ時が結論を決めることを見る。

    ⛔ **時計を偽物にしないと、この検査は日が変わると答えを変える。**
    """

    # ⚠️ **本物を先に持っておく。** 差し替えた後では、もう `datetime.datetime` は無い。
    Real = datetime.datetime

    class At:
        @staticmethod
        def now():
            return Real(2026, 10, 19, 23, 30)

    monkeypatch.setattr(edge.datetime, "datetime", At)
    assert edge.decide(Room(sound=True), "main", "SessionStart", 0.0).sound is None

    class Noon:
        @staticmethod
        def now():
            return Real(2026, 10, 20, 12, 0)

    monkeypatch.setattr(edge.datetime, "datetime", Noon)
    assert edge.decide(Room(sound=True), "main", "SessionStart", 0.0).sound == "hello"


def test_the_rule_is_named_once():
    """⚠️ **21 と 5 は `quiet.py` に在り、`__main__.py` は数を持たない。**"""
    source = (
        __import__("pathlib").Path(edge.__file__).read_text(encoding="utf-8")
    )
    assert "QUIET_FROM" not in source and "QUIET_UNTIL" not in source
    assert quiet.QUIET_FROM == 21 and quiet.QUIET_UNTIL == 5
