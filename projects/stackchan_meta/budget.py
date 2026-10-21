# -*- coding: utf-8 -*-
"""**声の間隔を決める —— 枠・予算・失効・冷却。** 時計は読まない（`at` は値で来る）。

⛔ **候補の枠はセッションごとに1つ、予算と冷却は全体で1つである。**
全体で1つの枠にすると、窓が別のセッションへ移ったとき、**前のセッションの候補が
新しいセッションの文脈へ渡る**（実測: live 2件・11h 1件・27h 0件）。
⇒ **宛先の違う一言は、届かなかったのと同じではない——間違って届いたのである。**

⚠️ **予算と冷却が全体で1つなのは、声がひとつしかないからである。**
候補はセッションごとに住むが、**口は1つである。**

⚠️ **失効（10分）が予算（15分）より短いのは意図である。** 10分前の指摘は、
10分後の文脈ではない。

⛔ **`superseded` は損失ではない。** 競合した回数であり、勝った候補が後で
配送されることもある。⇒ **落ちた4つの理由を足しても、候補の総数にはならない。**
"""
from __future__ import annotations

from dataclasses import dataclass

from .candidates import Candidate

#: ⚠️ **小さいほど強い。** 実測で決めた順である——`failure-loop` を先頭に置くと、
#: 配送が 1 → 4 に増えた（§19.3）。
PRIORITY: dict[str, int] = {
    "failure-loop": 0,
    "context-pressure": 1,
    "turn-review": 2,
}

#: **15分に1件。** ⚠️ **600秒との差は live で1件・27h で1件・11h で0件**——
#: 声の頻度を落とす側に倒した（§5）。
BUDGET_SECONDS = 900.0

#: **10分で失効する。**
TTL_SECONDS = 600.0

#: ⚠️ **語ごとの冷却である。** 同じ種類の一言を、短い間に二度言わない。
COOLDOWN_SECONDS: dict[str, float] = {
    "failure-loop": 600.0,
    "context-pressure": 3600.0,
    "turn-review": 1800.0,
}

#: ⛔ **落ちた理由の語彙である。** 自由文を入れない（§10.6）。
WHY: tuple[str, ...] = ("budget", "cooldown", "expired", "superseded")


@dataclass(frozen=True)
class Drop:
    """**落ちた1件。** ⚠️ **どの語が、なぜ落ちたかだけである。**"""

    kind: str
    why: str

    def __post_init__(self) -> None:
        if self.why not in WHY:
            raise ValueError(f"落ちた理由の語彙に無い: {self.why!r}")

    def as_dict(self, at: float) -> dict:
        """**ログの1行**（§10.6）。⚠️ **`at` はここで初めて値になる。**"""
        return {"meta": "dropped", "kind": self.kind, "why": self.why, "at": at}


@dataclass(frozen=True)
class Pending:
    """**枠の中の1件。** 生まれた時刻と、持ち主を覚える。"""

    candidate: Candidate
    born: float
    owner: str


class Budget:
    """**枠と、声の間隔。** ⚠️ **候補を作らない。作られた候補を置くだけである。**"""

    def __init__(
        self,
        budget: float = BUDGET_SECONDS,
        ttl: float = TTL_SECONDS,
        cooldown: dict[str, float] | None = None,
    ) -> None:
        self.budget = float(budget)
        self.ttl = float(ttl)
        self.cooldown = dict(COOLDOWN_SECONDS if cooldown is None else cooldown)
        #: ⚠️ **セッションごとの枠である。**
        self.slots: dict[str, Pending] = {}
        #: ⚠️ **最後に声を出した時刻。全体で1つである。**
        self.last_delivery: float | None = None
        #: ⚠️ **語ごとの最後の配送。全体で1つである。**
        self.last_kind: dict[str, float] = {}

    def offer(self, candidate: Candidate, session: str, at: float) -> Drop | None:
        """**枠へ置く。** 埋まっていれば、強いほうが残る。

        ⚠️ **置き換えたときも、置き換えられたときも `superseded` である**——
        競合した事実は同じであり、**どちらが勝ったかは `kind` が見分ける**
        （落ちた語の `kind` を返す）。
        """
        cur = self.slots.get(session)
        if cur is None:
            self.slots[session] = Pending(candidate, float(at), session)
            return None
        if PRIORITY[candidate.kind] < PRIORITY[cur.candidate.kind]:
            self.slots[session] = Pending(candidate, float(at), session)
            return Drop(kind=cur.candidate.kind, why="superseded")
        return Drop(kind=candidate.kind, why="superseded")

    def prompt(
        self, session: str, at: float
    ) -> tuple[Candidate | None, Drop | None]:
        """**`UserPromptSubmit` の瞬間。** 渡すか、落として理由を返す。

        ⚠️ **渡したら消える**（at-most-once）。確認応答は無い——
        **届かなければ、それは捨てられたのである**（§12.3）。
        """
        at = float(at)
        cur = self.slots.pop(session, None)
        if cur is None:
            return None, None
        kind = cur.candidate.kind
        if at - cur.born > self.ttl:
            return None, Drop(kind, "expired")
        if self.last_delivery is not None and at - self.last_delivery < self.budget:
            return None, Drop(kind, "budget")
        last = self.last_kind.get(kind)
        if last is not None and at - last < self.cooldown.get(kind, 0.0):
            return None, Drop(kind, "cooldown")
        self.last_delivery = at
        self.last_kind[kind] = at
        return cur.candidate, None

    def pending(self, session: str) -> Candidate | None:
        """**枠の中身。** ⚠️ **読むだけであり、消さない。**"""
        cur = self.slots.get(session)
        return None if cur is None else cur.candidate


__all__ = [
    "PRIORITY",
    "BUDGET_SECONDS",
    "TTL_SECONDS",
    "COOLDOWN_SECONDS",
    "WHY",
    "Drop",
    "Pending",
    "Budget",
]
