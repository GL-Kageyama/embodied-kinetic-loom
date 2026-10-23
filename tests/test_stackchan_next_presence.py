# -*- coding: utf-8 -*-
"""**判定の後処理 —— この層が何を見て、何を返すか。**

⛔ **ここには機械が無い。** `Decision` を受け取って `Decision` を返す関数だけを
押さえる。⚠️ **光の色そのものは主張しない**——色はファームウェアの選択であり、
机の上で区別できるかは著者の目が決める。ここで測るのは**どの語を選ぶか**までである。

⚠️ **2026-10-24 に、この層は2つ目のチャンネルを得た**——顔である（著者の
「3つ（＋失敗）」）。⇒ **光と顔は同じ1つの判断で動く。** 滞留も、章の終わりに
忘れることも、背後の窓を通さないことも、**2つに共通である**。⛔ 別々に置けば、
片方だけが遅れた日に「光は `busy`、顔は `focused`」という枠が出る。
"""
from __future__ import annotations

import pytest

from projects.stackchan.behaviors import (
    DISTANT,
    IDLE_SECONDS,
    Companion,
    Focus,
    Light,
    Phase,
)
from projects.stackchan.faces import Face
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


# ───────────────────────── 写像そのもの ─────────────────────────


def test_two_work_words_have_a_light_of_their_own():
    """✅ **0.19.47。** ⛔ **語と光を同じ日に足す**——先に語だけ足せば、基板は枠ごと拒む。"""
    assert presence.WORK_LIGHTS == {"write": Light.WRITING, "run": Light.BUSY}
    assert presence.WORK_LIGHT_OTHER is Light.DIM


def test_every_work_light_is_a_word_the_wire_can_carry():
    """⛔ **`Light` に値を足して codec に語を足し忘れれば、枠は送れない。**"""
    from engine.backend import protocol_stackchan as wire

    for light in (*presence.WORK_LIGHTS.values(), presence.WORK_LIGHT_OTHER):
        assert light.value in wire.LIGHTS


def test_two_work_words_have_a_face_of_their_own():
    """⚠️ **光の写像と同じ形をしている。** ⛔ 語は意味に対して付けた。

    ⚠️ **形がその語に見えるかは、この検査の外である**——`bench face` の前に
    著者の目があり、**どの形もまだ判定されていない**（2026-10-24）。
    """
    assert presence.WORK_FACES == {"write": Face.FOCUSED, "run": Face.WATCHING}
    assert presence.WORK_FACE_OTHER is Face.CURIOUS
    assert presence.FAILURE_FACE is Face.STARTLED


def test_every_work_face_is_a_word_the_wire_can_carry():
    """⛔ **`Face` に値を足して codec に語を足し忘れれば、枠は送れない。**

    ⚠️ **2026-10-24 の順序はこれである**——語を codec・schema・ファームの3か所に
    同じ日に載せ、**基板を焼き、その後にホストを設置する**。⛔ 逆にすれば、
    基板は語を知らず、**枠ごと拒んで光も身振りも一緒に落とす**（`kUnknownValue`）。
    """
    from engine.backend import protocol_stackchan as wire

    for face in (
        *presence.WORK_FACES.values(),
        presence.WORK_FACE_OTHER,
        presence.FAILURE_FACE,
    ):
        assert face.value in wire.FACES


# ───────────────────────── 作業の光 ─────────────────────────


def test_a_write_shows_as_soon_as_the_chapter_opens():
    """⚠️ **章へ入ることは滞留に数えない。** 最初の `write` はすぐ見える。"""
    room = _presence()
    assert _start(room, 0.0).light is Light.DIM
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING


