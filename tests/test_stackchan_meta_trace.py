# -*- coding: utf-8 -*-
"""**台帳 —— ターンの数え方。** ここが狂えば、規則は正しいまま誤った数を見る。

⛔ **いちばん大事な1つは「道具1回」の単位である。** `PreToolUse` と `PostToolUse`
の両方を数えれば、**1回の呼び出しが2回になる**（実測: 1,645 / 1,546）。
連続の手数も同じだけ水増しされ、**「25回」が実際は約12回になる。**
⇒ **同じ回数だけ流して、道具は1回であることを押さえる。**

⚠️ **このファイルは時計を測らない。** `at` は値で来る——**それが再生できる理由である。**
"""
from __future__ import annotations

import pathlib

import pytest

from projects.stackchan.behaviors import STEALS
from projects.stackchan_meta.trace import CLOSES, Trace

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def opened(trace: Trace, session: str = "s", at: float = 0.0):
    return trace.observe(session, "UserPromptSubmit", at)


# ---------------------------------------------------------------------------
# 開く・閉じる・窓
# ---------------------------------------------------------------------------


def test_a_turn_opens_on_a_prompt_and_closes_on_stop():
    trace = Trace()
    moment = opened(trace, at=10.0)
    assert moment is not None and moment.opened
    assert moment.turn.start == 10.0
    assert trace.held == "s"

    moment = trace.observe("s", "Stop", 25.0)
    assert moment is not None and moment.closed
    assert moment.turn.start == 10.0
    assert trace.closed == 1 and trace.prompts == 1
    assert trace.turns == {}


def test_stop_failure_closes_and_session_end_closes_without_a_window_move():
    trace = Trace()
    opened(trace, at=0.0)
    moment = trace.observe("s", "StopFailure", 5.0)
    assert moment is not None and moment.closed and moment.event == "StopFailure"
    assert trace.held == "s", "⛔ Stop は窓を移さない"

    opened(trace, at=6.0)
    moment = trace.observe("s", "SessionEnd", 7.0)
    assert moment is not None and moment.closed and moment.event == "SessionEnd"
    assert trace.held == "s"


def test_a_second_prompt_closes_the_first_turn_as_interrupted():
    trace = Trace()
    opened(trace, at=0.0)
    trace.observe("s", "PreToolUse", 1.0, "read")
    trace.observe("s", "UserPromptSubmit", 500.0)
    assert trace.interrupted == 1
    assert trace.turns["s"].start == 500.0
    assert trace.turns["s"].tools == 0, "⚠️ 新しいターンは0から数える"


def test_a_distant_window_is_counted_nowhere_but_its_turn_still_closes():
    trace = Trace()
    opened(trace, session="a", at=0.0)
    trace.observe("b", "SessionStart", 1.0)
    assert trace.held == "b"

    assert trace.observe("a", "PreToolUse", 2.0, "read") is None
    assert trace.turns["a"].tools == 0, "⛔ 背後の窓の事象は数えない"

    assert trace.observe("a", "Stop", 3.0) is None
    assert trace.closed == 1, "⚠️ 閉じたことは数える。声はかけない"


def test_permission_request_moves_the_window_without_opening_a_turn():
    trace = Trace()
    trace.observe("b", "PermissionRequest", 1.0)
    assert trace.held == "b"
    assert trace.turns == {}
    assert trace.prompts == 0


def test_the_window_set_is_the_first_layers_and_not_a_copy():
    """⛔ **写さない。** 第1層が緩んだ日に、こちらも同じ日に緩む。"""
    assert STEALS == {"SessionStart", "UserPromptSubmit", "PermissionRequest"}
    assert CLOSES.isdisjoint(STEALS), "⚠️ 閉じる事象は窓を移さない"


# ---------------------------------------------------------------------------
# 呼び出しの単位 —— このファイルの中心
# ---------------------------------------------------------------------------


def test_one_call_is_one_pre_tool_use_even_when_post_follows():
    trace = Trace()
    opened(trace)
    trace.observe("s", "PreToolUse", 1.0, "read")
    trace.observe("s", "PostToolUse", 1.1, "read")
    assert trace.turns["s"].tools == 1
    assert trace.turns["s"].longest == 1


