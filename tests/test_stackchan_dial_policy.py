# -*- coding: utf-8 -*-
"""**ソケットから届いた行のうち、どれを実行してよいかを、実際にコンパイルして確かめる。**

⛔ **なぜ要るか。** 0.19.60 から基板は二本の線で体を動かす——USB のコンソールと、
**基板が外へ開いた TCP のリンク**である。同じ `Dispatch` が両方を読む。
⚠️ **この二本は同じ channel ではない。** コンソールはその機械を手に持っている人であり、
リンクはセグメント上の何者でもありうるソケットである。

⇒ **この基板へ「どう届くか」を変える命令は、コンソールのものである。**
`bench wifi …` は SSID と PSK を運び、NVS に書き、station に新しい住所を置く。
`bench dial …` はリンク自体を別のホストへ向け直す。
⛔ **平文の TCP に流れた PSK は、線の上に書かれた PSK である**——この側の
コンソールが既に禁じているものと同じである。

## ⚠️ 規則の書き方

**動詞は `<verb>` か `<verb> ` に一致させる。接頭辞では一致させない。**
そうしなければ、いつか `bench wifiish` が、動詞だけを意味していた規則に巻き込まれる。

## ⛔ このファイルが確かめないこと

- **`dial.cpp` はビルドしない。** lwIP と FreeRTOS を要求するので、ここでは走らない。
  **確かめるのは `dial_policy.cpp` の判定だけである。**
- **機体にもリンクにも何も届かない。** ここにソケットは無い。
- ⚠️ **コンパイラの無い環境では、丸ごと飛ばす**（`skipif`）。**飛ばしたことは緑と同じ
  意味を持たない**——理由を `skip` の文に書いてある。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = REPO_ROOT / "projects" / "stackchan-firmware" / "main"
SOURCE = MAIN / "dial_policy.cpp"

COMPILER = shutil.which("clang++") or shutil.which("g++")

pytestmark = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——判定は走らせられない",
)

#: **1行を受け取り、`console_only` の答えを1つ出すだけの器。**
HARNESS = r"""
#include "dial_policy.h"
#include <cstdio>

int main(int argc, char** argv) {
  if (argc < 2) {
    return 100;
  }
  std::printf("%d\n", dial_policy::console_only(argv[1]) ? 1 : 0);
  return 0;
}
"""


@pytest.fixture(scope="module")
def policy(tmp_path_factory) -> pathlib.Path:
    directory = tmp_path_factory.mktemp("dial-policy")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "policy"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-I", str(MAIN), "-o", str(binary),
         str(harness), str(SOURCE)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"
    return binary


def run(policy: pathlib.Path, line: str) -> bool:
    done = subprocess.run([str(policy), line], capture_output=True, text=True)
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    return done.stdout.strip() == "1"


@pytest.mark.parametrize(
    "line",
    [
        # ⛔ **PSK を運ぶもの、NVS に書くもの、住所を変えるもの。**
        "bench wifi join BFW6K-G-48420 hunter2",
        "bench wifi join opennetwork",
        "bench wifi addr 192.168.0.77 255.255.255.0 192.168.0.254",
        "bench wifi scan",
        "bench wifi",
        # ⛔ **リンク自身を別のホストへ向け直すもの。**
        "bench dial 192.168.0.103 3333",
        "bench dial",
        # ⚠️ **動詞の直後が空白か終端である限り、引数の形は問わない。**
        "bench  wifi",
        "bench wifi ",
    ],
)
def test_the_console_keeps_these(policy: pathlib.Path, line: str) -> None:
    assert run(policy, line) is True


@pytest.mark.parametrize(
    "line",
    [
        # ✅ **体を動かす行は、どちらの線からでも届いてよい。**
        "bench pos",
        "bench set 10 40",
        "bench move 20",
        "bench sound chime",
        "bench leds",
        "bench power off",
        '{"face":"curious","gesture":null,"light":"writing","sound":null}',
        "pose 100 491*26",
        "help",
        # ⛔ **接頭辞では一致させない。** この三つは、規則が接頭辞だった日に
        #    巻き込まれる形である。
        "bench wifiish",
        "bench dialup",
        "bench net send 192.168.0.103 7000 hi",
        "benchmark",
        # ⚠️ **`bench` だけでは動詞が無い。**
        "bench",
        "",
    ],
)
def test_a_socket_may_carry_these(policy: pathlib.Path, line: str) -> None:
    assert run(policy, line) is False


def test_null_is_not_console_only() -> None:
    """⚠️ **`nullptr` は「拒む」ではない。** 行が無いことは、命令が禁じられている
    ことと同じではない——そして `Dispatch` は長さ 0 の行を既に捨てる。"""
    source = SOURCE.read_text(encoding="utf-8")
    assert "line == nullptr" in source