def test_the_work_light_does_not_change_more_often_than_the_dwell():
    """⚠️ **道具のたびに色が変われば、それは鏡であり、相棒ではない。**"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING
    assert room.offer("main", "PreToolUse", 1.2, work="read").light is Light.WRITING
    assert room.offer("main", "PreToolUse", 5.4, work="read").light is Light.WRITING
    assert room.offer("main", "PreToolUse", 5.5, work="read").light is Light.DIM


def test_leaving_the_chapter_is_not_held_by_the_dwell():
    """⛔ **滞留は `working` の内側の規則である。** 章の出入りは即座である。"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING

    blocked = room.offer("main", "PermissionRequest", 0.6)
    assert blocked.phase is Phase.BLOCKED and blocked.light is Light.ALERT

    back = room.offer("main", "PostToolUse", 0.7, work="run")
    assert back.phase is Phase.WORKING
    assert back.light is Light.BUSY, "入り直した章は、滞留を待たない"


def test_a_background_window_does_not_touch_the_light():
    """⛔ **「背景の窓は何も変えない」は、この層でも真でなければならない。**

    ⚠️ **2026-10-20 のデモで、これが偽だった**——背後の窓の `run` が、見ている窓の
    光を `writing` から `busy` へ変えた。**語は部屋に1つだからである。**
    """
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING

    distant = room.offer("other", "PreToolUse", 6.0, work="run")
    assert distant.reason == DISTANT
    assert distant.light is Light.WRITING, "背後の窓の語で、見ている窓の光が変わった"

    # ⛔ **語を覚えていてもいけない。** 覚えれば、次の道具が `busy` へ飛ぶ。
    assert room.offer("main", "PreToolUse", 6.1, work="write").light is Light.WRITING


def test_a_background_failure_does_not_flash():
    """⛔ **背後の窓の失敗は、見ている窓の `alert` を点さない。**"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING

    distant = room.offer("other", "PostToolUseFailure", 0.6)
    assert distant.reason == DISTANT
    assert distant.light is Light.WRITING

    # ⚠️ **点滅の期限が置かれていれば、この刻みが `flashed` を返す。**
    assert room.tick(0.6 + FAILURE_FLASH_SECONDS) is None


def test_a_new_chapter_does_not_inherit_the_last_word():
    """⚠️ **語は章に属する。** 前の章の最後の道具の色で、次の章を開かない。"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="run").light is Light.BUSY
    assert room.offer("main", "Stop", 1.0).phase is Phase.CLOSING

    decision = room.offer("main", "UserPromptSubmit", 2.0)
    assert decision.phase is Phase.WORKING
    assert decision.light is Light.DIM, "前の章の run を、次の章が着ていた"


def test_a_blocked_pause_keeps_the_word():
    """⚠️ **許可待ちは章の途中である。** 戻ったとき、同じ作業が続いている。"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING
    assert room.offer("main", "PermissionRequest", 0.6).phase is Phase.BLOCKED

    back = room.offer("main", "PostToolUse", 0.7)   # ⚠️ 語を運ばない事象
    assert back.phase is Phase.WORKING
    assert back.light is Light.WRITING


def test_a_work_word_on_an_event_that_carries_none_is_ignored():
    """⛔ **語は、それを運ぶ事象のものである。** `Stop` が `run` を名乗っても覚えない。"""
    room = _presence()
    _start(room, 0.0)
    room.offer("main", "Stop", 0.5, work="run")
    room.tick(4.0)                                    # 締めの表情が明ける
    decision = room.offer("main", "UserPromptSubmit", 4.5)
    assert decision.phase is Phase.WORKING
    assert decision.light is Light.DIM, "busy ではなく、知らされていない作業の光"


def test_an_unknown_work_word_is_not_remembered():
    """⛔ **知らない語を覚えれば、次の判定がその語で光る。**"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING
    assert room.offer("main", "PreToolUse", 6.0, work="dance").light is Light.WRITING


def test_lively_changes_the_light_sooner():
    """⚠️ **賑やかな側は、滞留が短いだけである。** 光の意味は変わらない。"""
    room = _presence(PRESENCE_LIVELY)
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").light is Light.WRITING
    assert room.offer("main", "PreToolUse", 2.4, work="read").light is Light.WRITING
    assert room.offer("main", "PreToolUse", 2.5, work="read").light is Light.DIM


# ───────────────────────── 失敗の長さ ─────────────────────────


