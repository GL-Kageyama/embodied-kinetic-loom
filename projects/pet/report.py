# -*- coding: utf-8 -*-
"""**何が起きたかを、1箇所に書く。** 緑を「成立した」と読ませないためである。

⛔ **このファイルは `__main__.py` から出てきた**（2026-09-28）。理由は2つある。

1. **`__main__.py` は検査から名指しで除かれている**（`tests/test_pet_purity.py`）。
   **そこに論理を置けば、その論理は走査の外に在る**——**除いた範囲は、狭い方がよい。**
2. **除かれたファイルは、試験からも遠い。** ここは純粋である——
   `time` も `os` も持たず、`Take` と表だけを受け取る。**ゆえに試験できる。**

⚠️ **文そのものは、ここには無い。** 雛形は `locales/` に在り、
引くのは `strings.py` である——**この層が持つのは、どの数を、どの穴に、どの順で入れるかである。**
"""
from __future__ import annotations

from . import strings
from .motion import Take

__all__ = ["report"]

#: ⚠️ **語を並べる記号。** 言語ではないので表には置かない——**3言語で同じものである。**
ARROW = " → "


def report(take: Take, name: str, lang: str | None = None) -> str:
    """**走らせた結果を、人間の文にする。**

    ⛔ **弾かれた場合は、1行目でそう言い切る。** 「送った 0 フレーム」と書けば、
    **成立した回と見分けが付かない**——**0 は緑に見える。**
    """
    if not take.ran:
        return strings.text(
            "pet_report", "refused", lang,
            name=name, reason=strings.refusal(take.refusal, lang),
        )

    lines = [
        strings.text("pet_report", "head", lang,
                     name=name, words=ARROW.join(take.expression.words)),
        strings.text("pet_report", "counts", lang,
                     frames=len(take.sent), ticks=len(take.ticks),
                     refusals=take.refusals, skipped=take.skipped),
        # ⚠️ **小数の桁は表が決める**（`{worst_ms:.3f}`）——**表示の作法も言語の一部である。**
        strings.text("pet_report", "lateness", lang,
                     worst_ms=take.worst_lateness * 1000.0),
        strings.text("pet_report", "position", lang,
                     arrived=tuple(round(v, 1) for v in take.arrived)),
        strings.text("pet_report", "caveat", lang),
    ]
    return "\n".join(lines)
