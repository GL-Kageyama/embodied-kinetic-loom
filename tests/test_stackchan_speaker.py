# -*- coding: utf-8 -*-
"""**声の糸 —— 1文が、頭つきの塊の列になって出ていく。**

⛔ **ここで確かめないこと:** `say` の声、`afconvert` の変換、基板の増幅器、Wi-Fi。
**合成は函数として渡る**（`Render`）ので、このファイルは**鎖を持たない**——
ゆえに**声そのものは、ここでは1ミリ秒も鳴らない。**

⚠️ **ここが測るのは3つである**: ① 塊の形（`audio <n>` と、その n バイト）
② 呼ぶ側を待たせないこと ③ **断ったことが行になること**。
"""
from __future__ import annotations

import threading
import time

import pytest

from projects.stackchan.voice import pcm
from projects.stackchan.voice.speaker import Speaker

#: ⚠️ **糸を待つ上限（秒）。** 本物の合成（1〜2 秒）より長く取る。
WAIT = 2.0


class Wire:
    """**送られた塊を、順に溜める。** ⛔ 回線ではない——**形だけが `Link.send` と同じである。**"""

    def __init__(self, fail_at: int | None = None) -> None:
        self.pieces: list[bytes] = []
        self.fail_at = fail_at

    def send(self, payload: bytes) -> bool:
        if self.fail_at is not None and len(self.pieces) >= self.fail_at:
            return False
        self.pieces.append(payload)
        return True

    def stream(self) -> bytes:
        return b"".join(self.pieces)


def _wait_until(condition, message: str) -> None:
    deadline = time.monotonic() + WAIT
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError(message)


def _samples(count: int) -> list[int]:
    """**`count` 個の標本。** ⚠️ 値は問わない——ここで測るのは長さと並びである。"""
    return [((i * 37) % 2000) - 1000 for i in range(count)]


def test_a_sentence_goes_out_as_a_head_and_its_bytes():
    """⚠️ **頭は基板の綴りである**（`audio <n>` と1つの改行）。⛔ **行ではない。**"""
    wire = Wire()
    speaker = Speaker(wire.send, lambda text: _samples(3000))
    speaker.start()
    try:
        assert speaker.say("長かった。") is True
        _wait_until(lambda: wire.pieces, "1つも送られなかった")
        _wait_until(lambda: len(wire.pieces) == 2, "2つ目の塊が来なかった")
        pieces = pcm.blocks(pcm.bytes_of(_samples(3000)))
        assert wire.pieces == pieces
        # ⚠️ **最初の塊は、基板の上限ちょうどである**（4096 バイト）。
        assert wire.pieces[0].startswith(b"audio 4096\n")
        assert len(wire.pieces[0]) == len(b"audio 4096\n") + 4096
        # ⚠️ **最後は短くてよい**——6000 バイトの残りは 1904 バイトである。
        assert wire.pieces[1].startswith(b"audio 1904\n")
    finally:
        speaker.stop()


def test_the_log_keeps_the_count_and_not_the_words():
    """⛔ **言った言葉を写さない。** 数だけである（§8.2 と同じ作法）。"""
    rows: list[dict] = []
    wire = Wire()
    speaker = Speaker(wire.send, lambda text: _samples(100), emit=rows.append)
    speaker.start()
    try:
        speaker.say("これは、声にだけ出る文である。")
        _wait_until(lambda: any(r.get("voice") == "spoke" for r in rows),
                    "話した行が無い")
    finally:
        speaker.stop()
    spoken = [r for r in rows if r.get("voice") == "spoke"][0]
    assert spoken["bytes"] == 200
    assert spoken["blocks"] == 1
    assert "これは" not in str(rows), "言葉が行に載っている"


def test_a_second_sentence_is_refused_while_the_first_is_speaking():
    """⛔ **古い候補を、新しい瞬間に言わない。** ⚠️ **断りは行になる。**"""
    rows: list[dict] = []
    wire = Wire()
    release = threading.Event()

    def render(text: str) -> list[int]:
        release.wait(WAIT)
        return _samples(100)

    speaker = Speaker(wire.send, render, emit=rows.append)
    speaker.start()
    try:
        assert speaker.say("1つめ") is True
        # ⚠️ **糸は、もう1つめを抱えている。** 2つめは断られる。
        assert speaker.say("2つめ") is False
        assert any(r.get("voice") == "busy" for r in rows), "断りが行になっていない"
    finally:
        release.set()
        speaker.stop()


