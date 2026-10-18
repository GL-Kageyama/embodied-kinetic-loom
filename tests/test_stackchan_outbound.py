# -*- coding: utf-8 -*-
"""**部屋の外向きの状態——判定が、機体へ渡る枠になる。**

⚠️ **このファイルが確かめるのは、枠が出る規則と、その中身が語だけであることである。**
⛔ **確かめないのは、機体へ届くことである。** 伝送路はまだ存在しない。
"""
from __future__ import annotations

import dataclasses

from engine.backend import protocol_stackchan as wire
from projects.stackchan.behaviors import Companion
from projects.stackchan.outbound import Frame, Outbound


# ---------------------------------------------------------------------------
# いつ枠が出るか。⚠️ 理由ではなく、状態そのものを見る。
# ---------------------------------------------------------------------------


def test_the_first_frame_establishes_the_state():
    """⚠️ **プロセスで最初の判定は、必ず枠になる。** 機体の状態は知られていない。

    ⚠️ **顔は `None` でありうる**——「変えない」である。**光は常に在る。**
    """
    outbound = Outbound()
    decision = Companion().offer("PreToolUse", 0.0)

    frame = outbound.frame(decision)

    assert frame == Frame(face=None, light="breathe", gesture=None)
    assert outbound.known == (None, "breathe")


def test_an_unchanged_decision_is_not_a_frame():
    """⛔ **変わらない判定は、枠にならない。** それが流れを作らない理由である。"""
    companion = Companion()
    outbound = Outbound()
    outbound.frame(companion.offer("PreToolUse", 0.0))

    assert outbound.frame(companion.offer("PostToolUse", 1.0)) is None


def test_a_light_only_change_carries_a_null_face():
    """⚠️ **`PostToolUseFailure` が3つ続くと、光だけが `alert` になる。**

    ⛔ **これは遷移事象ではない**——段階は `working` のままである。だが光は変わる。
    **だから枠は、事象の種類ではなく状態の変化で出る。** 顔は変わらないので `null` である。
    """
    companion = Companion()
    outbound = Outbound()
    outbound.frame(companion.offer("UserPromptSubmit", 0.0))

    assert outbound.frame(companion.offer("PostToolUseFailure", 1.0)) is None
    assert outbound.frame(companion.offer("PostToolUseFailure", 2.0)) is None
    frame = outbound.frame(companion.offer("PostToolUseFailure", 3.0))

    assert frame == Frame(face=None, light="alert", gesture=None)


def test_a_phase_change_carries_the_face_the_light_and_the_gesture():
    """✅ **挨拶は、3つの欄がそろって渡る。** ⚠️ **身振りは遷移でしか選ばれない。**"""
    outbound = Outbound()

    frame = outbound.frame(Companion().offer("SessionStart", 0.0))

    assert frame == Frame(face="greeting", light="warm", gesture="look_up")


def test_a_gesture_alone_is_still_a_frame():
    """⚠️ **状態が同じでも、身振りが選ばれていれば枠になる。**"""
    companion = Companion()
    outbound = Outbound()
    first = companion.offer("UserPromptSubmit", 0.0)
    outbound.frame(first)

    frame = outbound.frame(dataclasses.replace(first, gesture="nod"))

    assert frame == Frame(face=None, light="dim", gesture="nod")


def test_a_hundred_evidence_events_are_one_frame():
    """⛔ **これは流れではない。** 同じ状態の事象を100回送っても、枠は1つである。"""
    companion = Companion()
    outbound = Outbound()

    frames = [
        outbound.frame(companion.offer("PreToolUse", float(i)))
        for i in range(100)
    ]

    assert [frame for frame in frames if frame is not None] == [
        Frame(face=None, light="breathe", gesture=None)
    ]


def test_the_face_is_sent_back_only_when_it_changes():
    """⚠️ **`face: null` は「変えない」である。** 既知の顔は保たれる。"""
    outbound = Outbound()
    companion = Companion()
    outbound.frame(companion.offer("SessionStart", 0.0))       # greeting
    assert outbound.known == ("greeting", "warm")

    frame = outbound.frame(companion.offer("UserPromptSubmit", 1.0))
    assert frame == Frame(face="curious", light="dim", gesture="look_up")
    assert outbound.known == ("curious", "dim")


