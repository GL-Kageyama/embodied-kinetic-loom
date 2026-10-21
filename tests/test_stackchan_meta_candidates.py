# -*- coding: utf-8 -*-
"""**候補 —— 語彙が閉じていること、自由文の欄が無いこと。**

⛔ **ここが緩むと、分析器が言葉を書き始める。** 言葉を書くにはモデルが要り、
「規則だけで走る」という決定が壊れる（§11.2）。⇒ **欄の数と名前を固定する。**

⚠️ **`word` と `longest` は対である**（§11.1）。**両方向に締める**——
片方だけを締めれば、残る側が空欄になり、空欄は誰かの既定で埋まる。
"""
from __future__ import annotations

import json

import pytest

from projects.stackchan_next.work import WORK_WORDS
from projects.stackchan_meta.candidates import (
    EVIDENCE,
    KINDS,
    LONG_AT,
    PRIORITIES,
    Candidate,
)


def candidate(kind: str = "failure-loop", **evidence: object) -> Candidate:
    base: dict[str, dict[str, object]] = {
        "context-pressure": {"compactions": 1},
        "turn-review": {"seconds": 200, "tools": 31, "longest": 27, "word": "read"},
        "failure-loop": {"failures": 2},
    }
    base[kind].update(evidence)
    return Candidate(kind=kind, evidence=base[kind], expires_after=600)


# ---------------------------------------------------------------------------
# 語彙
# ---------------------------------------------------------------------------


def test_the_vocabulary_is_closed_and_has_three_words():
    assert KINDS == ("context-pressure", "turn-review", "failure-loop")
    assert set(EVIDENCE) == set(KINDS)
    assert PRIORITIES == ("low", "normal", "high")


def test_the_evidence_fields_are_fixed_per_word():
    assert EVIDENCE == {
        "context-pressure": ("compactions",),
        "turn-review": ("seconds", "tools", "longest", "word"),
        "failure-loop": ("failures",),
    }


def test_the_long_boundary_is_the_rules_number():
    from projects.stackchan_meta import rules

    assert LONG_AT == rules.META_STREAK == 25


# ---------------------------------------------------------------------------
# 閉じていること
# ---------------------------------------------------------------------------


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        Candidate(kind="long-stretch", evidence={}, expires_after=600)
    with pytest.raises(ValueError):
        Candidate(kind="verification-gap", evidence={}, expires_after=600)


def test_an_unknown_priority_is_refused():
    with pytest.raises(ValueError):
        Candidate(kind="failure-loop", evidence={"failures": 2},
                  expires_after=600, priority="urgent")


def test_a_missing_or_extra_evidence_field_is_refused():
    with pytest.raises(ValueError):
        Candidate(kind="failure-loop", evidence={}, expires_after=600)
    with pytest.raises(ValueError):
        Candidate(kind="failure-loop", evidence={"failures": 2, "message": "hi"},
                  expires_after=600)


def test_there_is_no_free_text_field():
    """⛔ **`message` は無い**（旧稿の `suggested_message` は廃止）。"""
    with pytest.raises(TypeError):
        Candidate(kind="failure-loop", evidence={"failures": 2},
                  expires_after=600, message="you seem stuck")  # type: ignore[call-arg]
    assert set(candidate().as_dict()) == {
        "kind", "evidence", "priority", "expires_after"
    }


def test_the_evidence_cannot_be_mutated_after_it_is_made():
    made = candidate()
    with pytest.raises(TypeError):
        made.evidence["failures"] = 9  # type: ignore[index]


# ---------------------------------------------------------------------------
# word と longest
# ---------------------------------------------------------------------------


def test_a_long_run_carries_a_word():
    made = candidate("turn-review", longest=25, word="write")
    assert made.evidence["longest"] == 25
    assert made.evidence["word"] == "write"


def test_a_short_run_carries_no_word():
    made = candidate("turn-review", longest=3, word=None)
    assert made.evidence["word"] is None


def test_a_word_below_the_boundary_is_refused():
    with pytest.raises(ValueError):
        candidate("turn-review", longest=24, word="read")
    with pytest.raises(ValueError):
        candidate("turn-review", longest=0, word="read")


def test_a_run_at_the_boundary_without_a_word_is_refused():
    with pytest.raises(ValueError):
        candidate("turn-review", longest=25, word=None)


def test_a_word_outside_the_six_is_refused():
    with pytest.raises(ValueError):
        candidate("turn-review", longest=25, word="frobnicate")


# ---------------------------------------------------------------------------
# 数
# ---------------------------------------------------------------------------


def test_a_bool_is_not_a_number():
    """⚠️ `True` は `int` である。**数として通してはならない。**"""
    with pytest.raises(TypeError):
        candidate("failure-loop", failures=True)
    with pytest.raises(TypeError):
        candidate("turn-review", tools=True)


def test_a_float_or_negative_count_is_refused():
    with pytest.raises(TypeError):
        candidate("failure-loop", failures=2.0)
    with pytest.raises(ValueError):
        candidate("failure-loop", failures=-1)


def test_expiry_must_be_a_positive_number():
    with pytest.raises(ValueError):
        Candidate(kind="failure-loop", evidence={"failures": 2}, expires_after=0)
    with pytest.raises(TypeError):
        Candidate(kind="failure-loop", evidence={"failures": 2}, expires_after=True)
    with pytest.raises(TypeError):
        Candidate(kind="failure-loop", evidence={"failures": 2},
                  expires_after="600")  # type: ignore[arg-type]


def test_every_candidate_is_json_serialisable():
    for kind in KINDS:
        text = json.dumps(candidate(kind).as_dict())
        assert set(json.loads(text)) == {
            "kind", "evidence", "priority", "expires_after"
        }


def test_the_six_words_are_the_second_layers():
    assert WORK_WORDS == ("read", "write", "run", "search", "plan", "other")
