# -*- coding: utf-8 -*-
"""**文を、24 kHz・16ビット・モノラルの WAV にする縁。**

`python3 -m projects.stackchan.voice "終わりました。次は、走ります。" --out /tmp/a.wav`

⛔ **間の数は、ここに無い。** `render.spoken()` が `[[slnc N]]` として書き込み、
`render.PAUSE_MS` が唯一の出どころである（**2つ目の綴りを作らない**）。

⚠️ **`say` と `afconvert` は macOS のものである。** ここが縁である理由——
**規則は音を持たず、音を作るのは縁だけ**（`projects/**/__main__.py` は決定論の走査から除かれる）。

⛔ **この道具は、まだ何も鳴らさない。** ファイルを書くだけで、基板へは送らない。
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import tempfile

from .render import spoken

#: ⚠️ **声は1つに決めていない。** 既定は Kyoko——**著者の耳が決めるまで、これは仮である。**
DEFAULT_VOICE = "Kyoko"
#: ⚠️ **基板の標本化周波数に合わせる**（`board.h` の `kAudioSampleRate`）。
RATE = 24000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="projects.stackchan.voice")
    parser.add_argument("text", help="読み上げる文（日本語）")
    parser.add_argument("--out", required=True, help="書き出す .wav のパス")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    out = pathlib.Path(args.out)
    with tempfile.TemporaryDirectory() as tmp:
        aiff = pathlib.Path(tmp) / "voice.aiff"
        said = subprocess.run(
            ["say", "-v", args.voice, "-o", str(aiff), spoken(args.text)],
            capture_output=True,
            text=True,
        )
        if said.returncode != 0:
            sys.stderr.write(f"say failed: {said.stderr}\n")
            return 1
        converted = subprocess.run(
            ["afconvert", "-f", "WAVE", "-d", f"LEI16@{RATE}", "-c", "1",
             str(aiff), str(out)],
            capture_output=True,
            text=True,
        )
        if converted.returncode != 0:
            sys.stderr.write(f"afconvert failed: {converted.stderr}\n")
            return 1
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
