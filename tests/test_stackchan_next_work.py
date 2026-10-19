# -*- coding: utf-8 -*-
"""**作業の語 —— 何を読んで、何を通さないか。**

⛔ **このファイルの中心は、光の話ではない。** **同乗できないこと**である——
`tool_input`（ファイルパス）も `prompt` も、**この層を通る道が無い**ことを、
関数の形で押さえる。
"""
from __future__ import annotations

import json

import pytest

from projects.stackchan import hooks
from projects.stackchan_next import work
from projects.stackchan_next.client import line_from


def test_the_six_words_are_closed_and_the_table_only_points_into_it():
    """⚠️ **表の行き先は、6語のどれかである。** 7語目を作らない。"""
    assert work.WORK_WORDS == ("read", "write", "run", "search", "plan", "other")
    assert set(work.TOOLS.values()) <= set(work.WORK_WORDS)
    assert work.OTHER in work.WORK_WORDS


@pytest.mark.parametrize(
    ("tool", "word"),
    [
        ("Read", "read"),
        ("Glob", "read"),
        ("Grep", "read"),
        ("Edit", "write"),
        ("Write", "write"),
        ("MultiEdit", "write"),
        ("NotebookEdit", "write"),
        ("Bash", "run"),
        ("BashOutput", "run"),
        ("KillShell", "run"),
        ("WebSearch", "search"),
        ("WebFetch", "search"),
        ("Task", "plan"),
        ("TodoWrite", "plan"),
        ("EnterPlanMode", "plan"),
        ("ExitPlanMode", "plan"),
    ],
)
def test_every_named_tool_lands_on_its_word(tool, word):
    assert work.word_for(tool) is word


def test_an_unknown_tool_is_other_not_a_refusal():
    """⚠️ **知らない道具は落とさない。** それも作業の1つの形である。"""
    assert work.word_for("SomeFutureTool") == work.OTHER
    assert work.word_for("") == work.OTHER


@pytest.mark.parametrize("value", [None, 3, True, ["Read"], {"tool_name": "Read"}])
def test_a_non_string_is_other(value):
    """⛔ **型を見るのは、辞書に当たらないからである**——断るためではない。"""
    assert work.word_for(value) == work.OTHER


def test_only_two_events_carry_a_work_word():
    assert work.WORK_EVENTS == frozenset({"PreToolUse", "PostToolUse"})
    for event in hooks.EVENTS:
        assert work.carries_work(event) is (event in work.WORK_EVENTS)


# ───────────────────────── 組み直し ─────────────────────────


def _payload(**extra):
    base = {"session_id": "s-1", "hook_event_name": "PreToolUse"}
    base.update(extra)
    return base


def test_the_line_carries_exactly_session_event_and_work():
    line = line_from(_payload(tool_name="Edit"))
    assert json.loads(line) == {"session": "s-1", "event": "PreToolUse", "work": "write"}


def test_a_prompt_cannot_ride_along():
    """⛔ **ここがこの層のプライバシーである。** 入力に在っても、行に在りはしない。"""
    line = line_from(_payload(
        tool_name="Bash",
        prompt="delete everything",
        tool_input={"command": "rm -rf /"},
        tool_response={"stdout": "secret"},
        cwd="/Users/user/secret-project",
    ))
    assert json.loads(line) == {"session": "s-1", "event": "PreToolUse", "work": "run"}
    for forbidden in ("prompt", "tool_input", "tool_response", "cwd", "secret"):
        assert forbidden not in line


def test_an_event_that_carries_no_work_carries_no_field():
    """⚠️ **`Stop` に `tool_name` が在っても、載せない。** 語の意味が薄まる。"""
    line = line_from({"session_id": "s-1", "hook_event_name": "Stop",
                      "tool_name": "Edit"})
    assert json.loads(line) == {"session": "s-1", "event": "Stop"}


def test_a_missing_tool_name_is_not_the_word_other():
    """⚠️ **「その他」と「知らされていない」は別である。** どちらも `dim` になるが、
    **欄が在るかどうかで読める。**"""
    line = line_from(_payload())
    assert "work" not in json.loads(line)


def test_an_unknown_event_is_not_sent():
    assert line_from({"session_id": "s-1", "hook_event_name": "NoSuchEvent"}) is None


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "x",
        {"session_id": "", "hook_event_name": "PreToolUse"},
        {"session_id": "s-1"},
        {"session_id": "s-1", "hook_event_name": ""},
        {"session_id": 4, "hook_event_name": "PreToolUse"},
    ],
)
def test_a_payload_that_cannot_be_rebuilt_is_not_sent(payload):
    assert line_from(payload) is None


def test_the_line_ends_with_one_newline():
    line = line_from(_payload(tool_name="Read"))
    assert line.endswith("\n") and not line.endswith("\n\n")