def test_one_failure_is_visible_for_two_seconds():
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
    # ⚠️ **この行は 2026-10-24 まで `face is None` だった**——「点滅は顔を連れて
    #    こない」。**顔を着せた日から、脱ぐのも点滅の仕事である**——`None` は
    #    電線の上で「変えない」であり、**基板は `startled` を着たままになる。**
    assert done.face is Face.CURIOUS, "点滅が、着せた顔を脱がせていない"
    assert done.sound is None
    assert done.light is Light.DIM


def test_three_failures_hold_the_alert_past_the_flash():
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
    """⚠️ **21:00–06:00 は無音であり、存在しない時間ではない。**"""
    room = _presence(sound=True)
    _start(room, 0.0)
    _rest(room, 0.0)
    assert room.offer("main", "InstructionsLoaded", 95.0, quiet=True).sound is None


# ───────────────────────── ダイヤル ─────────────────────────


def test_quiet_closes_every_channel_this_layer_added():
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


def test_the_layer_changes_the_light_and_the_face_and_nothing_else():
    """⛔ **この層が持つのは、光と顔の2つである。**

    ⚠️ **この検査は 2026-10-24 まで「顔はこの層のものではない」と主張していた**
    （`test_the_layer_changes_no_field_but_the_light`、`decision.face is None`）。
    **著者の「表情も自然に連動させたい」が、その主張を反転させた。**
    ⛔ 身振り・体・音・`sent` は、いまもこの層のものではない。
    """
    room = _presence()
    _start(room, 0.0)
    decision = room.offer("main", "PreToolUse", 0.5, work="write")

    assert decision.light is Light.WRITING
    assert decision.face is Face.FOCUSED, "write の顔が focused でない"
    assert decision.gesture is None
    assert decision.sound is None
    assert decision.sent is False
    assert decision.event == "PreToolUse"


def test_without_a_flash_the_deadline_is_the_rooms():
    """⚠️ **期限は1つ増える。増えていないときは、部屋のものがそのまま出る。**"""
    room = _presence()
    _start(room, 0.0)
    assert room.deadline == pytest.approx(IDLE_SECONDS)


# ───────────────────────── 作業の顔（2026-10-24） ─────────────────────────


def test_the_face_and_the_light_move_in_one_decision():
    """⛔ **光と顔は、同じ判定から出る。** 片方だけが先に動く形を作らない。

    ⚠️ **2つの欄を別々に置く日が、この規則の破れである**——`write` の枠に
    `busy` と `focused` が並ぶような日である。
    """
    room = _presence()
    opened = _start(room, 0.0)
    assert (opened.light, opened.face) == (Light.DIM, Face.CURIOUS)

    written = room.offer("main", "PreToolUse", 0.5, work="write")
    assert (written.light, written.face) == (Light.WRITING, Face.FOCUSED)

    # ⚠️ **滞留の内側では、2つとも動かない。**
    held = room.offer("main", "PreToolUse", 1.2, work="run")
    assert (held.light, held.face) == (Light.WRITING, Face.FOCUSED)

    # ⚠️ **滞留が明ければ、2つとも動く。**
    ran = room.offer("main", "PreToolUse", 6.0, work="run")
    assert (ran.light, ran.face) == (Light.BUSY, Face.WATCHING)


def test_an_untold_work_gets_the_rooms_face():
    """⚠️ **知らされていない作業の顔は `curious` である**——第1層が `working` で出す顔。

    ⛔ **「変えない」ではない。** `write` の後に `read` が来て顔が `focused` のままなら、
    光は `dim`、顔は `focused` という、**2つが食い違う枠**が出る。
    """
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").face is Face.FOCUSED
    decision = room.offer("main", "PreToolUse", 6.0, work="read")
    assert (decision.light, decision.face) == (Light.DIM, Face.CURIOUS)


def test_a_background_window_paints_neither():
    """⛔ **背後の窓は、光も顔も変えない。**

    ⚠️ **`witness` は第1層の素の顔を運ぶ**——そのまま返せば、背後の道具1つで
    **見ている窓の `focused` が `curious` へ落ちる**。光と同じ理由である。
    """
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").face is Face.FOCUSED

    distant = room.offer("other", "PreToolUse", 6.0, work="run")
    assert distant.reason == DISTANT
    assert (distant.light, distant.face) == (Light.WRITING, Face.FOCUSED)


