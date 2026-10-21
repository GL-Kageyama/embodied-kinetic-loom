# -*- coding: utf-8 -*-
"""**第3層 —— メタ監修。** 事象を数え、規則で判定し、1行にする。

⛔ **この層は体を動かさない。** 光・顔・音・身振りに触れない（§12.4）。
**候補は `Decision` を1つも変えない**——変えれば、監修の有無で体が変わる。

⚠️ **第1層から読むのは `STEALS` という集合1つだけである**（§10.5）。
状態も判定も読まない。⛔ **規則が2か所に住めば、片方が黙って緩んだ日に、
もう片方が鳴らない。**

⚠️ **時計もファイルも読まない。** `at` は値で来る。⇒ **実ログを再生できる。**

5つの部品と、その口:

| 部品 | 何をするか |
|---|---|
| `trace` | 事象からターンと数を取り出す（窓・呼び出し・連続・失敗・圧縮） |
| `rules` | 3つの語が、閾値で鳴る |
| `candidates` | 閉じた語彙と、証拠の欄 |
| `render` | 候補を1行にする（前置きは1つ） |
| `budget` | 枠・予算・失効・冷却・優先度 |
| `room` | 上の5つを、縁から見た**1つの関数**にまとめる（`MetaRoom.observe`） |

⚠️ **`room` も純粋である。** 書き先は `emit` という値で渡り、時計は `at` で渡る——
⇒ **ソケットも糸も、この層の外に在る**（第2層のデーモン、Phase 3.5）。
"""
from __future__ import annotations

from .budget import (
    BUDGET_SECONDS,
    COOLDOWN_SECONDS,
    PRIORITY,
    TTL_SECONDS,
    Budget,
    Drop,
    Pending,
)
from .candidates import EVIDENCE, KINDS, LONG_AT, PRIORITIES, Candidate
from .render import PRELUDE, line, render
from .room import MetaRoom, Sink
from .rules import (
    META_FAILURES,
    META_STREAK,
    META_TURN_SECONDS,
    META_WIDE_TOOLS,
    RULES,
    evaluate,
    observe,
)
from .trace import CLOSES, Moment, Trace, Turn

__all__ = [
    "BUDGET_SECONDS",
    "COOLDOWN_SECONDS",
    "PRIORITY",
    "TTL_SECONDS",
    "Budget",
    "Drop",
    "Pending",
    "EVIDENCE",
    "KINDS",
    "LONG_AT",
    "PRIORITIES",
    "Candidate",
    "PRELUDE",
    "line",
    "render",
    "MetaRoom",
    "Sink",
    "META_FAILURES",
    "META_STREAK",
    "META_TURN_SECONDS",
    "META_WIDE_TOOLS",
    "RULES",
    "evaluate",
    "observe",
    "CLOSES",
    "Moment",
    "Trace",
    "Turn",
]