# ---------------------------------------------------------------------------
# 中身。⛔ 語だけであり、数は1つも無い。
# ---------------------------------------------------------------------------


def _scripted_frames() -> list[Frame]:
    companion = Companion()
    outbound = Outbound()
    frames: list[Frame] = []
    script = [
        ("SessionStart", 0.0),
        ("PreToolUse", 1.0),
        ("PermissionRequest", 2.0),
        ("PostToolUse", 3.0),
        ("PostToolUseFailure", 4.0),
        ("PostToolUseFailure", 5.0),
        ("PostToolUseFailure", 6.0),
        ("PostToolUse", 7.0),
        ("Stop", 30.0),
        ("StopFailure", 31.0),
        ("SessionEnd", 32.0),
    ]
    for event, at in script:
        frame = outbound.frame(companion.offer(event, at))
        if frame is not None:
            frames.append(frame)
    for at in (100.0, 200.0, 1000.0):
        decision = companion.tick(at)
        if decision is not None:
            frame = outbound.frame(decision)
            if frame is not None:
                frames.append(frame)
    return frames


def test_every_frame_the_room_can_make_is_in_the_contract():
    """⚠️ **契約・符号器・この層が、同じ語を綴る。** 食い違った日に赤くなる。"""
    frames = _scripted_frames()
    assert frames  # ⚠️ 空なら、この検査は何も言っていない

    for frame in frames:
        assert frame.face is None or frame.face in wire.FACES
        assert frame.light in wire.LIGHTS
        assert frame.gesture is None or frame.gesture in wire.GESTURES
        assert frame.sound is None or frame.sound in wire.SOUNDS


def test_every_frame_round_trips_on_the_wire():
    """⚠️ **枠は、そのまま1行になり、そのまま戻る。**"""
    for frame in _scripted_frames():
        command = wire.Command(face=frame.face, light=frame.light,
                               gesture=frame.gesture, sound=frame.sound)
        assert wire.decode(wire.encode(command)) == command


def test_no_number_crosses():
    """⛔ **4つの欄は、すべて語か `None` である。** 角度も周波数も無い。"""
    for frame in _scripted_frames():
        for value in (frame.face, frame.light, frame.gesture, frame.sound):
            assert value is None or isinstance(value, str)


# ---------------------------------------------------------------------------
# 音。✅ 2026-10-18 から、遷移の4つに1語ずつ載る。
# ---------------------------------------------------------------------------


def test_a_sound_alone_is_still_a_frame():
    """⚠️ **状態が同じでも、音が選ばれていれば枠になる。** ⛔ 音は状態ではない。"""
    companion = Companion(sound=True)
    outbound = Outbound()
    first = companion.offer("SessionStart", 0.0)
    outbound.frame(first)

    frame = outbound.frame(dataclasses.replace(first, sound="pip"))

    assert frame == Frame(face=None, light="warm", gesture="look_up", sound="pip")


def test_the_sound_is_off_until_the_switch_turns_it_on():
    """⚠️ **既定は off である**（作者の決定、2026-10-18）。切られていれば語は選ばれない。"""
    quiet = Companion().offer("SessionStart", 0.0)
    assert quiet.sound is None

    speaking = Companion(sound=True).offer("SessionStart", 0.0)
    assert speaking.sound == "hello"


def test_each_transition_carries_its_own_word():
    """⚠️ **4つの遷移に4つの語、そして2つの遷移は黙る。**

    ⛔ `UserPromptSubmit` は鳴らない——人はいま自分で喋った。`SessionEnd` も鳴らない——
    去る窓に声をかけない。**「遷移なら鳴る」は規則ではない。**
    """
    companion = Companion(sound=True)
    assert companion.offer("SessionStart", 0.0).sound == "hello"
    assert companion.offer("UserPromptSubmit", 1.0).sound is None
    assert companion.offer("PermissionRequest", 2.0).sound == "pip"
    assert companion.offer("PostToolUse", 3.0).sound is None
    assert companion.offer("Stop", 30.0).sound == "chime"
    assert companion.offer("StopFailure", 31.0).sound == "fall"
    assert companion.offer("SessionEnd", 32.0).sound is None