def test_a_render_that_fails_is_a_row_not_silence():
    """⛔ **合成できなかったことを、無音で埋めない。**

    ⚠️ **`say` が失敗する日は必ず来る**（声が消えた、`afconvert` が変わった）。
    その日に**黙って0バイトを送る**なら、基板は「言うことが無かった」と読む。
    """
    rows: list[dict] = []
    wire = Wire()

    def render(text: str) -> list[int]:
        raise RuntimeError("say failed")

    speaker = Speaker(wire.send, render, emit=rows.append)
    speaker.start()
    try:
        speaker.say("言えない文")
        _wait_until(lambda: any(r.get("voice") == "cannot render" for r in rows),
                    "失敗の行が無い")
    finally:
        speaker.stop()
    assert wire.pieces == [], "失敗したのに送っている"
    failed = [r for r in rows if r.get("voice") == "cannot render"][0]
    assert failed["error"] == "RuntimeError"


def test_a_block_that_cannot_be_written_stops_the_rest():
    """⛔ **途中で書けなくなったら、残りを送らない。**

    ⚠️ **送れば、基板は次の頭のバイトを前の塊の続きとして食う**——頭と標本の
    境目がずれた回線は、もう戻らない（`Link.send` が `broken` を立てる理由）。
    """
    rows: list[dict] = []
    wire = Wire(fail_at=1)  # ⚠️ **2つ目で書けなくなる。**
    speaker = Speaker(wire.send, lambda text: _samples(5000), emit=rows.append)
    speaker.start()
    try:
        speaker.say("長い文")
        _wait_until(lambda: any(r.get("voice") == "cut" for r in rows),
                    "切れた行が無い")
    finally:
        speaker.stop()
    assert len(wire.pieces) == 1, f"切れた後も送っている: {len(wire.pieces)}"
    cut = [r for r in rows if r.get("voice") == "cut"][0]
    # ⚠️ **全体の数は残す**——どこで切れたかを、あとから数えられるように。
    assert cut["blocks"] == 3
    assert cut["bytes"] == 10000


def test_stopping_a_speaker_that_never_started_is_nothing():
    """⚠️ **起こしていない糸を、降ろそうとしても何も起きない。**"""
    speaker = Speaker(Wire().send, lambda text: [])
    speaker.stop()  # ⛔ 例外にならないこと自体が、この試験である。
    assert speaker.say("黙っている") is True


def test_the_speaker_does_not_wait_for_the_render():
    """⛔ **`say` は、合成を待たない。** 待てば、呼んだ糸が 1〜2 秒止まる。

    ⚠️ **2026-10-21 の同じ形**（読みながら鳴らす読み手は実時間の3分の1しか
    鳴らなかった）。**待つ者が居る場所を、1つに決める**——ここでは声の糸だけである。
    """
    release = threading.Event()
    started = threading.Event()

    def render(text: str) -> list[int]:
        started.set()
        release.wait(WAIT)
        return _samples(10)

    speaker = Speaker(Wire().send, render)
    speaker.start()
    try:
        began = time.monotonic()
        assert speaker.say("待たない文") is True
        took = time.monotonic() - began
        assert took < 0.05, f"合成を待っている: {took:.3f} 秒"
        assert started.wait(WAIT), "糸が動いていない"
    finally:
        release.set()
        speaker.stop()


@pytest.mark.parametrize("count", [0, 1])
def test_a_sentence_shorter_than_a_block_is_still_one_head(count):
    """⚠️ **短い文でも、頭は1つである。** ⛔ **頭を省いては、基板は音を読めない。**"""
    wire = Wire()
    speaker = Speaker(wire.send, lambda text: _samples(count))
    speaker.start()
    try:
        speaker.say("短い")
        if count == 0:
            # ⛔ **標本0は、塊0である。** ⚠️ `pcm.blocks(b"")` は空の列を返す
            #    ——**頭の無い空の列**であり、送るものが無いことと等しい。
            time.sleep(0.1)
            assert wire.pieces == []
        else:
            _wait_until(lambda: wire.pieces, "1つも送られなかった")
            # ⚠️ **標本1つは、2バイトの塊1つである**——頭は `audio 2`。
            assert wire.pieces == pcm.blocks(pcm.bytes_of(_samples(1)))
            assert wire.pieces[0].startswith(b"audio 2\n")
    finally:
        speaker.stop()
