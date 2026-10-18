# -*- coding: utf-8 -*-
"""**基板の枠パーサを、実際にコンパイルして走らせる。**

⛔ **なぜ要るか。** 2026-10-18、ホストが初めて本物の枠を基板へ書いたとき、
基板は `frame: refused (malformed)` と答えた——**正しい枠を、1つも受理したことが
なかったからである。** `parse_command` は閉じ括弧 `}` を読み飛ばさずに `break` し、
最後の「余分なバイト」検査が、その `}` を余分なバイトと読んでいた。

⚠️ **その欠陥は、既存の検査を全部通っていた。** `tests/test_stackchan_wire.py` は
**語の綴りを字面で比べる**だけで、C++ を1行も走らせない。
⇒ **字面の一致は、受理の一致ではない。** このファイルが、その差を埋める。

## ⛔ このファイルが確かめないこと

- **ファームウェアはビルドしない。** `main.cpp` も `leds.cpp` も `servo.cpp` も通さない。
  **確かめるのは `command_frame.cpp` の受理と拒否だけである。**
- **機体には何も届かない。** ここに端末は無い。
- ⚠️ **コンパイラの無い環境では、丸ごと飛ばす**（`skipif`）。**飛ばしたことは、
  緑と同じ意味を持たない**——理由を `skip` の文に書いてある。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE = REPO_ROOT / "projects" / "stackchan-firmware"
SOURCE = FIRMWARE / "command_frame.cpp"

COMPILER = shutil.which("clang++") or shutil.which("g++")

pytestmark = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——パーサは走らせられない",
)

#: **1行を受け取り、`ParseResult` の数を1つ出すだけの器。**
HARNESS = r"""
#include "command_frame.h"
#include <cstdio>
#include <cstring>

int main(int argc, char** argv) {
  if (argc < 2) {
    return 100;
  }
  Command command;
  const ParseResult result =
      parse_command(argv[1], static_cast<int>(std::strlen(argv[1])), &command);
  std::printf("%d\n", static_cast<int>(result));
  return 0;
}
"""

#: ⚠️ **`command_frame.h` の並びである。** 数を書くのは、その並びが変わった日に
#: この表が黙って別の意味にならないためである（`test_the_enum_still_matches`）。
OK = 0
MALFORMED = 2
NOT_AN_OBJECT = 3
UNKNOWN_KEY = 4
MISSING_KEY = 5
UNKNOWN_VALUE = 7


@pytest.fixture(scope="module")
def parser(tmp_path_factory) -> pathlib.Path:
    directory = tmp_path_factory.mktemp("frame-parser")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "parser"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-I", str(FIRMWARE), "-o", str(binary),
         str(harness), str(SOURCE)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"
    return binary


def run(parser: pathlib.Path, line: str) -> int:
    done = subprocess.run([str(parser), line], capture_output=True, text=True)
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    return int(done.stdout.strip())


def test_the_enum_still_matches():
    """⚠️ **数の対応を、ヘッダに対して確かめる。**

    ⛔ この表が古くなれば、以下の検査は**別の意味の数を比べて緑になる**。
    """
    header = (FIRMWARE / "command_frame.h").read_text(encoding="utf-8")
    order = ["kOk", "kTooLong", "kMalformed", "kNotAnObject", "kUnknownKey",
             "kMissingKey", "kBadType", "kUnknownValue"]
    positions = [header.index(f"  {name},") for name in order]
    assert positions == sorted(positions), "enum の並びが表と違う"


@pytest.mark.parametrize(
    "line, expected",
    [
        # ✅ **受理される形。** 閉じ括弧の後に改行が在っても、無くても。
        ('{"face":"greeting","gesture":"perk","light":"warm"}', OK),
        ('{"face":"greeting","gesture":"perk","light":"warm"}\n', OK),
        ('{"face":null,"gesture":null,"light":"breathe"}', OK),
        # ⚠️ **鍵の順は問わない**（パーサの docstring がそう言っている）。
        ('{"light":"dim","face":"curious","gesture":"nod"}', OK),
        # ⛔ **1行に2つは拒む。**
        ('{"face":null,"gesture":null,"light":"dim"}{}', MALFORMED),
        ('{"face":null,"gesture":null,"light":"dim"} ', OK),
        # ⛔ **知らない鍵は拒む**——同乗できないことが privacy である。
        ('{"face":null,"gesture":null,"light":"dim","prompt":"secret"}', UNKNOWN_KEY),
        # ⛔ **欠けた鍵は拒む。**
        ('{"face":null,"light":"dim"}', MISSING_KEY),
        ('{}', MISSING_KEY),
        # ⛔ **語彙の外の語は拒む。**
        ('{"face":"smug","gesture":null,"light":"dim"}', UNKNOWN_VALUE),
        ('{"face":null,"gesture":null,"light":null}', MISSING_KEY),
        # ⛔ **対象でない行は拒む。**
        ('pose 50 857*2A', NOT_AN_OBJECT),
        ('', NOT_AN_OBJECT),
    ],
)
def test_the_parser_accepts_and_refuses_what_it_says(parser, line, expected):
    """⛔ **閉じ括弧を1つ読み飛ばすだけで、ここは全部 `malformed` になる。**

    2026-10-18 の欠陥は、まさにその1バイトだった。
    """
    assert run(parser, line) == expected
