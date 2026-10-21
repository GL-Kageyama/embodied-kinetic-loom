# -*- coding: utf-8 -*-
"""**候補 —— 第3層が外へ出す唯一の型。** 数と、閉じた語だけを持つ。

⛔ **自由文の欄は無い。** `message` を持てば、分析器が言葉を書くことになり、
「規則だけで走る」という決定が壊れる（設計 §11.2）。**言葉は本体のものである**——
本体はユーザーの言語・直前の文脈・その日の調子を知っており、分析器は知らない。

⚠️ **`evidence` の欄は語ごとに閉じている。** 語を足すことは、この表に1行足し、
`render.py` に1行足すことである。⛔ **語を足さずに規則だけ足さない**
（設計 §16）——規則が語を持たなければ、鳴ったことが描けない。

⚠️ **`word` は `longest` と対である。** 25回に満たないターンに語を付ければ、
すべての振り返りが「3回続いてる」と言う（§11.1）。⇒ **ここで両方向に締める**——
`longest < LONG_AT` なら `word` は `None`、`longest >= LONG_AT` なら語が要る。
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from projects.stackchan_next.work import WORK_WORDS

#: **語彙である。** ⚠️ **閉じている。** ここに無い語は、鳴ることも描かれることも無い。
#: ⛔ `verification-gap` / `fan-out` / `probe-only` は**測って落とした**（§10.2）——
#: 語彙に無いことが、その決定の実体である。
KINDS: tuple[str, ...] = ("context-pressure", "turn-review", "failure-loop")

#: **語ごとの証拠の欄。** ⚠️ **数と、閉じた語だけである。**
EVIDENCE: dict[str, tuple[str, ...]] = {
    "context-pressure": ("compactions",),
    "turn-review": ("seconds", "tools", "longest", "word"),
    "failure-loop": ("failures",),
}

#: **強さの語。** ⚠️ **`high` を付けられるのは `failure-loop` だけである**（§12.2）。
PRIORITIES: tuple[str, ...] = ("low", "normal", "high")

#: ⚠️ **連続の話をする境目である。** `rules.META_STREAK` はこの数であり、
#: `render` もこの数を見る——**数は1つ、名前が2つである。**
LONG_AT = 25


@dataclass(frozen=True)
class Candidate:
    """**1件の候補。** 語・証拠・失効までの秒数・強さ。

    ⚠️ **`expires_after` に既定値を置かない。** 既定を置けば、`budget.py` の
    失効の数と、ここに書いた数が2か所になる——**片方が黙って緩んだ日に、
    もう片方が鳴らない。** 作る側（`rules.py`）が `budget.TTL_SECONDS` を渡す。
    """

    kind: str
    evidence: Mapping[str, object]
    expires_after: float
    priority: str = "normal"

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"語彙に無い語である: {self.kind!r}")
        if self.priority not in PRIORITIES:
            raise ValueError(f"強さの語彙に無い: {self.priority!r}")
        if isinstance(self.expires_after, bool) or not isinstance(
            self.expires_after, (int, float)
        ):
            raise TypeError(f"失効は数である: {self.expires_after!r}")
        if self.expires_after <= 0:
            raise ValueError(f"失効は正の数である: {self.expires_after!r}")

        if not isinstance(self.evidence, Mapping):
            raise TypeError(f"証拠は写像である: {self.evidence!r}")
        fields = EVIDENCE[self.kind]
        if set(self.evidence) != set(fields):
            raise ValueError(
                f"{self.kind} の証拠の欄は {fields} である: {tuple(self.evidence)}"
            )
        for name, value in self.evidence.items():
            if name == "word":
                if value is not None and value not in WORK_WORDS:
                    raise ValueError(f"word は6語か null である: {value!r}")
                continue
            # ⚠️ `True` は `int` である。**数として通してはならない。**
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} は整数である: {value!r}")
            if value < 0:
                raise ValueError(f"{name} は負にならない: {value!r}")

        if self.kind == "turn-review":
            # ⚠️ **両方向である。** 片方だけを締めると、残る側が空欄になる。
            if self.evidence["longest"] < LONG_AT and self.evidence["word"] is not None:
                raise ValueError("連続が25に満たないのに語が付いている")
            if self.evidence["longest"] >= LONG_AT and self.evidence["word"] is None:
                raise ValueError("連続が25以上なのに語が無い")

        object.__setattr__(self, "evidence", MappingProxyType(dict(self.evidence)))

    def as_dict(self) -> dict:
        """**外へ出す形。** ⚠️ **欄は4つである**（§11.1）。自由文は無い。"""
        return {
            "kind": self.kind,
            "evidence": dict(self.evidence),
            "priority": self.priority,
            "expires_after": self.expires_after,
        }


__all__ = [
    "KINDS",
    "EVIDENCE",
    "PRIORITIES",
    "LONG_AT",
    "Candidate",
]
