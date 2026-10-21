# -*- coding: utf-8 -*-
"""**規則 —— 3つの語が、閾値で鳴り、その手前で鳴らない。**

⛔ **このファイルの中心は、`long-stretch` が語彙に無いことである**（決定12）。
連続25回は `turn-review` の**証拠**になり、単独の語にならない——
`META_WIDE_TOOLS == META_STREAK` がその条件であり、**連続25回のターンは
必ず道具25回以上なので、`Stop` で閉じたターンでは振り返りが必ず立つ。**

⚠️ **「25回」は呼び出しの回数である。** 事象25行（`PreToolUse`＋`PostToolUse`）で
数えれば、**12回の呼び出しで鳴ってしまう**——それを固定する検査をここに置く。
"""
from __future__ import annotations

from projects.stackchan_meta import candidates, rules
from projects.stackchan_meta.trace import Trace


def drive(script, eager: bool = False):
    """⚠️ **台本は (session, event, at, work) の並びである。**"""
    trace = Trace()
    out = []
    for session, event, at, work in script:
        out.extend(rules.observe(trace, session, event, at, work, eager=eager))
    return trace, out


def calls(word: str, n: int, at: float = 1.0, include_post: bool = False):
    script = []
    for k in range(n):
        script.append(("s", "PreToolUse", at + k, word))
        if include_post:
            script.append(("s", "PostToolUse", at + k + 0.5, word))
    return script


# ---------------------------------------------------------------------------
# 3つの語
# ---------------------------------------------------------------------------


def test_context_pressure_fires_on_a_compaction_and_once_per_turn():
    trace, out = drive([("s", "UserPromptSubmit", 0.0, None)])
    assert out == []
    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PreCompact", 5.0, None),
    ])
    assert [c.kind for c in out] == ["context-pressure"]
    assert out[0].evidence == {"compactions": 1}

    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PreCompact", 5.0, None),
        ("s", "PreCompact", 6.0, None),
    ])
    assert [c.kind for c in out] == ["context-pressure"], "⛔ 同じターンで2度鳴らない"


def test_failure_loop_fires_at_the_second_failure_not_the_first_or_third():
    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PostToolUseFailure", 1.0, None),
    ])
    assert out == []

    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PostToolUseFailure", 1.0, None),
        ("s", "PostToolUseFailure", 2.0, None),
    ])
    assert [c.kind for c in out] == ["failure-loop"]
    assert out[0].evidence == {"failures": 2}

    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PostToolUseFailure", 1.0, None),
        ("s", "PostToolUseFailure", 2.0, None),
        ("s", "PostToolUseFailure", 3.0, None),
    ])
    assert [c.kind for c in out] == ["failure-loop"], "⛔ 鳴るのは2回目である"


def test_turn_review_fires_at_180_seconds_and_not_at_179_9():
    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "Stop", 179.9, None),
    ])
    assert out == []

    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "Stop", 180.0, None),
    ])
    assert [c.kind for c in out] == ["turn-review"]
    assert out[0].evidence == {"seconds": 180, "tools": 0,
                               "longest": 0, "word": None}


def test_turn_review_fires_at_25_calls_and_not_at_24():
    _, out = drive([("s", "UserPromptSubmit", 0.0, None)]
                   + calls("read", 24) + [("s", "Stop", 30.0, None)])
    assert out == []

    _, out = drive([("s", "UserPromptSubmit", 0.0, None)]
                   + calls("read", 25) + [("s", "Stop", 30.0, None)])
    assert [c.kind for c in out] == ["turn-review"]
    assert out[0].evidence["tools"] == 25


def test_the_boundary_is_25_calls_not_25_event_rows():
    """⛔ **13回の呼び出しを25行に水増ししても、鳴ってはならない。**"""
    script = [("s", "UserPromptSubmit", 0.0, None)]
    for k in range(13):
        script.append(("s", "PreToolUse", 1.0 + k, "read"))
    for k in range(12):
        script.append(("s", "PostToolUse", 1.5 + k, "read"))
    assert sum(1 for e in script if e[1] in ("PreToolUse", "PostToolUse")) == 25, \
        "⚠️ 道具の行は25である"
    script.append(("s", "Stop", 30.0, None))
    _, out = drive(script)
    assert out == [], "⛔ 呼び出しは13回である"


def test_a_turn_closed_by_a_prompt_is_not_reviewed_by_default():
    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "UserPromptSubmit", 500.0, None),
    ])
    assert out == [], "⚠️ 振り返る版は配送を1件も増やさなかった（§19.4）"


def test_session_end_does_not_review():
    _, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "SessionEnd", 500.0, None),
    ])
    assert out == []


def test_a_distant_window_makes_no_candidates():
    trace, out = drive([
        ("a", "UserPromptSubmit", 0.0, None),
        ("b", "UserPromptSubmit", 1.0, None),
    ] + [("a", "PreToolUse", 2.0 + k, "read") for k in range(30)]
      + [("a", "Stop", 40.0, None)])
    assert out == []
    assert trace.held == "b"


# ---------------------------------------------------------------------------
# 決定12 —— 連続は語ではない
# ---------------------------------------------------------------------------


def test_twenty_five_in_a_row_is_evidence_of_turn_review_not_a_word():
    _, out = drive([("s", "UserPromptSubmit", 0.0, None)]
                   + calls("read", 25) + [("s", "Stop", 30.0, None)])
    assert len(out) == 1, "⛔ 連続だけの候補は立たない"
    candidate = out[0]
    assert candidate.kind == "turn-review"
    assert candidate.evidence["longest"] == 25
    assert candidate.evidence["word"] == "read"
    assert "long-stretch" not in candidates.KINDS


def test_the_three_silent_words_are_not_in_the_vocabulary():
    for word in ("verification-gap", "fan-out", "probe-only"):
        assert word not in candidates.KINDS
    assert len(rules.RULES) == 3
    assert {rule.__name__ for rule in rules.RULES} == {
        "context_pressure", "failure_loop", "turn_review"
    }


def test_the_wide_threshold_and_the_streak_threshold_are_the_same_number():
    """⚠️ **これが吸収の条件である。** ずれた日に、連続だけのターンが生まれる。"""
    assert rules.META_WIDE_TOOLS == rules.META_STREAK == candidates.LONG_AT


# ---------------------------------------------------------------------------
# 強さ
# ---------------------------------------------------------------------------


def test_eager_promotes_failure_loop_and_nothing_else():
    script = [
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PreCompact", 1.0, None),
        ("s", "PostToolUseFailure", 2.0, None),
        ("s", "PostToolUseFailure", 3.0, None),
    ]
    _, out = drive(script)
    assert {c.kind: c.priority for c in out} == {
        "context-pressure": "normal", "failure-loop": "normal"
    }
    _, out = drive(script, eager=True)
    assert {c.kind: c.priority for c in out} == {
        "context-pressure": "normal", "failure-loop": "high"
    }


def test_one_candidate_per_kind_per_turn():
    trace, out = drive([
        ("s", "UserPromptSubmit", 0.0, None),
        ("s", "PreCompact", 1.0, None),
        ("s", "PostToolUseFailure", 2.0, None),
        ("s", "PostToolUseFailure", 3.0, None),
        ("s", "PostToolUseFailure", 4.0, None),
        ("s", "PreCompact", 5.0, None),
        ("s", "Stop", 200.0, None),
    ])
    kinds = [c.kind for c in out]
    assert sorted(kinds) == ["context-pressure", "failure-loop", "turn-review"]
    assert len(kinds) == len(set(kinds))
