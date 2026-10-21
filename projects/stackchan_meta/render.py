# -*- coding: utf-8 -*-
"""**描画 —— 候補を1行にする。** 表は語ごとに1つであり、検査できる。

⚠️ **言葉は本体のものである**（§11.2）。ここが作るのは英語の1行であり、
本体がユーザーの言語に直す。⛔ **テンプレート表は検査できるが、自由文は検査できない。**

⛔ **前置きは1か所に1つである。** 語ごとに instruction を書き分けると、
語を足すたびに指示が増え、**文体が割れる。**

⛔ **語彙外は描かない。** 黙って落とせば、語を足した日に「描かれていない」ことが
見えない——**規則が鳴っているのに声が出ない日を、誰も数えられない。**
"""
from __future__ import annotations

from .candidates import LONG_AT, Candidate

#: ⚠️ **1行であり、語ごとに1つ。** 数は `evidence` から入る。
LINES: dict[str, str] = {
    "context-pressure": (
        "the conversation was compacted {compactions}x during that turn; "
        "the earlier part is out of view"
    ),
    "turn-review": "that turn ran {seconds}s over {tools} tool calls",
    "failure-loop": "{failures} failures in a row in that turn",
}

#: ⚠️ **連続の話は、振り返りの1行の後半に付く。** 別の語ではない——
#: だから**別の一言にもならない**（§11.3）。
LONG_SUFFIX = ", {longest} of them '{word}' in a row"

#: ⛔ **1つだけである。** 本体への指示はここにしかない。
PRELUDE = (
    "[stack-chan meta] {line}. At most one sentence about it, in the user's "
    "language, and only if it still matters; otherwise say nothing."
)

#: ⚠️ **口が在るときだけ、後ろに1節が付く**（2026-10-21、§22.10）。⛔ **語ごとではない**
#: ——だから文体は割れない（§11.3 の規則はそのままである）。**節は丸ごと在るか、
#: 丸ごと無いか**であり、**半分だけの前置きは作らない。**
#: ⛔ **命令は縁が値を入れる**（`MetaRoom` の `mouth`）——**ここに絶対の道を書かない**。
#: 道は走っている場所のものであり、規則の層はこの機械の住所を知らない。
MOUTH = " To say it aloud, run: {mouth} '<your sentence>'"


def line(candidate: Candidate) -> str:
    """**候補を英語の1行にする。** ⚠️ **前置きは付けない。**

    ⛔ **語彙に無い語は `ValueError` である。** `Candidate` は語彙外を建てられないが、
    ここでも断る——**2つの門は、片方が緩んだ日に効く。**
    """
    kind = getattr(candidate, "kind", None)
    template = LINES.get(kind)
    if template is None:
        raise ValueError(f"語彙に無い候補は描かない: {kind!r}")
    text = template.format(**candidate.evidence)
    if kind == "turn-review":
        longest = candidate.evidence["longest"]
        word = candidate.evidence["word"]
        # ⚠️ **25回に満たなければ後半を付けない。** 付けば、すべての振り返りが
        # 「3回続いてる」と言う（§11.1）。
        if longest >= LONG_AT and word is not None:
            text += LONG_SUFFIX.format(longest=longest, word=word)
    return text


def render(candidate: Candidate, mouth: str | None = None) -> str:
    """**本体へ渡す文字列。** 1行と、1つの前置きである。

    ⚠️ **`mouth` は、口が開いているときだけ渡る。** 渡れば、前置きの後ろに
    **1節**が付く——**文を声にする道の命令である**（§22.10）。⛔ **渡らなければ
    付かない**：**開いていない口の命令は、失敗する道具の1行にしかならない。**
    """
    text = PRELUDE.format(line=line(candidate))
    if mouth is not None:
        text += MOUTH.format(mouth=mouth)
    return text


__all__ = ["LINES", "LONG_SUFFIX", "PRELUDE", "MOUTH", "line", "render"]
