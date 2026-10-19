# -*- coding: utf-8 -*-
"""**判定の後処理 —— この層が何を見て、何を返すか。**

⛔ **ここには機械が無い。** `Decision` を受け取って `Decision` を返す関数だけを
押さえる。⚠️ **光の色そのものは主張しない**——`write` と `run` に自分の語が
付くのは 0.19.47 であり、**その日まで両方 `dim` である**（`presence.WORK_LIGHTS`）。
だから滞留と点滅の規則は、**写像を差し替えて**測る——
**色が決まっていなくても、規則は決まっている。**
"""
from __future__ import annotations

import pytest

from projects.stackchan.behaviors import (
    IDLE_SECONDS,
    Companion,
    Focus,
    Light,
    Phase,
)
from projects.stackchan_next import presence
from projects.stackchan_next.presence import (
    FAILURE_FLASH_SECONDS,
    FLASHED,
    PRESENCE_LIVELY,
    PRESENCE_NORMAL,
    PRESENCE_QUIET,
    WAKE_SOUND,
    Presence,
)


def _presence(dial: str = PRESENCE_NORMAL, *, sound: bool = True,
              motion: bool = False) -> Presence:
    """⚠️ **音を既定で開けておく**——起きたときの1語は、開いていなければ測れない。"""
    return Presence(presence=dial, room=Focus(Companion(motion=motion, sound=sound)))


def _start(room: Presence, at: float = 0.0):
    """**章を開ける。** プロンプトが1つ届いた、というだけである。"""
    return room.offer("main", "UserPromptSubmit", at)


def _rest(room: Presence, at: float) -> None:
    """**90秒黙たせ、休息へ入れる。** ⛔ 時計は読まない——`at` は渡す値である。"""
    slept = room.tick(at + IDLE_SECONDS)
    assert slept is not None and slept.phase is Phase.RESTING


@pytest.fixture
def two_lights(monkeypatch):
    """⚠️ **0.19.46 では `write` も `run` も `dim` である。**
    色が決まる前でも規則を測れるよう、**写像だけを差し替える**——
    ⛔ **規則そのものは差し替えない。**
    """
    monkeypatch.setitem(presence.WORK_LIGHTS, "write", Light.WARM)
    monkeypatch.setitem(presence.WORK_LIGHTS, "run", Light.ERROR)


# ───────────────────────── 作業の光 ─────────────────────────


def test_a_write_shows_as_soon_as_the_chapter_opens(two_lights):
    """⚠️ **章へ入ることは滞留に数えない。** 最初の `write` はすぐ見える。"""
    room = _presence()
    assert _start(room, 0.0).light is Light.DIM
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WARM


def test_the_work_light_does_not_change_more_often_than_the_dwell(two_lights):
    """⚠️ **道具のたびに色が変われば、それは鏡であり、相棒ではない。**"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WARM
    assert room.offer("main", "PreToolUse", 1.2, work="read").light is Light.WARM
    assert room.offer("main", "PreToolUse", 5.4, work="read").light is Light.WARM
    assert room.offer("main", "PreToolUse", 5.5, work="read").light is Light.DIM


def test_leaving_the_chapter_is_not_held_by_the_dwell(two_lights):
    """⛔ **滞留は `working` の内側の規則である。** 章の出入りは即座である。"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WARM

    blocked = room.offer("main", "PermissionRequest", 0.6)
    assert blocked.phase is Phase.BLOCKED and blocked.light is Light.ALERT

    back = room.offer("main", "PostToolUse", 0.7, work="run")
    assert back.phase is Phase.WORKING
    assert back.light is Light.ERROR, "入り直した章は、滞留を待たない"


def test_a_work_word_on_an_event_that_carries_none_is_ignored(two_lights):
    """⛔ **語は、それを運ぶ事象のものである。** `Stop` が `run` を名乗っても覚えない。"""
    room = _presence()
    _start(room, 0.0)
    room.offer("main", "Stop", 0.5, work="run")
    room.tick(4.0)                                    # 締めの表情が明ける
    decision = room.offer("main", "UserPromptSubmit", 4.5)
    assert decision.phase is Phase.WORKING
    assert decision.light is Light.DIM, "run の光ではなく、知らされていない作業の光"


