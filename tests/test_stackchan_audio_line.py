# -*- coding: utf-8 -*-
"""**音の塊の頭を、実際にコンパイルして走らせる。**

⛔ **なぜ要るか。** この頭は、この基板で**唯一「行ではないもの」の始まり**である——
`audio <n>` のあとの n バイトは生の標本であり、**改行で割られない**。
その境目を1バイト読み違えれば、**音は鳴らず、代わりに標本が命令として走るか、
命令が標本として鳴る。** どちらも静かに起きる。

⚠️ **確かめるのは `audio_line.cpp` の受理と拒否だけである。** `sound::play_pcm` も
`dial.cpp` の読み手も**ここでは走らない**——I2S もソケットも無い。
**鳴ったかどうかは、このファイルの外の話である。**

⚠️ **コンパイラの無い環境では丸ごと飛ばす**（`skipif`）。飛ばしたことは緑と同じ意味を持たない。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE = REPO_ROOT / "projects" / "stackchan-firmware"
SOURCE = FIRMWARE / "main" / "audio_line.cpp"

COMPILER = shutil.which("clang++") or shutil.which("g++")

pytestmark = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——頭のパーサは走らせられない",
)

#: **1行を受け取り、受理なら「数の答え」、拒否なら `-1` を出す器。**
HARNESS = r"""
#include "audio_line.h"
#include <cstdio>
#include <cstring>

int main(int argc, char** argv) {
  if (argc < 2) {
    return 100;
  }
  int bytes = 0;
  const bool ok = audio_line::parse(argv[1], static_cast<int>(std::strlen(argv[1])), &bytes);
  std::printf("%d\n", ok ? bytes : -1);
  return 0;
}
"""


@pytest.fixture(scope="module")
def parser(tmp_path_factory) -> pathlib.Path:
    directory = tmp_path_factory.mktemp("audio-line")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "parser"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-I", str(FIRMWARE / "main"), "-o", str(binary),
         str(harness), str(SOURCE)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"
    return binary


def run(parser: pathlib.Path, line: str) -> int:
    done = subprocess.run([str(parser), line], capture_output=True, text=True)
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    return int(done.stdout.strip())


def test_the_bound_matches_the_host_s_chunk():
    """⚠️ **基板のバッファと、ホストの上限が同じ数であること。**

    ⛔ 食い違えば、ホストは**基板が丸ごと拒む頭**を送り続け、音は1バイトも鳴らない
    ——そして送る側からは「送れた」と見える。
    """
    from projects.stackchan.voice import pcm

    header = (FIRMWARE / "main" / "audio_line.h").read_text(encoding="utf-8")
    assert "constexpr int kMaxBytes = 4096;" in header
    assert pcm.MAX_BYTES == 4096
    assert pcm.CHUNK <= pcm.MAX_BYTES


@pytest.mark.parametrize(
    "line, expected",
    [
        # ✅ **受理される形。** 2 から 4096 までの**偶数**。
        # ⛔ **2バイトが1標本である。** 奇数の塊は半端な標本であり、鳴らせない。
        ("audio 2", 2),
        ("audio 4", 4),
        ("audio 1024", 1024),
        ("audio 2046", 2046),
        ("audio 2048", 2048),
        ("audio 4096", 4096),
        # ⛔ **奇数は拒む。** 16ビットの標本は2バイトで、半端は標本ではない。
        ("audio 1", -1),
        ("audio 3", -1),
        ("audio 2047", -1),
        ("audio 4095", -1),
        # ⛔ **0 は拒む。** 「何もしない」を命じられる読み手は、永遠に何もしない読み手である。
        ("audio 0", -1),
        # ⛔ **上限を越えるものは拒む。** ⚠️ 途中で拒むので、桁あふれもしない。
        ("audio 4098", -1),
        ("audio 99999999999999999999", -1),
        # ⛔ **綴りは1つだけ。** 先頭の 0、符号、空白、大文字——どれも別の語である。
        ("audio 02", -1),
        ("audio +2", -1),
        ("audio -2", -1),
        ("audio  2", -1),
        ("Audio 2", -1),
        ("audio2", -1),
        ("audio", -1),
        ("audio ", -1),
        # ⛔ **行でないものは拒む**——`pose` も枠も、この頭ではない。
        ("pose 100 491*26", -1),
        ('{"face":null,"gesture":null,"light":"dim","sound":null}', -1),
        ("", -1),
        ("  audio 2", -1),
        # ⚠️ **数字のあとに何か在れば拒む。**
        ("audio 2 ", -1),
        ("audio 2x", -1),
        ("audio 2\r", -1),
    ],
)
def test_the_head_accepts_and_refuses_what_it_says(parser, line, expected):
    assert run(parser, line) == expected


def test_a_sample_byte_may_be_a_newline(parser):
    """⛔ **これが、この文法が在る理由である。**

    標本の1バイトは 0x0A でありうる。**頭が無ければ、その1バイトで行が切れる。**
    ⚠️ ここで確かめるのは**数の話**だけである——0x0A を含む塊を、この頭は
    **2 バイトでも 2048 バイトでも同じように**受ける。
    """
    assert run(parser, "audio 2") == 2
    assert run(parser, "audio 2048") == 2048


# --- 標本は運ばれるだけである ------------------------------------------------
#
# ⛔ **µ-law の展開器は 2026-10-21 にここから消えた。** 二つの端が同じ数で鳴るかを
# 突き合わせる必要があったのは、**符号化が損失であったから**である。16ビット線形に
# 戻ったいま、**ホストが送った2バイトは、基板がそのまま I2S へ書く**——照合する
# 算術が両端に無い。⚠️ **ゆえにこの節は空である**。空所は欠陥ではない。
#
# ⚠️ **代わりに鳴るのは、頭の側の検査だけである**（上の `parse`）。**鳴った音が
# 正しいかは、このファイルの外の話**——耳か、基板の外の計器の話である。
