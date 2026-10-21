# -*- coding: utf-8 -*-
"""**文を、24 kHz・16ビット・モノラルの WAV にする縁。**

`python3 -m projects.stackchan.voice "終わりました。次は、走ります。" --out /tmp/a.wav`

⛔ **規則はここに無い。** 間は `render.PAUSE_MS`、声の高さは `render.PITCH`、
つなぎ方は `wav.trim` と `wav.join`——**この縁は道具を呼ぶだけで、数を1つも持たない。**

⛔ **1文を1回の `say` に渡さない。** 渡せば `say` が句読点に自分の間を入れ、
**規則がその上に乗って二重になる**（実測で 600 のつもりが 816.3 ms）。
⇒ **断片ごとに合成し、端を切り、規則どおりの無音でつなぐ**（設計 §22.3 の3行目）。

⚠️ **`say` と `afconvert` は macOS のものである。** ここが縁である理由——
**規則は音を持たず、音を作るのは縁だけ**（`projects/**/__main__.py` は決定論の走査から除かれる）。

⚠️ **このファイルは、2つの入口から使われる**（2026-10-21）——**この道具**（下の `main`）と、
**デーモンの声の糸**（`speaker.Speaker` に渡す `samples`）。⛔ **合成を2か所に
書かない**のは、`subprocess` を輸入してよいのが**縁だけ**だからである
（`tools/purity.py` の一覧）。⇒ **鎖はこのファイルに1つだけ在る。**

⛔ **`samples` は、まだ何も送らない。** 標本を返すだけで、基板へは送らない——
**送るのは `speaker.py` であり、鳴らすのは基板である。**
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile
import wave

from .render import GAIN, PITCH, VOICE, pitched, segments
from .wav import join, normalize, scale, trim

#: ⚠️ **基板の標本化周波数に合わせる**（`board.h` の `kAudioSampleRate`）。
#: ⛔ **2026-10-21 に 16 kHz を試して、同じ日に戻した。** 回線には楽だった
#: （32,000 B/s）が、著者の耳は **「始めの頃のほうがクリアだった」** と言い、
#: 測れば **8〜12 kHz に −18.5 dB 分**があった——16 kHz はそれを消す。
#: ⚠️ **間の長さは動かない**: `gap_frames` はミリ秒から標本を出すだけである。
RATE = 24000


def _say(text: str, voice: str, pitch: int, into: pathlib.Path) -> list[int]:
    """**1つの断片を合成し、端を切った標本を返す。** ⛔ 失敗は例外である——無音で埋めない。"""
    aiff = into.with_suffix(".aiff")
    wav = into.with_suffix(".wav")
    said = subprocess.run(
        ["say", "-v", voice, "-o", str(aiff), pitched(text, pitch)],
        capture_output=True, text=True,
    )
    if said.returncode != 0:
        raise RuntimeError(f"say failed: {said.stderr.strip()}")
    converted = subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", f"LEI16@{RATE}", "-c", "1",
         str(aiff), str(wav)],
        capture_output=True, text=True,
    )
    if converted.returncode != 0:
        raise RuntimeError(f"afconvert failed: {converted.stderr.strip()}")
    with wave.open(str(wav)) as w:
        data = w.readframes(w.getnframes())
    return trim([
        int.from_bytes(data[i:i + 2], "little", signed=True)
        for i in range(0, len(data) - 1, 2)
    ])


def samples(text: str, *, voice: str = VOICE, pitch: int = PITCH) -> list[int]:
    """**1文を、24 kHz・16ビットの標本にする。** ⛔ 失敗は例外である——無音で埋めない。

    ⚠️ **鎖は `main` と同じである**——断片ごとに合成し、端を切り、規則の無音で
    つなぎ、正規化してから `GAIN` を掛ける。⛔ **2つの入口に2つの鎖を書けば、
    片方だけが直る日が来る。**
    """
    pieces = segments(text)
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        parts = []
        for i, (piece, _) in enumerate(pieces):
            parts.append(_say(piece, voice, pitch, work / f"p{i}"))
        # ⚠️ **掛けるのは、つないだ後である**——端を切る閾値（200）は生の標本に当てる。
        # ⛔ **正規化が先、`GAIN` が後。** `say` の返す大きさは一定でない
        # （実測ピーク −18.9 dBFS）ので、掛け算だけで大きさを決めると
        # **声の機嫌が音量になる**。正規化してから掛ければ、`GAIN` が唯一の数になる。
        return scale(normalize(join(parts, [pause for _, pause in pieces], RATE)), GAIN)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="projects.stackchan.voice")
    parser.add_argument("text", help="読み上げる文（日本語）")
    parser.add_argument("--out", required=True, help="書き出す .wav のパス")
    parser.add_argument("--voice", default=VOICE)
    parser.add_argument("--pitch", type=int, default=PITCH,
                        help="声の高さ（say の pbas。⚠️ セミトーンではない）")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    out = pathlib.Path(args.out)
    try:
        rendered = samples(args.text, voice=args.voice, pitch=args.pitch)
    except RuntimeError as error:
        sys.stderr.write(f"{error}\n")
        return 1

    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(
            int(s).to_bytes(2, "little", signed=True) for s in rendered
        ))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
