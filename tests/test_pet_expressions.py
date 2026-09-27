# -*- coding: utf-8 -*-
"""**5つの顔を、決定 A の対象として押さえる。**

⛔ **このファイルは、「データがデータと等しい」ことを主張している。**
**それでも置くのは、この5つが決定 A（保って「猫」と名乗る）の対象そのものであり、
黙って変わることを許さないからである。**
⚠️ **出典は概念文書 §5。そして概念文書はリポジトリの外に在る**——
**ゆえに検査は、出典ではなく、ここに写した姿を守る。**
"""
from __future__ import annotations

import pytest

from projects.pet.expressions import BOX_HEIGHT, BOX_WIDTH, FACES, State

EARS = "  /\\_/\\"
FEET = "  > ^ <"

EXPECTED = {
    State.HAPPY: (EARS, " ( ^.^ )", FEET),
    State.SLEEPY: (EARS, " ( -.- )", "  > _ <", "    z"),
    State.ANGRY: (EARS, " ( >.< )", FEET),
    State.CURIOUS: (EARS, " ( o.o )", FEET),
    State.GREETING: (EARS, " ( ^.^ )", FEET),
}


@pytest.mark.parametrize("state", list(State))
def test_the_face_is_the_one_the_concept_document_draws(state):
    assert FACES[state] == EXPECTED[state]


def test_the_five_faces_are_five_and_the_state_names_are_the_documents():
    """⚠️ **値は概念文書 §4 の `PetResponse.state` の綴りである。**"""
    assert [state.value for state in State] == [
        "happy", "sleepy", "angry", "curious", "greeting",
    ]


def test_two_states_share_one_face():
    """⛔ **これは、この5つについての実測である。**

    **「うれしい」と「あいさつ」の顔は、1文字も違わない。**
    ⇒ **顔だけでは、この2つを区別できない。** 区別するのは運動である
    （概念文書 §5——うれしい＝small bounce、あいさつ＝small forward tilt）。
    ⇒ **ゆえに [06] §11-8（「顔と身体は必ず同時に一つの時計から出す」）は、
    様式の好みではなく、この図から出る要件である**——**身体を落とすと、
    この2つは同じものになる。**
    """
    assert FACES[State.HAPPY] == FACES[State.GREETING]

    distinct = {tuple(lines) for lines in FACES.values()}
    assert len(distinct) == 4, "5つの状態に、4つの顔しか無い"


def test_sleepy_is_the_only_face_with_a_fourth_line():
    with_four = [state for state, lines in FACES.items() if len(lines) == BOX_HEIGHT]
    assert with_four == [State.SLEEPY]


def test_no_face_has_a_line_wider_than_the_box():
    for state, lines in FACES.items():
        for line in lines:
            assert len(line) <= BOX_WIDTH, f"{state.value}: {line!r}"


def test_the_box_is_the_size_the_faces_actually_need():
    """⚠️ **箱が顔より大きいと、この2つの数は誰も検算しない定数になる。**"""
    assert max(len(line) for lines in FACES.values() for line in lines) == BOX_WIDTH
    assert max(len(lines) for lines in FACES.values()) == BOX_HEIGHT
