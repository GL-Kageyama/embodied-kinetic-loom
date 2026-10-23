# -*- coding: utf-8 -*-
"""**この体が映せる顔は8語である。うち5語は Pet のもので、3語はこの機体のものである。**

⛔ **`projects/pet/expressions.py` の `State` は増やさない。** あの5つは概念文書 §5 から
逐語で写した図であり、**増やせば「写した」が偽になる**。この体は Pet ではない——
画面に映るのは同じ5つの名前を借りた図と、**この機体が自分の仕事のために足した3語**である。

| 語 | 出どころ | いつ出るか |
|---|---|---|
| `curious` `greeting` `happy` `angry` `sleepy` | Pet の5つ（名前だけ借りる） | 段階が決める（第1層） |
| `focused` | この機体 | `write` のあいだ（第2層） |
| `watching` | この機体 | `run` のあいだ（第2層） |
| `startled` | この機体 | 1回の失敗の2秒（第2層） |

⚠️ **語は意味に対して付けた。形に対してではない。** 形は目の判定で変わるが、
**語は変わらない**——だからログを後から数えても意味が残る。

⚠️ **5つの語はここで綴り直していない。** `Face.CURIOUS` の値は `State.CURIOUS.value`
そのものである——**写しを1つ減らすためであり、`Face` を Pet の上に載せるため**である。
⇒ **`Face` の先頭5つが `State` と食い違うことは、構造上ありえない。**
⛔ **食い違えるのは綴りではなく、電線の写しのほうである**（`engine/backend/protocol_stackchan.py`）。
それは `tests/test_stackchan_wire.py` が3つとも突き合わせる。
"""
from __future__ import annotations

from enum import Enum

from projects.pet.expressions import FACES as PET_ART
from projects.pet.expressions import State

__all__ = ["Face", "FACES", "PET_FACES", "art"]


class Face(str, Enum):
    """⚠️ **8語。** 値は電線に載る綴りそのものである（`str` を継承するのはそのため）。"""

    # ——— Pet の5つ。⛔ 値はここで書かず、Pet から取る。
    CURIOUS = State.CURIOUS.value
    GREETING = State.GREETING.value
    HAPPY = State.HAPPY.value
    ANGRY = State.ANGRY.value
    SLEEPY = State.SLEEPY.value

    # ——— この機体の3つ（2026-10-24）。⚠️ 形は `face_bitmap.cpp` が持ち、
    #     どれがどれに見えるかは著者の目が決める。ここにあるのは語だけである。
    FOCUSED = "focused"
    WATCHING = "watching"
    STARTLED = "startled"


#: **Pet から借りた5つ。** ⛔ この並びは `State` の並びと同じであり、
#: `tests/test_stackchan_faces.py` がそれを突き合わせる。
PET_FACES: tuple[Face, ...] = (
    Face.CURIOUS,
    Face.GREETING,
    Face.HAPPY,
    Face.ANGRY,
    Face.SLEEPY,
)

#: 8語すべて。⚠️ 電線の `FACES` と食い違った日に赤くなるのは
#: `tests/test_stackchan_wire.py` であり、**この一覧はその検査の一方の端である**。
FACES: tuple[Face, ...] = tuple(Face)


def art(face: Face) -> tuple[str, ...]:
    """**Pet の5つなら、その図の行を返す。この機体の3つなら、空を返す。**

    ⛔ **この3つに ASCII の図は無い。** 図はファームの `face_bitmap.cpp` にあり、
    C++ であって、ここから読めるものではない。**空を返すのは、無いからである**——
    行はすでに語を持っているので、図の代わりに何かを発明する必要はない。
    """
    if face in PET_FACES:
        return PET_ART[State(face.value)]
    return ()
