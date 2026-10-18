# -*- coding: utf-8 -*-
"""**焼く前の層の、二十五の主張。**

⚠️ **何を主張していないか。** **機体が動くことは、1つも主張していない。**
ここで検査するのは、**33の事象が6つの段階・5つの顔・6つの光・5つの身振りの記号へ
どう進むか**、**失敗は3回で初めて合図になること**、**作業中は体が動かないこと**、
そして**どの判定も `sent=False` であること**である。

⛔ **身振りは候補語であり、語彙の行ではない。** 数になった日に、行が書かれる
（`references/README.md`）。**それが機体へ行く道は、このリポジトリにまだ無い**
（`docs/first-contact-stackchan.md`）。
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from projects.pet import strings
from projects.pet.expressions import State
from projects.stackchan import hooks
from engine.backend import protocol_stackchan as wire
from projects.stackchan.__main__ import build_parser, trace
from projects.stackchan.behaviors import (
    ACTED,
    BODY_COOLDOWN,
    BODY_GESTURE,
    BODY_NONE,
    BODY_STILL,
    BODY_VALUES,
    CONCERN,
    CONCERN_AFTER_FAILURES,
    DECISION_REASONS,
    DISTANT,
    EXPRESSION_SECONDS,
    GESTURES,
    IDLE_SECONDS,
    IGNORED,
    LONG_TURN_SECONDS,
    MIN_BODY_INTERVAL,
    OBSERVED,
    SETTLED,
    SLEPT,
    SOUNDS,
    STEALS,
    Companion,
    Focus,
    Light,
    Phase,
)

PACKAGE = pathlib.Path(__file__).resolve().parent.parent / "projects" / "stackchan"

#: ⚠️ **台本である。** 時刻はこの検査の中の値であり、機体の数ではない。
SCRIPT: list[tuple[str, float]] = [
    ("SessionStart", 0.0),
    ("Setup", 0.5),
    ("UserPromptSubmit", 2.0),
    ("PreToolUse", 2.1),
    ("PostToolUse", 2.2),
    ("PostToolUseFailure", 2.3),
    ("PostToolUseFailure", 2.4),
    ("PostToolUseFailure", 2.5),
    ("PermissionRequest", 2.6),
    ("PermissionDenied", 2.7),
    ("Stop", 30.0),
    ("StopFailure", 40.0),
    ("SessionEnd", 50.0),
]


# ---------------------------------------------------------------------------
# 語彙
# ---------------------------------------------------------------------------

def test_the_event_list_is_the_one_the_hook_reference_lists():
    """⚠️ **33は測った数である**（フック文書の表、2026-10-18）。増えたらここが鳴る。"""
    assert len(hooks.EVENTS) == 33
    assert len(set(hooks.EVENTS)) == 33


def test_every_event_has_exactly_one_kind():
    """⛔ **2つではない。** 遷移・証拠・無視の3つであり、重ならない。"""
    assert len(hooks.TRANSITIONS) == 6
    assert len(hooks.EVIDENCE) == 12
    assert len(hooks.IGNORED) == 15

    groups = (set(hooks.TRANSITIONS), set(hooks.EVIDENCE), set(hooks.IGNORED))
    assert groups[0] | groups[1] | groups[2] == set(hooks.EVENTS)
    assert not (groups[0] & groups[1])
    assert not (groups[0] & groups[2])
    assert not (groups[1] & groups[2])
    assert set(hooks.KINDS) == set(hooks.EVENTS)


def test_every_event_carries_a_reason_code():
    """⛔ **空欄を作らない。** 33のすべてに「なぜその扱いか」の符号がある。"""
    assert set(hooks.WHY) == set(hooks.EVENTS)
    assert set(hooks.WHY.values()) <= set(hooks.REASON_CODES)
    for event in hooks.EVENTS:
        assert hooks.WHY[event] in hooks.REASON_CODES
        assert hooks.classify(event).why == hooks.WHY[event]


def test_an_event_nobody_listed_is_refused():
    """⛔ **黙って `no-behavior` に落とさない。** 表が増えたことが見えなくなる。"""
    with pytest.raises(hooks.UnknownEvent):
        hooks.classify("ANewEvent")


# ---------------------------------------------------------------------------
# 段階・顔・光
# ---------------------------------------------------------------------------

def test_the_six_phases_are_all_reachable():
    phases = {row["phase"] for row in trace(SCRIPT, True, False)}
    assert phases == {phase.value for phase in Phase}


def test_the_five_faces_are_all_reached():
    faces = {row["face"] for row in trace(SCRIPT, True, False) if row["face"]}
    assert faces == {state.value for state in State}


def test_the_six_lights_are_all_used():
    """⚠️ **光は4つ目のチャンネルである。** 顔を見なくても、在席が分かる。"""
    lights = {row["light"] for row in trace(SCRIPT, True, False)}
    assert lights == {light.value for light in Light}


def test_a_long_turn_nods_and_a_short_turn_does_not():
    """⚠️ **返事に挨拶を重ねない。** 短いターンは、締めのうなずきを省く。"""
    long_turn = Companion()
    long_turn.offer("UserPromptSubmit", 0.0)
    closing = long_turn.offer("Stop", LONG_TURN_SECONDS)
    assert closing.gesture == "nod"
    assert closing.body == BODY_GESTURE

    short_turn = Companion()
    short_turn.offer("UserPromptSubmit", 0.0)
    closing = short_turn.offer("Stop", LONG_TURN_SECONDS - 1.0)
    assert closing.gesture is None
    assert closing.body == BODY_NONE


# ---------------------------------------------------------------------------
# 失敗と割り込み
# ---------------------------------------------------------------------------

def test_three_failures_in_a_row_are_the_first_concern():
    """⛔ **1回では鳴らさない。** テストの失敗は日常であり、怒る理由ではない。"""
    companion = Companion()
    companion.offer("UserPromptSubmit", 0.0)

    for at in (1.0, 2.0):
        assert companion.offer("PostToolUseFailure", at).reason == OBSERVED

    concern = companion.offer("PostToolUseFailure", 3.0)
    assert concern.reason == CONCERN
    assert concern.light is Light.ALERT
    assert concern.face is None, "⛔ 顔を怒らせない。光だけが引っかかりを言う"
    assert CONCERN_AFTER_FAILURES == 3

    # ⚠️ **4回目は、もう新しい合図ではない。**
    assert companion.offer("PostToolUseFailure", 4.0).reason == OBSERVED

    # ⚠️ **成功が連続を切る。** 次は1回目から数え直す。
    companion.offer("PostToolUse", 5.0)
    assert companion.offer("PostToolUseFailure", 6.0).reason == OBSERVED


def test_anger_is_reserved_for_a_failed_turn():
    """⛔ **`angry` は `StopFailure` だけである。** 道具の失敗は怒りではない。"""
    companion = Companion()
    companion.offer("UserPromptSubmit", 0.0)
    for at in (1.0, 2.0, 3.0, 4.0):
        assert companion.offer("PostToolUseFailure", at).face is not State.ANGRY

    failed = companion.offer("StopFailure", 5.0)
    assert failed.face is State.ANGRY
    assert failed.light is Light.ERROR


def test_permission_request_is_the_one_interrupt():
    """✅ **人が要る瞬間は、これ1つである。** 体が間に合わなくても、光は出る。"""
    companion = Companion()
    companion.offer("UserPromptSubmit", 0.0)

    blocked = companion.offer("PermissionRequest", 5.0)
    assert blocked.phase is Phase.BLOCKED
    assert blocked.light is Light.ALERT
    assert blocked.gesture == "look_side"

    denied = companion.offer("PermissionDenied", 6.0)
    assert denied.phase is Phase.WORKING
    assert denied.light is Light.DIM


def test_a_notification_does_not_end_the_wait():
    """⚠️ **注意の合図は、人が答えたことの証拠ではない。**"""
    companion = Companion()
    companion.offer("UserPromptSubmit", 0.0)
    companion.offer("PermissionRequest", 5.0)
    assert companion.offer("Notification", 6.0).phase is Phase.BLOCKED


# ---------------------------------------------------------------------------
# 2つ以上の窓。⚠️ 作品ではなく、作者の環境である（要求、2026-10-18）。
# ---------------------------------------------------------------------------

def test_the_first_window_to_speak_takes_the_gaze():
    """⚠️ **扉は1つである。** 最初に事象を出した窓から見る。"""
    focus = Focus()
    greeting = focus.offer("left", "SessionStart", 0.0)
    assert focus.held == "left"
    assert greeting.phase is Phase.GREETING
    assert greeting.reason == ACTED


def test_the_person_acting_in_the_other_window_moves_the_gaze():
    """✅ **人は、見ている窓でプロンプトを送る。** 注目は人の行為に従う。

    ⛔ **交互に振り向くこととは違う。** 奪うのは人の行為（と割り込み）だけで、
    道具の呼び出しでは奪わない——**首が2つの端末のあいだで震えないためである。**
    """
    focus = Focus()
    focus.offer("left", "SessionStart", 0.0)
    focus.offer("left", "UserPromptSubmit", 1.0)

    moved = focus.offer("right", "UserPromptSubmit", 5.0)
    assert focus.held == "right"
    assert moved.phase is Phase.WORKING
    assert moved.reason == ACTED

    # ⚠️ **背後の窓の道具の呼び出しは、注目を奪わない。**
    assert focus.offer("left", "PreToolUse", 6.0).reason == DISTANT
    assert focus.held == "right"


def test_a_background_window_finishing_does_not_turn_the_head():
    """⛔ **機械が終わったことは、人がそこを見ていることではない。**"""
    focus = Focus()
    focus.offer("left", "SessionStart", 0.0)

    finished = focus.offer("right", "Stop", 2.0)
    assert finished.reason == DISTANT
    assert finished.phase is not Phase.CLOSING

    failed = focus.offer("right", "StopFailure", 3.0)
    assert failed.reason == DISTANT
    assert failed.phase is not Phase.CLOSING, "⛔ 背後の窓の怒りを、顔に出さない"


def test_a_permission_request_from_the_background_window_steals_the_gaze():
    """⚠️ **唯一の割り込みは、注目を配分しない。** 人を要している側を見る。"""
    focus = Focus()
    focus.offer("left", "SessionStart", 0.0)

    blocked = focus.offer("right", "PermissionRequest", 5.0)
    assert focus.held == "right"
    assert blocked.phase is Phase.BLOCKED
    assert blocked.light is Light.ALERT

    assert focus.offer("left", "PostToolUse", 6.0).reason == DISTANT


def test_the_gaze_returns_when_the_holder_goes_quiet():
    """✅ **持ち主が黙れば、部屋はまだ起きていても、注目は離れる。**

    ⚠️ **同じ `IDLE_SECONDS` を使う。** 数は1つである——**新しい数を足さない。**
    """
    focus = Focus()
    focus.offer("left", "SessionStart", 0.0)
    focus.offer("right", "PreToolUse", 10.0)  # 部屋は起きるが、注目は動かない
    assert focus.held == "left"

    taken = focus.offer("right", "UserPromptSubmit", IDLE_SECONDS + 1.0)
    assert focus.held == "right"
    assert taken.phase is Phase.WORKING


def test_a_distant_event_still_keeps_the_room_awake():
    """⛔ **見ていないことは、死んでいることではない。** 部屋の時計は戻る。"""
    focus = Focus()
    focus.offer("left", "UserPromptSubmit", 0.0)
    focus.offer("right", "PreToolUse", IDLE_SECONDS - 5.0)

    assert focus.tick(IDLE_SECONDS) is None, "⚠️ 戻していなければ、ここで眠っていた"
    assert focus.held is None, "⚠️ 持ち主は90秒で離れる"
    slept = focus.tick(IDLE_SECONDS * 2)
    assert slept is not None and slept.reason == SLEPT


def test_the_holder_ending_frees_the_gaze():
    """⚠️ **去った窓を見続けない。** 次に事象を出した窓が取る。"""
    focus = Focus()
    focus.offer("left", "SessionStart", 0.0)
    ended = focus.offer("left", "SessionEnd", 4.0)
    assert ended.phase is Phase.RESTING
    assert focus.held is None

    woken = focus.offer("right", "PreToolUse", 5.0)
    assert focus.held == "right"
    assert woken.phase is not Phase.RESTING, "⚠️ どの事象も、休息から起こす"


def test_the_rule_does_not_count_to_two():
    """⚠️ **窓は2つに限らない。** 持ち主が1人であることだけを数える。"""
    focus = Focus()
    focus.offer("left", "SessionStart", 0.0)
    focus.offer("middle", "PreToolUse", 1.0)
    focus.offer("right", "PostToolUse", 2.0)
    assert focus.held == "left"

    # ✅ **3つ目で人が動けば、そこへ移る。**
    moved = focus.offer("right", "UserPromptSubmit", 3.0)
    assert focus.held == "right"
    assert moved.phase is Phase.WORKING

    # ⛔ **残り2つの窓は、それぞれ別に遠い。**
    assert focus.offer("left", "PostToolUse", 4.0).reason == DISTANT
    assert focus.offer("middle", "Stop", 5.0).reason == DISTANT
    assert focus.held == "right"


def test_a_script_can_name_its_windows():
    """⚠️ **行が窓を名乗らなければ、どれを見ているか読めない。**"""
    rows = trace([
        ("left", "SessionStart", 0.0),
        ("right", "PreToolUse", 1.0),
        ("left", "Stop", 5.0),
        ("right", "PermissionRequest", 6.0),
    ], True, False)

    assert {row["session"] for row in rows if row["event"]} == {"left", "right"}
    assert any(row["reason"] == DISTANT for row in rows)
    assert all(row["sent"] is False for row in rows)

    assert STEALS == {"SessionStart", "UserPromptSubmit", "PermissionRequest"}


# ---------------------------------------------------------------------------
# 生存と時計
# ---------------------------------------------------------------------------

def test_every_event_is_a_sign_of_life():
    """⛔ **`ignored` は「届いていない」ではない。** 33のすべてが休息から起こす。"""
    for event in hooks.EVENTS:
        companion = Companion()
        companion.offer("UserPromptSubmit", 0.0)
        slept = companion.tick(IDLE_SECONDS)
        assert slept is not None and slept.phase is Phase.RESTING

        woken = companion.offer(event, IDLE_SECONDS + 1.0)
        # ⚠️ **`SessionEnd` だけは、休息へ入ることが「起きた」である。**
        assert woken.phase is not Phase.RESTING or event == "SessionEnd", event


def test_an_evidence_event_resets_the_idle_timer():
    """⚠️ **長いビルドの間、ロボットは眠らない。** 道具の事象が時計を戻す。"""
    companion = Companion()
    companion.offer("UserPromptSubmit", 0.0)
    companion.offer("PostToolUse", IDLE_SECONDS - 5.0)

    assert companion.tick(95.0) is None, "⚠️ 戻していなければ、ここで眠っていた"

    slept = companion.tick(IDLE_SECONDS + IDLE_SECONDS - 5.0)
    assert slept is not None
    assert slept.reason == SLEPT
    assert (slept.phase, slept.face, slept.light) == (
        Phase.RESTING, State.SLEEPY, Light.OFF
    )


def test_an_expression_expires_and_returns_to_the_baseline():
    """⛔ **顔は、次まで残らない。** 3秒で在席へ戻る（製品の決定）。"""
    companion = Companion()
    companion.offer("SessionStart", 0.0)

    assert companion.tick(EXPRESSION_SECONDS - 0.1) is None
    settled = companion.tick(EXPRESSION_SECONDS)
    assert settled is not None
    assert settled.reason == SETTLED
    assert (settled.phase, settled.face, settled.light) == (
        Phase.PRESENT, State.CURIOUS, Light.BREATHE
    )


def test_sleeping_returns_to_the_baseline():
    companion = Companion()
    companion.offer("SessionStart", 0.0)
    assert companion.tick(EXPRESSION_SECONDS + 0.1).reason == SETTLED

    slept = companion.tick(IDLE_SECONDS)
    assert slept is not None
    assert slept.reason == SLEPT
    assert companion.tick(IDLE_SECONDS + 1.0) is None


# ---------------------------------------------------------------------------
# チャンネルと密度
# ---------------------------------------------------------------------------

def test_a_gesture_too_soon_is_dropped_but_the_light_is_not():
    """⛔ **光は、体の都合で遅れない。** 近すぎる身振りは捨てる。"""
    companion = Companion()
    assert companion.offer("SessionStart", 0.0).body == BODY_GESTURE

    blocked = companion.offer("PermissionRequest", MIN_BODY_INTERVAL - 0.5)
    assert blocked.body == BODY_COOLDOWN
    assert blocked.gesture is None
    assert blocked.phase is Phase.BLOCKED
    assert blocked.light is Light.ALERT
    assert companion.dropped == 1


def test_motion_off_keeps_the_face_and_the_light():
    """✅ **運動と音は別の軸である。** 顔と光は、どちらにも従わない。"""
    companion = Companion(motion=False)
    greeting = companion.offer("SessionStart", 0.0)
    assert greeting.body == BODY_STILL
    assert greeting.gesture is None
    assert greeting.face is State.GREETING
    assert greeting.light is Light.WARM


def test_sound_is_off_by_default_and_a_word_when_on():
    """⚠️ **既定は黙っている**（作者の決定、2026-10-18）。

    ✅ **切られていれば `None`、入っていれば語である**——2026-10-18 まで、この欄は
    真偽値であり、**どの音か**を言えなかった。**語になった日、`SessionEnd` は黙った**:
    去る窓に声をかけても、聞く人がいない。
    """
    assert Companion().offer("SessionStart", 0.0).sound is None

    companion = Companion(sound=True)
    assert companion.offer("SessionStart", 0.0).sound == "hello"
    assert companion.offer("PostToolUse", 1.0).sound is None
    assert companion.offer("SessionEnd", 2.0).sound is None


def test_every_sound_word_is_in_the_vocabulary_list():
    """⛔ **層の語と、電線の語は同じである。** 食い違った日に赤くなる。"""
    listed = set(SOUNDS)
    assert set(wire.SOUNDS) == listed
    companion = Companion(sound=True)
    for event, at in (
        ("SessionStart", 0.0),
        ("PermissionRequest", 2.0),
        ("Stop", 30.0),
        ("StopFailure", 31.0),
    ):
        assert companion.offer(event, at).sound in listed


def test_no_gesture_is_ever_sent():
    """⛔ **記号を送ったことにしない。** 機体2へ渡す数が1つも無い。"""
    rows = trace(SCRIPT, True, True)
    assert rows, "⚠️ 検査が空を回っている"
    for row in rows:
        assert row["sent"] is False
        assert row["gesture"] is None or row["gesture"] in GESTURES


def test_the_reason_and_body_sets_are_closed():
    """⛔ **理由と体の欄は、別の軸であり、どちらも閉じている。**"""
    bodies = set()
    reasons = set()
    for motion in (True, False):
        for row in trace(SCRIPT, motion, False):
            assert row["reason"] in DECISION_REASONS
            assert row["body"] in BODY_VALUES
            bodies.add(row["body"])
            reasons.add(row["reason"])
    # ⚠️ **`distant` は1つの窓の台本では届かない。** 2つの窓で届く。
    for row in trace([("left", "SessionStart", 0.0), ("right", "PreToolUse", 1.0)],
                     True, False):
        reasons.add(row["reason"])
    # ⚠️ **休息は、台本の最後の刻みで1度だけ出る。**
    for row in trace([("UserPromptSubmit", 0.0)], True, False):
        reasons.add(row["reason"])
    assert bodies == set(BODY_VALUES), bodies
    assert reasons == set(DECISION_REASONS), reasons


def test_the_trace_is_reproducible():
    """⚠️ **台本が同じなら、列も同じである。** 時計は渡された値だけである。"""
    assert trace(SCRIPT, True, False) == trace(SCRIPT, True, False)


def test_the_trace_refuses_a_script_that_runs_backwards():
    """⛔ **戻る台本は、この層の前提を破る。** 黙って走らせない。"""
    with pytest.raises(ValueError):
        trace([("SessionStart", 5.0), ("Stop", 4.0)], True, False)


# ---------------------------------------------------------------------------
# 入口と数を持たないこと
# ---------------------------------------------------------------------------

def test_the_parser_builds_in_every_language_and_the_help_differs():
    helps = {}
    for lang in strings.SUPPORTED:
        text = build_parser(lang).format_help()
        assert "stackchan_cli" not in text
        helps[lang] = text
    assert len(set(helps.values())) == 3

    args = build_parser("en").parse_args(["--event", "Stop@3"])
    assert args.event == [("main", "Stop", 3.0)]
    assert args.motion is True
    assert args.sound is False

    # ⚠️ **窓を名乗れる。** 名乗らなければ `main` である。
    windows = build_parser("en").parse_args(["--event", "left:SessionStart@0"])
    assert windows.event == [("left", "SessionStart", 0.0)]

    channels = build_parser("en").parse_args(["--motion", "off", "--sound", "on"])
    assert channels.motion is False
    assert channels.sound is True


def test_no_machine_one_name_or_number_is_in_the_package():
    """⚠️ **機体1の名前と数が、この層に1つも無い。** 借りれば「動いた」と言ってしまう。

    ⛔ **`engine` を1つも輸入しない。** この層は `Motion Intent` より上流であり、
    **下流の型に触れない**——触れれば、数の無いことが言えなくなる。
    """
    forbidden_names = {"DOF_REALITY_ENVELOPE", "DofRealityWire", "Envelope"}
    forbidden_numbers = (190, 512, 833)

    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("engine"), (path, node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("engine"), (path, alias.name)
            elif isinstance(node, ast.Name):
                assert node.id not in forbidden_names, (path, node.id)
            elif isinstance(node, ast.Attribute):
                assert node.attr not in forbidden_names, (path, node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                assert node.value not in forbidden_numbers, (path, node.value)

    assert not (PACKAGE / "motions").exists(), "機体2の意図が、いつの間にか在る"
