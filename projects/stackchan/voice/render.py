# -*- coding: utf-8 -*-
"""**声の間。** 「。」と「、」のあとに置く無音の長さを、1か所で決める。

⚠️ **著者の裁定（2026-10-21）である。** 2案を鳴らして選ばれた——
句点 400 ms・読点 200 ms と、**句点 600 ms・読点 300 ms** のうち**後者**。
⛔ **数はこの表にしか無い。** 断片を焼く道具も、都度合成する縁も、ここを読む。

## なぜ、記号に付けるのか

⛔ **`say` の句読点は、間を約束しない。** 声は同じでも、文が長いほど詰まる。
⇒ **間を「文の性質」ではなく「記号の性質」として置く**——そうすれば、
**文が変わっても間は変わらない**（[[design-names-function-not-wording]] の裏返しである）。

⚠️ **「!」「?」には数を置かない。** 著者の言葉は「言葉の切れ目（。、）」であり、
**嘆きの強さをミリ秒で決める根拠は無い**——`say` 自身の抑揚に任せる。

## 端の扱い

⛔ **文末の記号には無音を足さない。** 最後の「。」のあとに 600 ms 置けば、
**それは間ではなく、黙り込んだ後の空白である**（続けて鳴る音との間に、二重の空白ができる）。
"""
from __future__ import annotations

#: ⚠️ **著者の裁定の数（2026-10-21）。** ここ以外に書かない。
PAUSE_MS: dict[str, int] = {"。": 600, "、": 300}


def segments(text: str) -> list[tuple[str, int]]:
    """**切れ目で割り、後ろに置く無音の長さ（ms）を添える。**

    ⚠️ **記号は前の断片に残す。** 落とすと、`say` は文の終わりを知らない——
    **間だけを足して、抑揚を奪うことになる。**
    ⛔ **最後の断片の無音は 0 である**（上の「端の扱い」）。
    """
    out: list[tuple[str, int]] = []
    buffer = ""
    for ch in text:
        buffer += ch
        pause = PAUSE_MS.get(ch)
        if pause is not None:
            out.append((buffer, pause))
            buffer = ""
    if buffer:
        out.append((buffer, 0))
    elif out:
        # ⛔ **文末の記号の無音を落とす。** 落とさなければ、鳴り終わりに空白が残る。
        last_text, _ = out[-1]
        out[-1] = (last_text, 0)
    return out


def spoken(text: str) -> str:
    """**`say` に渡す本文。** 間は `[[slnc N]]` として、その場に書き込む。

    ⚠️ **`say` の命令であり、SSML ではない。** 綴りを変えると、
    記号のまま読み上げられる——**声は鳴るが、間は消える。**
    """
    return "".join(
        f"{piece}[[slnc {pause}]]" if pause else piece
        for piece, pause in segments(text)
    )


def gap_frames(pause_ms: int, rate: int) -> int:
    """**無音のフレーム数。** ⚠️ 端数は切り捨てる（**足りない側へ倒す**）。

    ⛔ **`rate` を既定にしない。** 基板の標本化周波数は `board.h` に1つ在り、
    **ここに2つ目の数を置けば、片方が古くなる。**
    """
    if pause_ms < 0:
        raise ValueError(f"負の無音は無い: {pause_ms}")
    if rate <= 0:
        raise ValueError(f"標本化周波数は正である: {rate}")
    return rate * pause_ms // 1000


__all__ = ["PAUSE_MS", "segments", "spoken", "gap_frames"]
