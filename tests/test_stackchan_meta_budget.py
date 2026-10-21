# -*- coding: utf-8 -*-
"""**枠・予算・失効・冷却 —— 声の間隔。**

⛔ **中心は2つである。** 候補の枠は**セッションごとに1つ**（全体で1つにすると、
前のセッションの候補が新しいセッションの文脈へ渡る——**間違って届く**）、
そして**予算と冷却は全体で1つ**（**口は1つしかない**）。

⚠️ **`superseded` は損失ではない。** 競合した回数であり、勝った候補が
後で配送されることもある。⇒ **落ちた理由を足しても候補の総数にはならない。**
"""
from __future__ import annotations

import pytest

from projects.stackchan_meta.budget import (
    BUDGET_SECONDS,
    COOLDOWN_SECONDS,
    PRIORITY,
    TTL_SECONDS,
    WHY,
    Budget,
    Drop,
)
from projects.stackchan_meta.candidates import Candidate


def candidate(kind: str = "turn-review") -> Candidate:
    base: dict[str, dict[str, object]] = {
        "context-pressure": {"compactions": 1},
        "turn-review": {"seconds": 200, "tools": 31, "longest": 0, "word": None},
        "failure-loop": {"failures": 2},
    }
    return Candidate(kind=kind, evidence=base[kind], expires_after=TTL_SECONDS)


# ---------------------------------------------------------------------------
# 枠はセッションごと
# ---------------------------------------------------------------------------


def test_one_slot_per_session_and_a_second_candidate_supersedes():
    budget = Budget()
    assert budget.offer(candidate("turn-review"), "a", 0.0) is None
    drop = budget.offer(candidate("failure-loop"), "a", 1.0)
    assert drop == Drop(kind="turn-review", why="superseded")
    assert budget.pending("a").kind == "failure-loop", "⚠️ 強いほうが残る"


def test_a_weaker_candidate_does_not_displace_a_stronger_one():
    budget = Budget()
    budget.offer(candidate("failure-loop"), "a", 0.0)
    drop = budget.offer(candidate("turn-review"), "a", 1.0)
    assert drop == Drop(kind="turn-review", why="superseded")
    assert budget.pending("a").kind == "failure-loop"


def test_the_priority_order_is_failure_then_context_then_review():
    assert PRIORITY["failure-loop"] < PRIORITY["context-pressure"] < PRIORITY["turn-review"]


def test_a_candidate_never_crosses_into_another_session():
    budget = Budget()
    budget.offer(candidate(), "a", 0.0)
    assert budget.prompt("b", 1.0) == (None, None)
    assert budget.pending("a") is not None, "⚠️ a の候補は a の枠に残る"


def test_the_slot_is_global_so_two_sessions_can_each_hold_one():
    """⚠️ **枠が別でも、口は1つである**——予算と冷却は全体で1つ。"""
    budget = Budget()
    budget.offer(candidate(), "a", 0.0)
    budget.offer(candidate(), "b", 0.0)
    assert budget.pending("a") is not None and budget.pending("b") is not None
    first, drop = budget.prompt("a", 1.0)
    assert drop is None and first is not None
    second, drop = budget.prompt("b", 2.0)
    assert second is None and drop == Drop(kind="turn-review", why="budget")


# ---------------------------------------------------------------------------
# 渡したら消える
# ---------------------------------------------------------------------------


def test_a_delivery_clears_the_slot_and_never_repeats():
    budget = Budget()
    budget.offer(candidate(), "a", 0.0)
    delivered, drop = budget.prompt("a", 1.0)
    assert delivered is not None and drop is None
    assert budget.pending("a") is None
    assert budget.prompt("a", 2.0) == (None, None)


def test_an_empty_slot_delivers_nothing_and_drops_nothing():
    assert Budget().prompt("a", 1.0) == (None, None)


# ---------------------------------------------------------------------------
# 失効・予算・冷却
# ---------------------------------------------------------------------------


def test_a_candidate_lives_for_ten_minutes_and_not_longer():
    budget = Budget()
    budget.offer(candidate(), "a", 0.0)
    delivered, drop = budget.prompt("a", TTL_SECONDS)
    assert delivered is not None and drop is None, "⚠️ ちょうど10分は生きている"

    budget = Budget()
    budget.offer(candidate(), "a", 0.0)
    delivered, drop = budget.prompt("a", TTL_SECONDS + 0.1)
    assert delivered is None and drop == Drop("turn-review", "expired")


def test_fifteen_minutes_between_deliveries_across_sessions():
    budget = Budget()
    budget.offer(candidate("turn-review"), "a", 0.0)
    assert budget.prompt("a", 1.0)[0] is not None
    budget.offer(candidate("turn-review"), "b", 100.0)
    delivered, drop = budget.prompt("b", 200.0)
    assert delivered is None
    assert drop == Drop(kind="turn-review", why="budget")
    assert BUDGET_SECONDS == 900.0


def test_the_cooldown_is_per_kind_and_global():
    budget = Budget()
    budget.offer(candidate("turn-review"), "a", 0.0)
    assert budget.prompt("a", 1.0)[0] is not None

    # ⚠️ 予算（15分）は明けているが、turn-review の冷却（30分）は明けていない。
    budget.offer(candidate("turn-review"), "a", 1000.0)
    delivered, drop = budget.prompt("a", 1000.0)
    assert delivered is None and drop == Drop("turn-review", "cooldown")

    # ⚠️ 別の語は別の冷却である。
    budget.offer(candidate("failure-loop"), "a", 1000.0)
    delivered, drop = budget.prompt("a", 1000.0)
    assert delivered is not None and drop is None
    assert COOLDOWN_SECONDS["failure-loop"] < COOLDOWN_SECONDS["turn-review"]


def test_the_cooldown_follows_the_word_across_sessions():
    """⚠️ **冷却は語のものであり、セッションのものではない。**

    ⛔ **`failure-loop` ではこの検査を作れない**——冷却10分は予算15分より短いので、
    予算が明けた時点で冷却も必ず明けている。**`turn-review`（30分）でだけ見える。**
    """
    budget = Budget()
    budget.offer(candidate("turn-review"), "a", 0.0)
    assert budget.prompt("a", 1.0)[0] is not None
    budget.offer(candidate("turn-review"), "b", 1000.0)
    delivered, drop = budget.prompt("b", 1000.0)
    assert delivered is None and drop == Drop("turn-review", "cooldown")


def test_expiry_is_checked_before_the_budget():
    budget = Budget()
    budget.offer(candidate(), "a", 0.0)
    delivered, drop = budget.prompt("a", 5000.0)
    assert delivered is None
    assert drop == Drop("turn-review", "expired"), "⚠️ 理由は1つだけ書く"


# ---------------------------------------------------------------------------
# 語彙
# ---------------------------------------------------------------------------


def test_the_drop_reasons_are_closed():
    assert WHY == ("budget", "cooldown", "expired", "superseded")
    with pytest.raises(ValueError):
        Drop("turn-review", "too noisy")


def test_a_drop_is_one_log_line_with_no_free_text():
    row = Drop("turn-review", "budget").as_dict(123.5)
    assert row == {"meta": "dropped", "kind": "turn-review",
                   "why": "budget", "at": 123.5}