def test_twenty_five_pairs_are_twenty_five_calls_not_fifty():
    trace = Trace()
    opened(trace)
    for n in range(25):
        trace.observe("s", "PreToolUse", 1.0 + n, "read")
        trace.observe("s", "PostToolUse", 1.5 + n, "read")
    assert trace.turns["s"].tools == 25
    assert trace.turns["s"].longest == 25, "⛔ 連続も水増しされない"


def test_a_post_without_a_pre_changes_no_call():
    trace = Trace()
    opened(trace)
    trace.observe("s", "PostToolUse", 1.0, "read")
    assert trace.turns["s"].tools == 0
    assert trace.turns["s"].longest == 0


# ---------------------------------------------------------------------------
# 連続・失敗・圧縮
# ---------------------------------------------------------------------------


def test_a_different_word_restarts_the_streak_and_the_longest_stays():
    trace = Trace()
    opened(trace)
    for n, word in enumerate(["read", "read", "read", "write"]):
        trace.observe("s", "PreToolUse", 1.0 + n, word)
    turn = trace.turns["s"]
    assert (turn.word, turn.streak, turn.longest) == ("write", 1, 3)


def test_a_call_without_a_word_is_a_call_but_not_a_streak():
    trace = Trace()
    opened(trace)
    trace.observe("s", "PreToolUse", 1.0, "read")
    trace.observe("s", "PreToolUse", 2.0)
    trace.observe("s", "PreToolUse", 3.0, "read")
    turn = trace.turns["s"]
    assert turn.tools == 3
    assert turn.longest == 2, "⚠️ 語の無い呼び出しは連続を切らない"


def test_failures_are_counted_in_the_turn():
    trace = Trace()
    opened(trace)
    trace.observe("s", "PostToolUseFailure", 1.0)
    trace.observe("s", "PostToolUseFailure", 2.0)
    assert trace.turns["s"].failures == 2


def test_compactions_are_counted_in_the_turn():
    trace = Trace()
    opened(trace)
    trace.observe("s", "PreCompact", 1.0)
    trace.observe("s", "PreCompact", 2.0)
    assert trace.turns["s"].compactions == 2


def test_events_with_no_turn_are_not_counted():
    trace = Trace()
    trace.observe("s", "SessionStart", 0.0)
    assert trace.observe("s", "PreToolUse", 1.0, "read") is None
    assert trace.observe("s", "Stop", 2.0) is None
    assert trace.closed == 0


# ---------------------------------------------------------------------------
# 純粋であること
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", ["trace.py", "rules.py", "candidates.py",
                                    "render.py", "budget.py", "room.py"])
def test_no_part_of_the_layer_reads_a_clock(module: str):
    source = (REPO_ROOT / "projects" / "stackchan_meta" / module).read_text("utf-8")
    for word in ("import time", "import datetime", "time.monotonic", "time.time"):
        assert word not in source


def test_the_same_script_leaves_the_same_state():
    script = [
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PreToolUse", 1.0, "read"),
        ("s", "PostToolUse", 1.1, "read"),
        ("s", "PreCompact", 2.0, None),
        ("s", "PostToolUseFailure", 3.0, None),
        ("s", "Stop", 4.0, None),
    ]
    states = []
    for _ in range(2):
        trace = Trace()
        for session, event, at, work in script:
            trace.observe(session, event, at, work)
        # ⚠️ `fired` は集合であり、順序を持たない。**中身で比べる。**
        states.append((trace.prompts, trace.closed, trace.interrupted))
    assert states[0] == states[1]


def test_an_unknown_work_word_is_refused():
    trace = Trace()
    opened(trace)
    with pytest.raises(ValueError):
        trace.observe("s", "PreToolUse", 1.0, "frobnicate")


def test_a_non_numeric_at_is_refused():
    trace = Trace()
    with pytest.raises(TypeError):
        trace.observe("s", "UserPromptSubmit", "1.0")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        trace.observe("s", "UserPromptSubmit", True)
