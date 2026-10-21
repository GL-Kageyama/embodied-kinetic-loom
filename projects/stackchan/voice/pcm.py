# -*- coding: utf-8 -*-
"""**標本を、リンクが運べる形と大きさにする。**

⛔ **1行に収まらないから割るのではない。** 音は、行ではない——
`audio <n>` という頭のあとに **n バイトの生の標本**が続き、**その中に改行は無い**
（標本の1バイトが 0x0A でありうる）。⇒ **割るのは、基板の受けるバッファの大きさに合わせるためである。**

⛔ **この道は 2026-10-21 に3回作り直された。記録は1行で足りる。**
µ-law（24,000 B/s）は途切れを消し、耳が **「ざらつく」** と言った。
16 kHz（32,000 B/s）は回線に余裕をくれ、耳が **「こもる」「始めの頃のほうが
クリアだった」** と言った——**測ればその通り**で、この声は **8〜12 kHz に
−18.5 dB 分**を載せている。⇒ **24 kHz・16ビット・48,000 B/s に戻す。**
**回線のむらは、先読みの深さ（683 ms）で受ける**——速さで受けない。

⚠️ **標本レートは基板のものである**（`main/board.h` の `kAudioSampleRate`）。
**ここはそれを知らない**——WAV の `readframes` をそのまま運ぶだけである。
**ゆえに 24 kHz の WAV を作るのは縁の仕事である**（`voice/__main__.py`）。

⛔ **`MAX_BYTES` は基板の数である**（`main/audio_line.h` の `kMaxBytes`）。
**これを越える頭は、基板が丸ごと拒む**——半分だけ鳴る、という形にはならない。
⚠️ **そして偶数であること。** 2バイトが1標本なので、**奇数の塊は半端な標本**である。
"""
from __future__ import annotations

#: ⚠️ **基板のバッファ**（`audio_line.h` の `kMaxBytes`）。**ここを動かすなら、あちらも動かす。**
MAX_BYTES = 4096

#: ⚠️ **こちらの塊は、基板の上限そのものである。** 4096 バイトは 24 kHz で
#: **85 ms** であり、基板はこれを8つまで先に持ち、**683 ms** を回線のむらに
#: 充てる（`audio_line.h`）。⛔ かつてこの塊は 4096 で、**基板の待ち行列が
#: 33 KB を要求し、空きが 36,512 バイトしか無かったので、行列は黙って作られ
#: なかった**——ゆえに一度 2048 へ落とした。⚠️ 同じ基板が 2048 の待ち行列を
#: 抱えた状態で **95,940 バイトの空き**を報告したので、4096 へ戻した
#: （2026-10-21）。**基板は起動時に `audio queue up` か `no memory` を言う。**
CHUNK = 4096


def bytes_of(samples: list[int]) -> bytes:
    """**標本を、リトルエンディアンの16ビットにする。** ⛔ 範囲外は丸める——例外にしない。

    ⚠️ **これがリンクの形である**——頭のあとの n バイトは、この並びそのものだ。
    """
    out = bytearray()
    for sample in samples:
        value = int(sample)
        if value > 32767:
            value = 32767
        elif value < -32768:
            value = -32768
        out += value.to_bytes(2, "little", signed=True)
    return bytes(out)


def head(count: int) -> bytes:
    """**塊の頭。** ⚠️ **綴りは基板のものである**——`audio <n>` と1つの改行、それだけ。

    ⛔ **奇数の n は送らない。** 基板は丸ごと拒み、音は1バイトも鳴らない。
    """
    if count <= 0 or count > MAX_BYTES:
        raise ValueError(f"audio {count}: 1..{MAX_BYTES} でなければならない")
    if count % 2 != 0:
        raise ValueError(f"audio {count}: 2バイトが1標本なので、偶数でなければならない")
    return f"audio {count}\n".encode("ascii")


def blocks(data: bytes, chunk: int = CHUNK) -> list[bytes]:
    """**16ビットの標本の並びを、頭つきの塊に割る。**

    `data` はリトルエンディアンの16ビット（WAV の `readframes` のまま）である。
    最後の塊は短くてよい——⚠️ **ただし偶数である。**
    """
    if chunk <= 0 or chunk > MAX_BYTES or chunk % 2 != 0:
        raise ValueError(f"chunk {chunk}: 2..{MAX_BYTES} の偶数でなければならない")
    if len(data) % 2 != 0:
        # ⚠️ 16ビットの並びが半端なら、標本として読めない。**鳴らさずに落とす。**
        raise ValueError(f"odd pcm: {len(data)} bytes")
    out = []
    for start in range(0, len(data), chunk):
        piece = data[start:start + chunk]
        out.append(head(len(piece)) + piece)
    return out


__all__ = ["MAX_BYTES", "CHUNK", "bytes_of", "head", "blocks"]
