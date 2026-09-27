# -*- coding: utf-8 -*-
"""**`projects/` の決定論を、`engine/` と同じ一覧で押さえる。**

⛔ **なぜこれが要るのか。** `tests/test_purity.py` が AST で歩くのは `engine/**` だけである。
**決定 C（Pet は `projects/` の下に住む、2026-09-28）は、その外側にコードを置いた**——
**そして著者に示した代価の逐語は「`projects/` の決定論は、誰も検査していない」であった。**
⇒ **このファイルは、その代価を1つ減らす。**

⚠️ **それでも代価はゼロにならない。** ここで見ているのは **import だけ**である。
**`engine/` に対する保証と同じ強さのものを、`projects/` が持つわけではない。**

⛔ **`projects/pet/__main__.py` を、名指しで除く。**
**このリポジトリで `time` を import してよい唯一の場所だからである**——
`engine/` は時計を呼ぶ側から受け取る。**その「呼ぶ側」が入口である。**
⚠️ **除いたことは、下の検査に書いてある。** **黙って除くと、走査した範囲が主張とずれる。**
"""
from __future__ import annotations

import pathlib

from tools.purity import scan

PROJECTS = pathlib.Path(__file__).resolve().parent.parent / "projects"

#: ⛔ **除くもの。理由はモジュールの docstring に在る。**
SKIP = frozenset({"projects/pet/__main__.py"})


def test_projects_imports_nothing_forbidden():
    files = sorted(PROJECTS.rglob("*.py"))
    assert files, "projects/ に .py が1つも無い——検査が空を回っている"

    found = scan(PROJECTS, skip=SKIP)
    assert not found, "決定論を壊す輸入がある:\n" + "\n".join(found)


def test_the_skip_list_names_a_file_that_exists():
    """⛔ **除いたファイルが消えたら、この検査は空を1つ多く回していることになる。**"""
    for rel in SKIP:
        assert (PROJECTS.parent / rel).exists(), f"除いたファイルが無い: {rel}"


def test_the_skip_list_is_the_whole_entry_point_and_nothing_else():
    """⚠️ **除いたのは入口だけである。** 図書館の側は1つも除いていない。"""
    skipped_at_pet_level = {rel for rel in SKIP if rel.startswith("projects/pet/")}
    assert skipped_at_pet_level == {"projects/pet/__main__.py"}

    scanned = {
        path.relative_to(PROJECTS.parent).as_posix()
        for path in PROJECTS.rglob("*.py")
    } - SKIP
    assert "projects/pet/screen.py" in scanned
    assert "projects/pet/expressions.py" in scanned
