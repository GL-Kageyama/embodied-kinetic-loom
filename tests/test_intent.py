# -*- coding: utf-8 -*-
"""**境界の型を、両側から押さえる。**

⛔ このファイルの中心は `test_the_open_field_is_accepted_and_ignored` である。
D-06（型が境界）と [08_語彙と日本語]（語→値写像）の衝突は、**消していない。**
`quality` という**1つの欄に住所を与えた**——
**型はそれを通し、コードはそれを読まない。**
⇒ **片側だけを押さえたら、境界は崩れる。**
"""
from __future__ import annotations

import json

import pytest

from engine.intent import SCHEMA_PATH, Intent, IntentError, load


def _move(**kw):
    base = {"dof": "pitch", "target": 512, "duration_ms": 800, "group": 0}
    base.update(kw)
    return base


def _intent(*moves):
    return {"moves": list(moves)}


# --------------------------------------------------------------------------
# 通る
# --------------------------------------------------------------------------


def test_a_minimal_intent_loads():
    intent = load(_intent(_move()))
    assert isinstance(intent, Intent)
    assert intent.moves[0].dof == "pitch"
    assert intent.moves[0].target == 512.0
    assert intent.moves[0].duration_ms == 800


def test_groups_are_returned_in_order():
    intent = load(_intent(
        _move(group=0), _move(dof="roll", group=0), _move(dof="yaw", group=1),
    ))
    groups = intent.groups()
    assert len(groups) == 2
    assert [m.dof for m in groups[0]] == ["pitch", "roll"]
    assert [m.dof for m in groups[1]] == ["yaw"]


# --------------------------------------------------------------------------
# ⛔ 開いた欄——**両側から**
# --------------------------------------------------------------------------


def test_the_open_field_is_accepted_and_ignored():
    """⛔ **型は通し、コードは読まない。** 片方だけなら境界は崩れる。

    ⚠️ **[08_語彙と日本語] の写像が閉じた日、この検査は書き換わる。**
    そのときは「読む」側の検査が1本足される——**この検査を消すのではなく。**
    """
    loaded = load(_intent(_move(quality={"effort": "sudden", "weight": "light"})))
    move = loaded.moves[0]

    assert not hasattr(move, "quality"), "開いた欄を、コードが持ち始めている"
    assert "quality" not in {f for f in move.__dataclass_fields__}


def test_the_open_field_accepts_any_object():
    """⚠️ **値の型が決まっていないのだから、中身を縛れない。**"""
    for value in ({}, {"a": 1}, {"nested": {"deep": [1, 2, 3]}}):
        assert load(_intent(_move(quality=value))).moves[0].dof == "pitch"


def test_the_open_field_still_has_to_be_an_object():
    """⚠️ **開いているのは「値の型」であって「何でもよい」ではない。**"""
    for bad in ("sudden", 3, [1, 2], None):
        with pytest.raises(IntentError):
            load(_intent(_move(quality=bad)))


def test_the_schema_is_closed_everywhere_except_that_one_field():
    """⚠️ **閉じていることを、スキーマ自身から数える。**

    `additionalProperties: false` が、オブジェクトの在る2箇所にあること。
    そして `quality` だけが `additionalProperties` を持たないこと。
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    move = schema["$defs"]["move"]
    assert move["additionalProperties"] is False

    open_fields = [k for k, v in move["properties"].items() if "additionalProperties" not in v
                   and v.get("type") == "object"]
    assert open_fields == ["quality"], f"開いている欄が1つでない: {open_fields}"


# --------------------------------------------------------------------------
# ⛔ 通らない
# --------------------------------------------------------------------------


def test_an_unknown_key_is_refused():
    """**閉じてあるので、知らない欄は落ちる。**"""
    with pytest.raises(IntentError):
        load({"moves": [_move()], "speed": "fast"})
    with pytest.raises(IntentError):
        load(_intent(_move(tempo=1.0)))


def test_a_missing_required_field_is_refused():
    for key in ("dof", "target", "duration_ms", "group"):
        m = _move()
        del m[key]
        with pytest.raises(IntentError):
            load(_intent(m))


def test_a_degree_of_freedom_outside_the_three_is_refused():
    """⚠️ **この3つは我々の名前である。** 機械の側に対応表は無い（`plan.py` を見よ）。"""
    with pytest.raises(IntentError):
        load(_intent(_move(dof="heave")))


def test_the_range_is_NOT_in_the_type():
    """⛔ **`target` に範囲を書かない。** 枠は `Envelope` が持ち、型は持たない。

    ⚠️ **同じ数を2箇所に持つと、食い違う。**（[02_調査/05] §6 の作法）
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    target = schema["$defs"]["move"]["properties"]["target"]
    assert "minimum" not in target and "maximum" not in target
    # 型は 900 を通す（弾くのは関門の仕事である）
    assert load(_intent(_move(target=900))).moves[0].target == 900.0


def test_group_order_is_checked_in_code():
    """⚠️ **JSON Schema が言えないことを、コードが言う。**"""
    with pytest.raises(IntentError):
        load(_intent(_move(group=1), _move(dof="roll", group=0)))


def test_groups_must_be_contiguous():
    with pytest.raises(IntentError):
        load(_intent(_move(group=0), _move(dof="roll", group=2)))


def test_moves_in_one_group_must_share_a_duration():
    """**同時に動くものは、同じ時間で終わらなければならない。**"""
    with pytest.raises(IntentError):
        load(_intent(_move(group=0), _move(dof="roll", group=0, duration_ms=900)))


def test_an_empty_intent_is_refused():
    with pytest.raises(IntentError):
        load({"moves": []})
