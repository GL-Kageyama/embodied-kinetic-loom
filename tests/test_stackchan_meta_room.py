# -*- coding: utf-8 -*-
"""**監修の部屋 —— 事象1つを、記録1行と、返事の1行にする。**

⚠️ **ここが縁から見た第3層の全部である**（設計 §7.2）。時計もソケットも読まないので、
**台本の時刻だけで、配送・失効・予算・冷却まで試験できる。**

⛔ **このファイルが確かめないこと:** ソケット、糸、フック、そして**声が人に届くこと**。
それは `tests/test_stackchan_next_daemon.py`（縁）と、Phase 4 のフックの側である。
"""
from __future__ import annotations

import json

from projects.stackchan_meta import (
    TTL_SECONDS,
    Candidate,
    MetaRoom,
    render,
)


def drive(room: MetaRoom, session: str = "m", at: float = 0.0,
          tools: int = 25, close: str = "Stop") -> None:
    """**1ターンを、台本の時刻で閉じる。** ⚠️ **ターンはプロンプトで開く。**"""
    room.observe(session, "UserPromptSubmit", at)
    for index in range(tools):
        room.observe(session, "PreToolUse", at + 0.001 * index)
    room.observe(session, close, at + 0.5)


def review(seconds: int = 0, tools: int = 25) -> Candidate:
    return Candidate(kind="turn-review",
                     evidence={"seconds": seconds, "tools": tools,
                               "longest": 0, "word": None},
                     expires_after=TTL_SECONDS)


# ---------------------------------------------------------------------------
# 作る・渡す —— 1行ずつ、別の行にする（§10.6）
# ---------------------------------------------------------------------------


def test_a_closed_turn_becomes_a_candidate_row_and_nothing_else():
    rows: list[dict] = []
    room = MetaRoom(emit=rows.append)
    drive(room)

    assert rows == [{"meta": "candidate", "kind": "turn-review",
                     "session": "m", "at": 0.5}]


def test_the_sentence_is_carried_by_the_next_prompt_not_by_the_candidate():
    """⛔ **作ったことと、渡したことを、同じ行にしない。**

    まとめれば、「作ったが渡らなかった」が数えられない（§10.6）。
    """
    rows: list[dict] = []
    room = MetaRoom(emit=rows.append)
    drive(room)
    said = room.observe("m", "UserPromptSubmit", 10.0)

    assert said == render(review())
    assert rows[-1] == {"meta": "delivered", "kind": "turn-review",
                        "session": "m", "at": 10.0}


def test_a_prompt_with_nothing_pending_says_nothing():
    room = MetaRoom()
    assert room.observe("m", "UserPromptSubmit", 0.0) is None


def test_the_room_works_without_a_sink():
    """⚠️ **書き先は値である。** 渡さなければ、何も書かない——**それでも数える。**"""
    room = MetaRoom()
    drive(room)
    assert room.observe("m", "UserPromptSubmit", 10.0) is not None


def test_the_same_script_leaves_the_same_rows_and_the_same_sentence():
    def run() -> tuple[list[dict], str | None]:
        rows: list[dict] = []
        room = MetaRoom(emit=rows.append)
        drive(room)
        said = room.observe("m", "UserPromptSubmit", 10.0)
        return rows, said

    assert run() == run()


# ---------------------------------------------------------------------------
# 落ちた —— `why` は閉じた4語であり、行に `session` を載せない
# ---------------------------------------------------------------------------


def test_the_budget_drops_a_second_delivery_and_says_why():
    rows: list[dict] = []
    room = MetaRoom(emit=rows.append)
    drive(room, "a", 0.0)
    room.observe("a", "UserPromptSubmit", 10.0)   # 配送

    drive(room, "b", 20.0)
    room.observe("b", "UserPromptSubmit", 30.0)   # 10秒後の2度目

    assert rows[-1] == {"meta": "dropped", "kind": "turn-review",
                        "why": "budget", "at": 30.0}
    # ⛔ **落ちた行に `session` を載せない。** 予算も冷却もセッションをまたいで
    #    1つであり、載せれば載る行と載らない行が生まれる（`room.py`）。
    assert "session" not in rows[-1]


