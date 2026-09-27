# -*- coding: utf-8 -*-
"""**決定論を、静的に押さえるための一覧と走査。**

⛔ **このモジュールは、2つの場所から使われる**——`engine/` と `projects/`。
**一覧を2つ書くと、片方だけが直る。** ゆえに一覧はここに1つだけ置く。

⚠️ **`import` を AST で見る。grep ではない。** 文字列で探すと、docstring の中の語に当たる
（`CLAUDE.md`「自分が今足した語を検索語にすると必ず当たる」）。
**AST なら、本物の import だけを見る。**

⚠️ **この一覧に足すことは、決定を1つ足すことである。** 気軽に足さない。
"""
from __future__ import annotations

import ast
import pathlib

__all__ = ["FORBIDDEN", "imported", "scan"]

#: ⛔ **禁じられた輸入。** **分類してあるのは、理由が違うからである。**
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


def imported(tree: ast.AST) -> set[str]:
    """⚠️ **相対輸入を、外部の名前と読み違えないこと**（`from .plan import plan`）。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def scan(root: pathlib.Path, *, skip: frozenset[str] = frozenset()) -> list[str]:
    """⛔ **`root` の下の `.py` を歩き、禁じられた輸入を「相対パス: 名前（理由）」で返す。**

    ⚠️ **`skip` は相対パスである。** **除いたことは、呼ぶ側の検査に書くこと**——
    **黙って除くと、走査した範囲が主張とずれる**（[[measured-scope-vs-claimed-scope]]）。
    """
    found = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root.parent).as_posix()
        if rel in skip:
            continue
        names = imported(ast.parse(path.read_text(encoding="utf-8")))
        for name in sorted(names & FORBIDDEN.keys()):
            found.append(f"{rel}: {name}（{FORBIDDEN[name]}）")
    return found
