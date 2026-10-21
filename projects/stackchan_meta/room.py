# -*- coding: utf-8 -*-
"""**監修の部屋 —— 事象1つを、記録1行と、返事の1行にする。**

⚠️ **純粋である。** 時計もソケットも読まない——時刻は値で受け取る。
⇒ **同じ事象の列と、同じ時刻の列を渡せば、同じ行と同じ返事が返る。**

⛔ **ここは「どこへ書くか」を知らない。** ログも標準出力も、この部屋の外である。
書き先は `emit` という**値**として渡る（渡さなければ、何も書かない）。
**この1つの関数が、縁から見た第3層の全部である**（設計 §7.2）。

## 順序

1. `UserPromptSubmit` なら、**先に口を開ける**——前のターンで作った候補が、
   このプロンプトに載る（§12.1）。**観るのはその後である。**
2. 事象を1つ食わせ、立った候補を**枠へ差し出す**（§12.3）。
3. 差し出した候補は `candidate` の行、枠が取った候補は `delivered` の行、
   落ちたものは `dropped` の行になる（§10.6）。

⚠️ **`dropped` の行に `session` を載せない。** 設計の行の形がそうであり、
**落ちた回数は、どの窓のものかを問わない**——予算も冷却もセッションをまたいで
1つだからである（§12.3）。⛔ **載せれば、載った行と載らない行が生まれる。**
"""
from __future__ import annotations

from typing import Callable

from .budget import Budget
from .render import render
from .trace import Trace
from .rules import observe as collect

#: ⚠️ **書き先は値である。** `None` なら何も書かない——**試験はこれで、行を溜める。**
Sink = Callable[[dict], None]


class MetaRoom:
    """**1つのトレースと、1つの口。** ⚠️ **体の `NextRoom` を包まない。**

    第3層は段階表も90秒も体の下限も知らない（§7.2）。知るのは事象・作業語・時刻だけである。
    ⇒ **糸が2本でも、共有する状態は1つも無い**——ロックも無い（§7.1）。

    ⚠️ **`eager` は `--meta eager` のときだけ真である**（§6）。そのとき
    `failure-loop` だけが `high` になり、`Stop` でも渡りうる（§12.2）。
    """

    def __init__(
        self,
        *,
        eager: bool = False,
        budget: Budget | None = None,
        emit: Sink | None = None,
    ) -> None:
        self._trace = Trace()
        self._budget = budget if budget is not None else Budget()
        self._eager = eager
        self._emit = emit

    def _row(self, payload: dict) -> None:
        # ⚠️ **行は、その場で渡す。** 溜めない——落ちたときに何も残らない
        #    （`daemon/__main__.emit` と同じ理由である）。
        if self._emit is not None:
            self._emit(payload)

    def observe(self, session: str, event: str, at: float,
                work: str | None = None) -> str | None:
        """**事象を1つ。返すのは、このプロンプトに載せる1文か `None` である。**

        ⚠️ **返事は候補そのものではない。** 候補は語と数しか持たず（§11.2）、
        文にするのは `render` の1か所だけである（§11.3）。
        ⛔ **ここで文を綴らない**——綴れば、テンプレートが2か所に住む。
        """
        says: str | None = None

        if event == "UserPromptSubmit":
            # ⚠️ **先に配る。** 前のターンの候補が、このプロンプトに載る。
            candidate, drop = self._budget.prompt(session, at)
            if drop is not None:
                self._row(drop.as_dict(at))
            if candidate is not None:
                self._row({"meta": "delivered", "kind": candidate.kind,
                           "session": session, "at": at})
                says = render(candidate)

        # ⚠️ **「事象は数えたが規則は当てない」を分けられる形のまま呼ぶ**
        #    （`rules.observe` の註）。ここではその1つだけを呼ぶ。
        for candidate in collect(self._trace, session, event, at, work,
                                 eager=self._eager):
            # ⚠️ **規則が鳴いたことは、枠が取ったかどうかと別である。**
            #    ⇒ **`candidate` は必ず1行**——「作ったが渡らなかった」を
            #    数えられるようにするためである（§10.6）。
            self._row({"meta": "candidate", "kind": candidate.kind,
                       "session": session, "at": at})
            drop = self._budget.offer(candidate, session, at)
            if drop is not None:
                # ⚠️ **`superseded` は2つの向きを持つ。** 新しい候補が古い候補を
                #    追い出した場合と、新しい候補が負けた場合である——どちらも
                #    `drop.kind` がどちらの候補かを言う。
                self._row(drop.as_dict(at))
        return says


__all__ = ["MetaRoom", "Sink"]
