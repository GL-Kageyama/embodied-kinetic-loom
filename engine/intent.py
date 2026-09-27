# -*- coding: utf-8 -*-
"""`Motion Intent`——**境界の型を読み込む。**

⛔ **この型が境界である**（D-06）。**上流は自由で、下流は関数である。**
上流（セッションの中の Claude）は何を書いてもよい——**ただし、この型に正規化されてから入る。**
同 §1.2.1 の3つの決め手のうち、**1つ目がこれを決めた**: `semantic-visual-loom` は
**LLM を1回も呼ばずに、型のある中間表現を Claude に書かせ、決定論的なコードで読む。**
**このリポジトリはその双子である。**

⛔ **そして、開いた欄はここで落ちる。**
`schema` は `quality` を**通す**（書ける）。だが `Move` は**それを持たない**——
**読み手が無いからである。** 「[08_語彙と日本語] の語→値写像」がまだ無いので、
**この欄に何を書いても、誰も読まない。**
⇒ **欄を閉じない**（閉じれば書けなくなる）**が、読まない**（読めば、決まっていないことを決めたことになる）。
⇒ **この境界は、`tests/test_intent.py` が両側から押さえている。**

⚠️ **段の順は「型が先、語彙が後」である。**
[03_境界の型] §2.1 の8項目のうち、**語彙に依存するのは #4（質）だけ**であり、
**それは未決のまま開いてある。** だから型は先に閉じられる——
**衝突は消していない。住所を与えただけである**（`quality` という1つの欄に）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Move", "Intent", "IntentError", "load", "SCHEMA_PATH"]

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "motion-intent.schema.json"


class IntentError(ValueError):
    """意図が読めない。**黙って既定値で埋めない。**"""


@dataclass(frozen=True)
class Move:
    """1つの自由度を、1つの目標へ、1つの時間で動かす。

    ⛔ **`quality` は、ここに無い。** 理由はモジュールの docstring にある。
    ⚠️ **`dof` は名札である。モーターの番号ではない**（`plan.py` を見よ）。
    """

    dof: str
    target: float
    duration_ms: int
    group: int


@dataclass(frozen=True)
class Intent:
    """動作の列。**同じ `group` の move は、同時に動く。**"""

    moves: tuple[Move, ...]

    def groups(self) -> tuple[tuple[Move, ...], ...]:
        """同時に動く組を、送る順に返す。**空の組は作らない。**"""
        out: list[tuple[Move, ...]] = []
        for move in self.moves:
            if out and out[-1][0].group == move.group:
                out[-1] = out[-1] + (move,)
            else:
                out.append((move,))
        return tuple(out)


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load(obj) -> Intent:
    """辞書を検める。**通らなければ `IntentError`。**

    ⚠️ **`jsonschema` が要る**（`requirements.txt`）。**中核の計算には要らない**——
    純粋な算術だけである（`plan.py`）。
    """
    import jsonschema  # ⚠️ ここで import する。**中核を依存から遠ざけるため。**

    try:
        jsonschema.validate(obj, _schema())
    except jsonschema.ValidationError as exc:
        raise IntentError(f"型に合わない: {exc.message}（場所: {list(exc.absolute_path)}）") from exc

    moves = tuple(
        Move(dof=m["dof"], target=float(m["target"]),
             duration_ms=int(m["duration_ms"]), group=int(m["group"]))
        for m in obj["moves"]
    )
    if not moves:
        raise IntentError("move が1つも無い")

    # ---- 型では書けない2つ。⛔ ここを飛ばすと、意味の壊れた意図が通る。 ----
    groups = Intent(moves).groups()
    seen = [g[0].group for g in groups]
    if seen != list(range(len(seen))):
        # ⛔ **昇順と一意だけでは足りない。** `[0, 2]` は両方を満たす。
        # **番号が飛べば、その間に「送られない組」があることになる。**
        raise IntentError(f"group が 0 から連番でない: {seen}")
    for group in groups:
        durations = {m.duration_ms for m in group}
        if len(durations) != 1:
            raise IntentError(
                f"group {group[0].group} の中で時間が食い違う: {sorted(durations)}"
                "——**同時に動くものは、同じ時間で終わらなければならない**"
            )
    return Intent(moves)
