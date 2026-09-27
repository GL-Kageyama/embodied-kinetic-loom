# -*- coding: utf-8 -*-
"""**決定論を、静的に押さえる。**

`CLAUDE.md` の2文——「このリポジトリのコードは LLM を呼ばない」と
「同じ入力なら同じ出力」——は、**実行して比べるだけでは足りない**。
**比べた2回が、たまたま同じだったかもしれない。**
⇒ **輸入そのものを見る。** 乱数・時刻・環境・ネットワーク・LLM のクライアントを、
**`engine/` が import していないこと**を、AST で確かめる。

⚠️ **grep ではない。** 文字列で探すと、docstring の中の語に当たる
（`CLAUDE.md`「自分が今足した語を検索語にすると必ず当たる」）。
**AST なら、本物の import だけを見る。**

⚠️ **この一覧に足すことは、決定を1つ足すことである。** 気軽に足さない。
"""
from __future__ import annotations

import ast
import pathlib

#: ⛔ `engine/` が輸入してはならないもの。**分類してあるのは、理由が違うからである。**
FORBIDDEN = {
    # 決定論を壊す
    "random": "乱数", "secrets": "乱数", "time": "時刻", "datetime": "時刻",
    "uuid": "一意性", "os": "環境（environ）",
    # ファイルの外へ出る
    "socket": "ネットワーク", "subprocess": "プロセス", "urllib": "ネットワーク",
    "http": "ネットワーク", "requests": "ネットワーク",
    # LLM
    "anthropic": "LLM", "openai": "LLM", "llama_cpp": "LLM",
}

ENGINE = pathlib.Path(__file__).resolve().parent.parent / "engine"


def _imported(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def test_engine_imports_nothing_forbidden():
    files = sorted(ENGINE.rglob("*.py"))
    assert files, "engine/ に .py が1つも無い——検査が空を回っている"

    found = []
    for path in files:
        names = _imported(ast.parse(path.read_text(encoding="utf-8")))
        for name in sorted(names & FORBIDDEN.keys()):
            found.append(f"{path.relative_to(ENGINE.parent)}: {name}（{FORBIDDEN[name]}）")
    assert not found, "決定論を壊す輸入がある:\n" + "\n".join(found)


def test_the_forbidden_list_itself_fires():
    """⛔ **検査が鳴ることを、検査する。**（空の検査は OK と言う）"""
    tree = ast.parse("import random\nfrom time import sleep\nimport json")
    assert _imported(tree) & FORBIDDEN.keys() == {"random", "time"}


def test_the_forbidden_list_does_not_fire_on_relative_imports():
    """⚠️ **`from .plan import plan` を、外部の `plan` と読み違えないこと。**"""
    tree = ast.parse("from .plan import plan\nfrom . import limits")
    assert _imported(tree) & FORBIDDEN.keys() == set()