def test_a_stale_candidate_is_dropped_as_expired_before_the_budget_is_asked():
    rows: list[dict] = []
    room = MetaRoom(emit=rows.append)
    drive(room, "a", 0.0)
    room.observe("a", "UserPromptSubmit", 700.0)  # 600秒を越えている

    assert rows[-1] == {"meta": "dropped", "kind": "turn-review",
                        "why": "expired", "at": 700.0}


def test_the_cooldown_drops_a_second_one_even_when_the_budget_is_free():
    """⚠️ **予算（15分）が空いていても、冷却（30分）は明ける前がある。**

    10 → 1500 は予算の外であり、turn-review の冷却の内側である。
    """
    rows: list[dict] = []
    room = MetaRoom(emit=rows.append)
    drive(room, "a", 0.0)
    room.observe("a", "UserPromptSubmit", 10.0)

    drive(room, "b", 1000.0)
    room.observe("b", "UserPromptSubmit", 1500.0)

    assert rows[-1] == {"meta": "dropped", "kind": "turn-review",
                        "why": "cooldown", "at": 1500.0}


def test_a_higher_candidate_supersedes_a_lower_one_in_the_same_turn():
    """⚠️ **`superseded` は損失ではない。** 競合した回数であり、勝った候補が
    後で配送されることもある——⇒ **4つの `why` を足しても、候補の総数にならない。**
    """
    rows: list[dict] = []
    room = MetaRoom(emit=rows.append)
    room.observe("m", "UserPromptSubmit", 0.0)
    room.observe("m", "PreCompact", 1.0)          # context-pressure（順位1）
    room.observe("m", "PostToolUseFailure", 2.0)
    room.observe("m", "PostToolUseFailure", 3.0)  # failure-loop（順位0）が勝つ

    # ⚠️ **規則が鳴いたことは、枠が取ったかどうかと別である**——⇒ `candidate` は
    #    勝っても負けても1行であり、`dropped` がその後ろに来る。
    assert [(row["meta"], row["kind"]) for row in rows] == [
        ("candidate", "context-pressure"),
        ("candidate", "failure-loop"),
        ("dropped", "context-pressure"),
    ]
    assert rows[-1]["why"] == "superseded"


# ---------------------------------------------------------------------------
# ダイヤル
# ---------------------------------------------------------------------------


def test_eager_changes_no_row_in_this_phase():
    """⛔ **`eager` の効き目は、まだどの行にも無い。**

    `eager` は `failure-loop` の強さを `high` にするが（§6）、**強さは行に載らない**
    ——行に載るのは種と数だけである（§10.6）。⇒ **効き目は Phase 4 の `Stop` の
    配送で初めて見える。** ⚠️ **ここで「何も変わらない」を検査しておく**ので、
    行の形に強さが紛れ込んだ日に、この検査が鳴る。
    """
    def run(eager: bool) -> list[dict]:
        rows: list[dict] = []
        room = MetaRoom(eager=eager, emit=rows.append)
        room.observe("m", "UserPromptSubmit", 0.0)
        room.observe("m", "PostToolUseFailure", 1.0)
        room.observe("m", "PostToolUseFailure", 2.0)
        return rows

    assert run(True) == run(False)


# ---------------------------------------------------------------------------
# 自由文は無い
# ---------------------------------------------------------------------------


def test_no_row_carries_free_text():
    """⛔ **行の鍵は最小限であり、値は閉じている**（§10.6、§14）。

    ここで確かめるのは**形**である——文字列の値が、種と窓と理由の語だけであること。
    """
    rows: list[dict] = []
    room = MetaRoom(emit=rows.append)
    room.observe("m", "UserPromptSubmit", 0.0)
    room.observe("m", "PreCompact", 1.0)
    room.observe("m", "PostToolUseFailure", 2.0)
    room.observe("m", "PostToolUseFailure", 3.0)
    room.observe("m", "Stop", 4.0)
    room.observe("m", "UserPromptSubmit", 5.0)

    assert rows, "行が1つも出ていない——この検査は何も見ていない"
    for row in rows:
        assert set(row) <= {"meta", "kind", "session", "why", "at", "error"}
        for key, value in row.items():
            if key in ("at",):
                assert isinstance(value, (int, float))
            elif key == "session":
                assert value == "m"
            else:
                assert isinstance(value, str) and " " not in value
        # ⚠️ **JSON にできること**も確かめる——1行として、そのままログへ行く。
        json.dumps(row)
