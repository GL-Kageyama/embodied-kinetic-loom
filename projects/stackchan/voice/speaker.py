# -*- coding: utf-8 -*-
"""**声の糸 —— 1文を、基板の回線へ流す。**

⛔ **呼ぶ側を待たせない。** 文を合成するのにも（`say` と `afconvert` で 1〜2 秒）、
4096 バイトの塊を書き切るのにも（85 ms の音）時間がかかる。**その2つを、
呼んだ糸の上でやってはならない**——この工房は既にそれを1度払っている:
2026-10-21、読みながら鳴らす読み手は **実時間の3分の1**でしか鳴らず、
**読むことと鳴らすことが交互にしか進まなかった**（`dial.cpp`）。

⚠️ **ここは決定論の側である**（`tools/purity.py` の一覧を輸入しない）。
時計も、ソケットも、`subprocess` も無い:
**文を合成する函数と、バイトを送る相手は、どちらも値として渡る。**

⛔ **塊を送る口は `link.send` である**——行を書く口ではない。音声の塊は行ではなく、
`audio <n>` の頭のあとの n バイトの中の 0x0A は改行ではない（`pcm.py`）。
"""
from __future__ import annotations

import queue
import threading
from typing import Callable

from . import pcm

#: **文を標本にする函数。** ⛔ **ここは `say` を知らない**——知れば、このモジュールが
#: `subprocess` を輸入し、決定論の一覧に載る。**合成は縁の仕事である**（`__main__.py`）。
Render = Callable[[str], list[int]]

#: **送る口。** ⚠️ `Link.send` と同じ形だけを要求する——**このモジュールは `Link` を知らない。**
Send = Callable[[bytes], bool]

Sink = Callable[[dict], None]

#: **糸が降りるのを待つ上限（秒）。** ⚠️ 3.5 秒の音が鳴り終わるより長い。
STOP_WAIT = 10.0


class Speaker:
    """**1本の糸と、深さ1の待ち行列。**

    ⚠️ **深さは1である。** 声は候補の1文であり、候補には寿命がある（§12）。
    **2つ溜めれば、古い方を読むことになる**——古い候補を、新しい瞬間に言う声は、
    数が合っているのに嘘になる。⇒ **話している最中に来た文は、断る**
    （`say` が `False` を返し、縁が `{"voice": "busy"}` を残す）。

    ⛔ **断ることは、黙って落とすことではない。** 落とせば、
    「規則が鳴ったのに声が出なかった日」が数えられない（`render.py` の同じ理屈）。
    """

    def __init__(self, send: Send, render: Render, *,
                 emit: Sink | None = None) -> None:
        self._send = send
        self._render = render
        self._emit = emit
        self._queue: queue.Queue[tuple[str, float] | None] = queue.Queue(maxsize=1)
        self._thread: threading.Thread | None = None
        #: ⛔ **行列の深さだけでは足りない。** 糸は文をすぐ取り出すので、
        #: **合成している3秒のあいだ、行列は空である**——空を「話していない」と
        #: 読めば、**古い文の最中に来た文が、その後ろで待つ。** ゆえに印を持つ。
        self._busy = threading.Event()

    # --- 呼ぶ側 ---------------------------------------------------------

    def start(self) -> None:
        """**糸を1本起こす。** ⚠️ `daemon=True`——降りるのはプロセスと一緒である。"""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="voice", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """**糸に降りてもらう。** ⛔ **塊の途中では降りない**——1つを書き切ってから。**

        ⚠️ **満杯でも入れる**（`say` ではない）——降りる合図を、断りの行として
        書いてしまわないためである。
        """
        if self._thread is None:
            return
        try:
            self._queue.put(None, timeout=STOP_WAIT)
        except queue.Full:
            pass
        self._thread.join(timeout=STOP_WAIT)
        self._thread = None
        self._busy.clear()

    def say(self, text: str, at: float = 0.0) -> bool:
        """**1文を、声の糸へ渡す。** ⛔ **ここでは合成しない。待ちもしない。**

        ⚠️ **話している最中なら `False` である**——古い候補を、新しい瞬間に言わない。
        """
        if self._busy.is_set():
            self._row({"voice": "busy"})
            return False
        self._busy.set()
        try:
            self._queue.put_nowait((text, at))
        except queue.Full:
            self._busy.clear()
            self._row({"voice": "busy"})
            return False
        return True

    # --- 糸 -------------------------------------------------------------

    def _row(self, payload: dict) -> None:
        if self._emit is not None:
            self._emit(payload)

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                return
            text, at = item
            try:
                self._utter(text, at)
            finally:
                # ⚠️ **印は必ず降ろす。** 降ろし忘れれば、その日からこの糸は
                #    何も言わない——**黙っている理由が、どこにも残らない。**
                self._busy.clear()

    def _utter(self, text: str, at: float) -> bool:
        """**1文を、頭つきの塊の列にして送る。** ⛔ **1つでも書けなければ、そこで止める。**

        ⚠️ **止めた後は何もしない。** 回線の頭と標本の境目はずれており、
        **それは `serve` が捨てる**（`Link._broken`）。ここで閉じれば、
        fd を2本の糸が閉じることになる。
        """
        try:
            samples = self._render(text)
        except Exception as error:  # noqa: BLE001 — 縁の失敗は、声の不在である
            # ⛔ **無音で埋めない。** 合成できなかったことは、行になる。
            self._row({"voice": "cannot render", "error": type(error).__name__})
            return False

        data = pcm.bytes_of(samples)
        pieces = pcm.blocks(data)
        for piece in pieces:
            if not self._send(piece):
                self._row({"voice": "cut", "blocks": len(pieces), "bytes": len(data)})
                return False
        # ⚠️ **文そのものは残さない。** 数だけである（§8.2 と同じ作法——
        #    ログは、その日の内訳を数えるために在り、言った言葉を写すためではない）。
        self._row({"voice": "spoke", "blocks": len(pieces), "bytes": len(data)})
        return True


__all__ = ["Render", "Send", "Speaker", "STOP_WAIT"]
