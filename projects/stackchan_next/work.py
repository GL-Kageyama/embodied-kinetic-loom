# -*- coding: utf-8 -*-
"""**何をしているか。** 道具の名前を、閉じた6語のどれか1つに落とす。

## なぜ要るか

⚠️ **フックが運ぶのは `{session, event}` の2語だけだった**（`projects/stackchan/client.py`）。
⇒ **読んでいるのか、書いているのか、走らせているのかが、機械に届かない。**
`working` は一日の3分の1を占めるのに、その中身は1種類である——
**測った**: 25時間18分で決定 9,168、うち `working` が 32.9%、
そのあいだ機械が出すのは `light: dim` と変わらない1つの顔だけだった。

## 何を読むか

⛔ **読むのは `tool_name` だけである。** `tool_input`（ファイルパス）、`prompt`、
`cwd`、`tool_response` は**構造的に通らない**——この表は名前だけを受け取る関数であり、
**名前以外を引数に取る口が無い**。プライバシーは約束ではなく、**関数の形**である。

⚠️ **表に無い名前は `other` である。** 落とさない——
**知らない道具を使っていることも、作業の1つの形である。**

⛔ **ここに在るのは語だけであり、数は1つも無い。** 語から光への対応は
`presence.py` に、語から色への対応はファームウェアに在る。
"""
from __future__ import annotations

#: ⚠️ **閉じた集合である。** 増やすことは、フックの契約を増やすことである
#: （`client.py` と、デーモンの `REQUEST_KEYS` と対）。
WORK_WORDS: tuple[str, ...] = ("read", "write", "run", "search", "plan", "other")

#: ⚠️ **表に無い名前の行き先である。** 「無い」ではなく「その他」である。
OTHER = "other"

#: ⚠️ **道具の名前から語への写像である。** 名前は Claude Code のものであり、
#: この機体のものではない——**だから表はここに1つだけ置く。**
TOOLS: dict[str, str] = {
    "Read": "read",
    "Glob": "read",
    "Grep": "read",
    "LS": "read",
    "Edit": "write",
    "Write": "write",
    "MultiEdit": "write",
    "NotebookEdit": "write",
    "Bash": "run",
    "BashOutput": "run",
    "KillShell": "run",
    "WebSearch": "search",
    "WebFetch": "search",
    "Task": "plan",
    "TodoWrite": "plan",
    "EnterPlanMode": "plan",
    "ExitPlanMode": "plan",
}

#: ⚠️ **作業の語を運ぶ事象である。** 遷移と失敗は作業ではない——
#: **遷移は章であり、失敗は光で言う**（`presence.py` の点滅）。
#: ⛔ **この2つ以外は `work` を載せない。** 載せれば、語の意味が薄まる。
WORK_EVENTS: frozenset[str] = frozenset({"PreToolUse", "PostToolUse"})


def word_for(tool_name: object) -> str:
    """**道具の名前を、6語のどれか1つに落とす。**

    ⚠️ **知らない名前・文字列でない値は、どちらも `other` である。**
    辞書を引く前に型を見るのは、**`None` や数が `TOOLS` に当たらないから**であり、
    **断るためではない**——落とすのは `client.py` の仕事である。
    """
    if not isinstance(tool_name, str):
        return OTHER
    return TOOLS.get(tool_name, OTHER)


def carries_work(event: str) -> bool:
    """**その事象が作業の語を運ぶか。**"""
    return event in WORK_EVENTS


__all__ = [
    "WORK_WORDS",
    "OTHER",
    "TOOLS",
    "WORK_EVENTS",
    "word_for",
    "carries_work",
]