def test_the_face_is_forgotten_with_the_word():
    """⚠️ **顔も語に属する。** 前の章の `focused` で、次の章を開かない。"""
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").face is Face.FOCUSED
    room.offer("main", "Stop", 1.0)
    room.tick(1.0 + 4.0)                              # 締めの表情が明ける

    decision = room.offer("main", "UserPromptSubmit", 6.0)
    assert decision.phase is Phase.WORKING
    assert (decision.light, decision.face) == (Light.DIM, Face.CURIOUS)


def test_a_failure_flashes_startled_and_returns_to_the_work_face():
    """⛔ **2秒の後に戻るのは、この層の顔である。**

    ⚠️ **`None` ではない。** 1回目の `PostToolUseFailure` で第1層が置く顔は
    第1層の欄では `None` であり、`None` は*変えない*を意味する——それを返せば、
    **基板は `startled` を着たままになる。**
    """
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").face is Face.FOCUSED

    failed = room.offer("main", "PostToolUseFailure", 1.0)
    assert failed.face is Face.STARTLED, "失敗が顔を着ていない"
    assert failed.light is Light.ALERT

    done = room.tick(1.0 + FAILURE_FLASH_SECONDS)
    assert done is not None and done.reason == FLASHED
    assert done.face is Face.FOCUSED, "作業の顔ではなく、別の顔へ戻った"
    assert done.light is Light.WRITING


def test_quiet_paints_no_face_of_its_own():
    """⚠️ **静かな側は、この層が着せた顔を脱ぐ**——光を `dim` にするのと同じ判断である。

    ⛔ **戻り値の顔は塗り替えない。** 第1層の顔（挨拶・締め・`sleepy`）は
    この層のものではない——`None` は「変えない」であり、**隠すことではない。**
    """
    room = _presence(PRESENCE_QUIET, sound=True)
    _start(room, 0.0)
    decision = room.offer("main", "PreToolUse", 0.5, work="write")
    assert decision.light is Light.DIM
    assert decision.face is None, "静かな側が、この層の顔を着せている"


def test_a_flash_that_spans_a_change_of_work_returns_both_fields_together():
    """⛔ **点滅の2秒のあいだに作業が変われば、戻る顔もその作業のものである。**

    ⚠️ **この検査は、実機が先に見つけた欠陥のためのものである**（2026-10-24）。
    最初の実装は「点滅の前に着ていた顔」を覚えて戻していたので、`write` の最中に
    失敗し、その2秒のあいだに `run` が来た日、点滅の刻みは
    **`light: "busy"` と `face: "focused"` が並ぶ枠**を書いた——**光と顔は1つの判定で
    動く**という、この層が同じ日に立てた規則の、ただ1つの破れである。
    ⇒ **戻すのは「そのとき欲しい顔」であり、滞留は点滅の終わりで振り直される**
    （光がそうしてきたのと同じである）。
    """
    room = _presence()
    _start(room, 0.0)
    assert room.offer("main", "PreToolUse", 0.5, work="write").face is Face.FOCUSED

    failed = room.offer("main", "PostToolUseFailure", 1.0)
    assert (failed.light, failed.face) == (Light.ALERT, Face.STARTLED)

    # ⚠️ **点滅の途中で語が変わった。** ⛔ **滞留は点滅を割らない**——1.5 秒では
    #    まだ `alert` のままで、顔の欄は `null`（*変えない*）であり、基板は
    #    `startled` を着続ける。**変わるのは点滅が尽きた刻みである。**
    moved = room.offer("main", "PreToolUse", 1.5, work="run")
    assert (moved.light, moved.face) == (Light.ALERT, None)

    done = room.tick(1.0 + FAILURE_FLASH_SECONDS)
    assert done is not None and done.reason == FLASHED
    assert (done.light, done.face) == (Light.BUSY, Face.WATCHING), (
        "点滅が、いま欲しい顔ではない顔へ戻した"
    )
