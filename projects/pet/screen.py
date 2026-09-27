# -*- coding: utf-8 -*-
"""画面——**1フレームを、1回の write で出す。**

⛔ **このファイルは `engine/` の外に在る。** ゆえに `engine/` の純度検査は、
**このファイルを1行も見ていない**——**それが決定 C の代価である**（[05] §3.3、2026-09-28）。
⇒ **だから `projects/` は自前の検査を持つ**: `tests/test_pet_purity.py`。
**そしてこのファイルは `time` を import しない**——**時計は `__main__.py` が持つ。**

**なぜ、1フレームを1回の write にまとめるのか**（[04] §8.1 が根拠である）。
⚠️ **速さの話ではない。****同期更新の対が、1回の write の中で閉じるからである。**
`CSI ? 2026 h` を出した後、`l` を出す前に落ちれば、**端末は描画を止めたままになる**
——**利用者から見れば、端末が固まったのと同じである。**
⇒ **`frame()` は必ず `h` と `l` の両方を含む1つの文字列を返す。** ゆえに、
**write が分割されない限り、対は閉じる。** 分割しないことが、ここでの安全性である。

⚠️ **そして `CSI ? 2026` に対応しているかを、このセッションからは測れない**（[05] §3.3 の ⚠️）。
⇒ **`synchronised` の既定は `False` である。** **測っていない前提を、端末に触る唯一の場所へ
既定で入れるわけにはいかない。** 使う側が `--sync` で入れる。
"""
from __future__ import annotations

from typing import Protocol

from .expressions import BOX_HEIGHT, BOX_WIDTH, FACES, State

__all__ = ["HOME", "SYNC_BEGIN", "SYNC_END", "CLOSE", "frame", "box", "Screen"]


#: ⚠️ **画面の左上へ戻る。** これが無いと、2フレーム目が1フレーム目の下へ積まれる。
HOME = "\x1b[H"

#: ⛔ **同期更新の開始と終了**（`CSI ? 2026 h` / `l`）。
SYNC_BEGIN = "\x1b[?2026h"
SYNC_END = "\x1b[?2026l"

#: ⚠️ **終わりに出すもの。** **カーソルを次の行へ送る**——
#: **これが無いと、シェルのプロンプトが猫の上に重なる。**
CLOSE = "\r\n"


class Writer(Protocol):
    """⚠️ **出力は注入される。** 画面は、自分がどこへ書いているかを知らない。"""

    def write(self, text: str) -> object: ...


def box(state: State) -> tuple[str, ...]:
    """⛔ **顔を、箱に収める。**

    **幅**: 行ごとの字下げは出典のままに、**右を `BOX_WIDTH` まで空白で埋める**。
    **高さ**: 足りない行を空白で埋める——**眠い顔だけが4行なので、これが無いと
    前のフレームの4行目が残る**（下の `test_...` を見よ）。

    ⛔ **箱より広い行は、黙って切らない。** 切ると、**ずれたことに誰も気づかない。**
    """
    lines = FACES[state]
    if len(lines) > BOX_HEIGHT:
        raise ValueError(
            f"{state.value} の顔は {len(lines)} 行あるが、箱は {BOX_HEIGHT} 行である"
            "——⛔ **箱を黙って広げない。** 広げると、他の顔の位置がずれる"
        )
    padded = []
    for line in lines:
        if len(line) > BOX_WIDTH:
            raise ValueError(
                f"{state.value} の行が箱より広い: {line!r}（{len(line)} > {BOX_WIDTH}）"
                "——⛔ **切らない。** 切ると、ずれたことに誰も気づかない"
            )
        padded.append(line.ljust(BOX_WIDTH))
    padded.extend([" " * BOX_WIDTH] * (BOX_HEIGHT - len(padded)))
    return tuple(padded)


def frame(state: State, *, synchronised: bool = False) -> str:
    """⛔ **1フレーム＝1つの文字列。** 呼ぶ側は、これを1回の write で出す。

    ⚠️ **`synchronised=True` のとき、`SYNC_BEGIN` と `SYNC_END` は同じ文字列の中にある。**
    それが出せるのは、**write が1回だからである。**
    """
    body = "\r\n".join(box(state))
    if synchronised:
        return SYNC_BEGIN + HOME + body + SYNC_END
    return HOME + body


class Screen:
    """⚠️ **画面は、端末を借りているだけである。**

    ⛔ **借りたものは返す**——`close()` がそれである。`__main__.py` は `finally` で呼ぶ。
    """

    def __init__(self, out: Writer, *, synchronised: bool = False) -> None:
        self._out = out
        self._synchronised = synchronised

    def draw(self, state: State) -> None:
        """⛔ **1フレーム＝1回の write。** ここが、このクラスの唯一の主張である。"""
        self._out.write(frame(state, synchronised=self._synchronised))

    def close(self) -> None:
        """⚠️ **端末を、借りる前の状態へ返す。**

        ⛔ **`SYNC_END` は、同期更新を使ったときにだけ出す。**
        **使っていない画面が閉じるときに `l` を出すのは、しなかった借りを返すことである**
        ——**実測 2026-09-28、`--state sleepy` の出力に `^[[?2026l` が出ていた。**
        ⚠️ **そして、そのときの検査はこの欠陥に同意していた**（`writes == [CLOSE]`）。

        ⚠️ **同期更新を使っているとき、`l` は2回出る。** 1回目はフレームの中
        （`frame()` が対で返す）、2回目がここである。**冗長ではない**——
        **`frame()` は `h` と `l` を同じ文字列に持つが、write が途中で切れれば
        `l` は端末に届かない。** そのとき、**この2回目が無ければ端末は止まったままになる。**
        **`l` は冪等である**（消えているものを、もう一度消すだけである）。
        """
        self._out.write((SYNC_END if self._synchronised else "") + CLOSE)
