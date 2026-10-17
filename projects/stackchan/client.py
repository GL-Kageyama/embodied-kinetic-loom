# -*- coding: utf-8 -*-
"""**フックの側の薄いクライアント。** 1事象につき1プロセスで走り、1行を送って消える。

⛔ **フックの入力には、プロンプトも道具の入力も入っている。** ここはそれを
「読まない」のではなく、**読んだ2つの欄だけを組み直す**——**同乗できないことが、
この層のプライバシーである**（`docs/stackchan-daemon.md`）。

⛔ **このファイルはソケットを開かない。** 開くのは隣の `hook/__main__.py` であり、
`tests/test_pet_purity.py` が入口（`__main__.py`）として名指しで除いている。
⇒ **組み直しは入力と出力の関数であり、プロセスを起こさずに検査できる。**

⚠️ **時刻は送らない。** 刻むのはデーモンである。
"""
from __future__ import annotations

import json

from projects.stackchan import hooks

#: ⚠️ **フックの入力のうち、外へ出るのはこの2つだけである。**
#: ⛔ **増やすことは、契約を増やすことである**（デーモン側の `REQUEST_KEYS` と対）。
SOURCE_FIELDS: tuple[str, str] = ("session_id", "hook_event_name")

#: ⚠️ **入力を読む上限。** プロンプトは捨てるが、**読む前にも大きさで切る。**
INPUT_LIMIT = 1 << 20


def line_from(payload: object) -> str | None:
    """**フックの入力を、送る1行に組み直す。** ⛔ **送れなければ `None` である。**

    - 辞書でない → `None`;
    - `session_id` か `hook_event_name` が、空でない文字列でない → `None`;
    - 33に無い事象の名前 → `None`（**デーモンへ送らない**——断りの山を作らない）。

    ⚠️ **知らない事象を落とすのは、ここが最後の門ではない。** デーモンも
    `parse_request` で同じ規則を持つ——**2つあるのは、片方が黙って緩んでも
    もう片方が鳴るためである。**
    """
    if not isinstance(payload, dict):
        return None

    session = payload.get(SOURCE_FIELDS[0])
    event = payload.get(SOURCE_FIELDS[1])
    if not isinstance(session, str) or not isinstance(event, str):
        return None
    if not session or not event:
        return None

    try:
        hooks.classify(event)
    except hooks.UnknownEvent:
        return None

    return json.dumps({"session": session, "event": event}, ensure_ascii=False) + "\n"


__all__ = ["SOURCE_FIELDS", "INPUT_LIMIT", "line_from"]
