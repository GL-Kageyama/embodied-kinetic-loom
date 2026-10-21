# -*- coding: utf-8 -*-
"""**描画 —— 1行と、1つの前置き。** 表は語ごとに1つである。

⛔ **「知らない語を黙って落とさない」を固定する。** 語彙を足した日に描画が無ければ、
**規則は鳴っているのに声が出ない**——その日を誰も数えられなくてはならない。

⚠️ **欠けた欄が `None` という文字にならないこと**を測る。テンプレートは
`str.format` である以上、**欠けた鍵は例外になる**（黙って `None` を書かない）。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from projects.stackchan_meta.candidates import KINDS, Candidate
from projects.stackchan_meta.render import LINES, PRELUDE, line, render


def candidate(kind: str, **evidence: object) -> Candidate:
    base: dict[str, dict[str, object]] = {
        "context-pressure": {"compactions": 2},
        "turn-review": {"seconds": 209, "tools": 31, "longest": 0, "word": None},
        "failure-loop": {"failures": 2},
    }
    base[kind].update(evidence)
    return Candidate(kind=kind, evidence=base[kind], expires_after=600)


# ---------------------------------------------------------------------------
# 3つの語
# ---------------------------------------------------------------------------


def test_every_word_in_the_vocabulary_has_exactly_one_line():
    assert set(LINES) == set(KINDS)


def test_context_pressure_renders_its_count():
    assert line(candidate("context-pressure")) == (
        "the conversation was compacted 2x during that turn; "
        "the earlier part is out of view"
    )


def test_turn_review_renders_seconds_and_calls():
    assert line(candidate("turn-review")) == (
        "that turn ran 209s over 31 tool calls"
    )


def test_failure_loop_renders_its_count():
    assert line(candidate("failure-loop")) == "2 failures in a row in that turn"


# ---------------------------------------------------------------------------
# 連続の話は、後半にだけ付く
# ---------------------------------------------------------------------------


def test_a_short_run_gets_no_second_half():
    text = line(candidate("turn-review", longest=3, word=None))
    assert "in a row" not in text


def test_a_long_run_gets_the_second_half():
    text = line(candidate("turn-review", longest=27, word="read"))
    assert text == (
        "that turn ran 209s over 31 tool calls, 27 of them 'read' in a row"
    )


def test_the_second_half_needs_both_the_length_and_the_word():
    """⚠️ **片方だけでは付けない。** 25回に満たない連続は、話す価値がない。"""
    fake = SimpleNamespace(
        kind="turn-review",
        evidence={"seconds": 209, "tools": 31, "longest": 24, "word": "read"},
    )
    assert "in a row" not in line(fake)
    fake = SimpleNamespace(
        kind="turn-review",
        evidence={"seconds": 209, "tools": 31, "longest": 27, "word": None},
    )
    assert "in a row" not in line(fake)


# ---------------------------------------------------------------------------
# 前置きと、語彙外
# ---------------------------------------------------------------------------


def test_the_prelude_appears_once_and_wraps_the_line():
    text = render(candidate("failure-loop"))
    assert text.count("[stack-chan meta]") == 1
    assert text.startswith("[stack-chan meta] 2 failures in a row in that turn.")
    assert text.endswith(
        "At most one sentence about it, in the user's language, "
        "and only if it still matters; otherwise say nothing."
    )
    assert text.count("At most one sentence") == 1


def test_every_candidate_renders_the_same_single_prelude():
    for kind in KINDS:
        text = render(candidate(kind))
        assert text.startswith(PRELUDE.split("{line}")[0])
        assert text.count("[stack-chan meta]") == 1


@pytest.mark.parametrize("kind", ["long-stretch", "verification-gap",
                                  "fan-out", "probe-only", "turn_review", ""])
def test_a_word_outside_the_vocabulary_is_refused_loudly(kind: str):
    fake = SimpleNamespace(kind=kind, evidence={})
    with pytest.raises(ValueError):
        line(fake)
    with pytest.raises(ValueError):
        render(fake)


def test_a_missing_evidence_field_is_an_error_not_the_word_none():
    fake = SimpleNamespace(kind="failure-loop", evidence={})
    with pytest.raises(KeyError):
        line(fake)


def test_rendering_never_writes_the_text_none():
    for kind in KINDS:
        assert "None" not in render(candidate(kind))
