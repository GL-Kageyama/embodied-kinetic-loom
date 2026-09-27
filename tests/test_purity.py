# -*- coding: utf-8 -*-
"""**決定論を、静的に押さえる。**

`CLAUDE.md` の2文——「このリポジトリのコードは LLM を呼ばない」と
「同じ入力なら同じ出力」——は、**実行して比べるだけでは足りない**。
**比べた2回が、たまたま同じだったかもしれない。**
⇒ **輸入そのものを見る。** 乱数・時刻・環境・ネットワーク・LLM のクライアントを、
**`engine/` が import していないこと**を、AST で確かめる。

⚠️ **一覧と走査は `tools/purity.py` に在る**——**`projects/` も同じ一覧を使う**（2026-09-28）。
**2つ書けば、片方だけが直る。**

⚠️ **この一覧に足すことは、決定を1つ足すことである。** 気軽に足さない。
"""
from __future__ import annotations

import ast
import pathlib

from tools.purity import FORBIDDEN, imported, scan

ENGINE = pathlib.Path(__file__).resolve().parent.parent / "engine"


def test_engine_imports_nothing_forbidden():
    files = sorted(ENGINE.rglob("*.py"))
    assert files, "engine/ に .py が1つも無い——検査が空を回っている"

    found = scan(ENGINE)
    assert not found, "決定論を壊す輸入がある:\n" + "\n".join(found)


def test_the_forbidden_list_itself_fires():
    """⛔ **検査が鳴ることを、検査する。**（空の検査は OK と言う）"""
    tree = ast.parse("import random\nfrom time import sleep\nimport json")
    assert imported(tree) & FORBIDDEN.keys() == {"random", "time"}


def test_the_forbidden_list_does_not_fire_on_relative_imports():
    """⚠️ **`from .plan import plan` を、外部の `plan` と読み違えないこと。**"""
    tree = ast.parse("from .plan import plan\nfrom . import limits")
    assert imported(tree) & FORBIDDEN.keys() == set()