def test_an_unknown_work_word_is_not_remembered(two_lights):
    """⛔ **知らない語を覚えれば、次の判定がその語で光る。**"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WARM
    assert room.offer("main", "PreToolUse", 6.0, work="dance").light is Light.WARM


def test_lively_changes_the_light_sooner(two_lights):
    """⚠️ **賑やかな側は、滞留が短いだけである。** 光の意味は変わらない。"""
    room = _presence(PRESENCE_LIVELY)
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WARM
    assert room.offer("main", "PreToolUse", 2.4, work="read").light is Light.WARM
    assert room.offer("main", "PreToolUse", 2.5, work="read").light is Light.DIM


# ───────────────────────── 失敗の長さ ─────────────────────────


def test_one_failure_is_visible_for_two_seconds(two_lights):
    """⚠️ **1回の失敗は、0.19.45 まで完全に見えなかった。** 長さで見えるようにする。"""
    room = _presence()
    _start(room, 0.0)

    failed = room.offer("main", "PostToolUseFailure", 1.0)
    assert failed.light is Light.ALERT
    assert room.deadline == pytest.approx(1.0 + FAILURE_FLASH_SECONDS)

    assert room.tick(2.9) is None, "まだ尽きていない刻みは、行にならない"

    done = room.tick(3.0)
    assert done is not None
    assert done.reason == FLASHED
    assert done.event is None
    assert done.phase is Phase.WORKING
    assert done.face is None, "点滅は顔を連れてこない"
    assert done.sound is None
    assert done.light is Light.DIM


def test_three_failures_hold_the_alert_past_the_flash(two_lights):
    """⛔ **語は増やさない。長さで区別する。** 持続は既存の `concern` である。"""
    from projects.stackchan.behaviors import CONCERN

    room = _presence()
    _start(room, 0.0)
    room.offer("main", "PostToolUseFailure", 1.0)
    room.offer("main", "PostToolUseFailure", 1.1)
    third = room.offer("main", "PostToolUseFailure", 1.2)

    assert third.reason == CONCERN
    assert third.light is Light.ALERT
    assert room.tick(10.0) is None, "2回目が置いた点滅の期限は、捨てられている"
    assert room.deadline == pytest.approx(1.2 + IDLE_SECONDS)


def test_a_failure_outside_working_does_not_flash():
    """⛔ **失敗の点滅は `working` の内側だけである。** 在席は自分の光を持つ。"""
    room = _presence()
    room.offer("main", "SessionStart", 0.0)
    room.tick(4.0)                                    # 挨拶が明けて present

    failed = room.offer("main", "PostToolUseFailure", 5.0)
    assert failed.phase is Phase.PRESENT
    assert failed.light is Light.BREATHE
    assert room.tick(7.5) is None, "点滅の期限は置かれていない"


# ───────────────────────── 起きたときの1語 ─────────────────────────


def test_waking_says_one_word():
    """⚠️ **90秒黙ったあとの最初の事象に、`pip` を1つだけ。**"""
    room = _presence()
    _start(room, 0.0)
    _rest(room, 0.0)

    woke = room.offer("main", "InstructionsLoaded", 95.0)
    assert woke.event == "InstructionsLoaded"
    assert woke.sound == WAKE_SOUND

    again = room.offer("main", "InstructionsLoaded", 96.0)
    assert again.sound is None, "起きているあいだは、もう言わない"


def test_a_transition_keeps_its_own_word_when_it_wakes_the_room():
    """⛔ **挨拶は、自分の音を持っている事象を塗り替えない。**"""
    room = _presence()
    _start(room, 0.0)
    _rest(room, 0.0)
    assert room.offer("main", "SessionStart", 95.0).sound == "hello"


def test_waking_is_silent_when_the_speaker_is_off():
    """⚠️ **`--sound off` は独立のダイヤルである。** この層はそれに従う。"""
    room = _presence(sound=False)
    _start(room, 0.0)
    _rest(room, 0.0)
    assert room.offer("main", "InstructionsLoaded", 95.0).sound is None


def test_waking_is_silent_in_the_quiet_hours():
    """⚠️ **21:00–05:00 は無音であり、存在しない時間ではない。**"""
    room = _presence(sound=True)
    _start(room, 0.0)
    _rest(room, 0.0)
    assert room.offer("main", "InstructionsLoaded", 95.0, quiet=True).sound is None


# ───────────────────────── ダイヤル ─────────────────────────


def test_quiet_closes_every_channel_this_layer_added(two_lights):
    """⛔ **`quiet` は、この層が足した3つだけを閉じる。**"""
    room = _presence(PRESENCE_QUIET, sound=True)
    _start(room, 0.0)

    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.DIM
    assert room.offer("main", "PostToolUseFailure", 1.0).light is Light.DIM
    assert room.deadline == pytest.approx(1.0 + IDLE_SECONDS), "点滅の期限は置かれない"

    _rest(room, 1.0)
    assert room.offer("main", "InstructionsLoaded", 95.0).sound is None


def test_a_presence_that_is_not_one_of_the_three_is_refused():
    with pytest.raises(ValueError):
        Presence(presence="loud")


# ───────────────────────── 触らないこと ─────────────────────────


def test_the_layer_changes_no_field_but_the_light(two_lights):
    """⛔ **顔・身振り・体・音・`sent` は、この層のものではない。**"""
    room = _presence()
    _start(room, 0.0)
    decision = room.offer("main", "PreToolUse", 0.5, work="write")

    assert decision.face is None, "「変えない」を、この層は塗り替えない"
    assert decision.gesture is None
    assert decision.sound is None
    assert decision.sent is False
    assert decision.event == "PreToolUse"
    assert decision.light is Light.WARM


def test_without_a_flash_the_deadline_is_the_rooms(two_lights):
    """⚠️ **期限は1つ増える。増えていないときは、部屋のものがそのまま出る。**"""
    room = _presence()
    _start(room, 0.0)
    assert room.deadline == pytest.approx(IDLE_SECONDS)
