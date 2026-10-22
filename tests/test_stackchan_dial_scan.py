# -*- coding: utf-8 -*-
"""**名指しの住所が黙ったとき、板がどの住所を、どの順に試すかを、実際にコンパイルして確かめる。**

⛔ **なぜ要るか。** 0.19.74 までの dialer は住所を1つしか知らなかった。そしてその住所は
**1つのルータの DHCP リースの事実**であった。2026-10-23、Mac の再起動が住所を
`192.168.0.103` から `192.168.0.106` へ動かし、**板は `.103` を叩き続け、デーモンの
ログは `"err": "nobody"` で埋まり、板の側には何も言うものが無かった。**

⇒ **板は、居場所を仮定するのをやめる。** ⚠️ ただし**走査ではない**——候補は
**名乗り（`loom`）を返したときだけ**受け入れられる。⛔ 名乗りが無ければ、掃き出しは
**3333 を持つ何者でも体を動かす**ことになる（回線は認証されていない、住所は身元ではない）。

## このファイルが確かめること

- 名指しの住所が**最初**であること。
- そのあとが**近い順**であること（`.+1`, `.-1`, `.+2`, `.-2`, …）。
- `.0` と `.255` を**ホストとして試さない**こと。
- /24 のホストが**ちょうど1回ずつ**入っていること。
- 住所でない文字列では**1つも返さない**こと（勝手に歩き出さない）。
- `loom` の判定が**語**であること（`loomish` は違う）。

## ⛔ このファイルが確かめないこと

- **`dial.cpp` はビルドしない。** lwIP と FreeRTOS を要求するので、ここでは走らない。
  **確かめるのは `dial_scan.cpp` の3つの関数だけである。**
- **機体にもネットワークにも何も届かない。** ここにソケットは無い。
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
SOURCE = MAIN / "dial_scan.cpp"

COMPILER = shutil.which("clang++") or shutil.which("g++")

pytestmark = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——走査の順序は走らせられない",
)

#: **3つの関数を、そのまま argv から呼ぶ器。** ⛔ 判定を器の中に書き写さない。
HARNESS = r"""
#include "dial_scan.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(int argc, char** argv) {
  if (argc < 2) {
    return 100;
  }
  if (std::strcmp(argv[1], "candidates") == 0) {
    if (argc < 3) {
      return 101;
    }
    uint32_t out[dial_scan::kMaxCandidates];
    const int count =
        dial_scan::candidates(argv[2], out, dial_scan::kMaxCandidates);
    std::printf("%d\n", count);
    for (int i = 0; i < count; ++i) {
      char text[20];
      if (dial_scan::format(out[i], text, sizeof(text)) == 0) {
        std::printf("?\n");
        continue;
      }
      std::printf("%s\n", text);
    }
    return 0;
  }
  if (std::strcmp(argv[1], "is_loom") == 0) {
    if (argc < 3) {
      return 102;
    }
    const int length = static_cast<int>(std::strlen(argv[2]));
    std::printf("%d\n", dial_scan::is_loom(argv[2], length) ? 1 : 0);
    return 0;
  }
  if (std::strcmp(argv[1], "format") == 0) {
    if (argc < 4) {
      return 103;
    }
    const unsigned long address = std::strtoul(argv[2], nullptr, 10);
    char text[20];
    const int length =
        dial_scan::format(static_cast<uint32_t>(address), text, std::atoi(argv[3]));
    std::printf("%d %s\n", length, length > 0 ? text : "");
    return 0;
  }
  if (std::strcmp(argv[1], "sweep") == 0) {
    if (argc < 6) {
      return 105;
    }
    const bool routed = std::atoi(argv[2]) != 0;
    const auto now = static_cast<int64_t>(std::atoll(argv[3]));
    const auto last = static_cast<int64_t>(std::atoll(argv[4]));
    const auto every = static_cast<int64_t>(std::atoll(argv[5]));
    switch (dial_scan::sweep_when(routed, now, last, every)) {
      case dial_scan::Sweep::kNow:
        std::printf("now\n");
        break;
      case dial_scan::Sweep::kNoRoute:
        std::printf("no-route\n");
        break;
      case dial_scan::Sweep::kTooSoon:
        std::printf("too-soon\n");
        break;
    }
    return 0;
  }
  return 104;
}
"""


@pytest.fixture(scope="module")
def sweep(tmp_path_factory) -> pathlib.Path:
    directory = tmp_path_factory.mktemp("dial-scan")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "scan"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-I", str(MAIN), "-o", str(binary),
         str(harness), str(SOURCE)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"
    return binary


def candidates(sweep: pathlib.Path, known: str) -> list[str]:
    done = subprocess.run([str(sweep), "candidates", known],
                          capture_output=True, text=True)
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    lines = done.stdout.split("\n")
    count = int(lines[0])
    found = [line for line in lines[1:] if line]
    assert len(found) == count, f"数を言ったのに {count} 個ではなく {len(found)} 個"
    return found


def is_loom(sweep: pathlib.Path, line: str) -> bool:
    done = subprocess.run([str(sweep), "is_loom", line],
                          capture_output=True, text=True)
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    return done.stdout.strip() == "1"


# ---------------------------------------------------------------------------
# 順序。⚠️ **近い順であることが、掃き出しを短くする唯一の理由である。**
# ---------------------------------------------------------------------------


def test_the_named_address_is_tried_first(sweep):
    """⛔ **コンソールが名指しした住所を、最初に試す。** 掃き出しは最後の手段である。"""
    assert candidates(sweep, "192.168.0.103")[0] == "192.168.0.103"


def test_the_sweep_walks_outward_from_the_named_address(sweep):
    """⚠️ **`.+1`, `.-1`, `.+2`, `.-2`, …**——2つ隣へ動いたホストは3回で見つかる。

    ⚠️ 2026-10-23 の Mac は `.103` から `.106` へ動いた。この順序なら4回目である。
    """
    assert candidates(sweep, "192.168.0.103")[:7] == [
        "192.168.0.103",
        "192.168.0.104", "192.168.0.102",
        "192.168.0.105", "192.168.0.101",
        "192.168.0.106", "192.168.0.100",
    ]


def test_the_network_and_the_broadcast_are_not_hosts(sweep):
    """⛔ **`.0` と `.255` は住所ではない。** 試せば、掃き出しは自分自身に訊くことになる。"""
    found = candidates(sweep, "192.168.0.103")
    assert "192.168.0.0" not in found
    assert "192.168.0.255" not in found


def test_every_host_of_the_slash_twenty_four_appears_once(sweep):
    """⚠️ **254 = 256 - `.0` - `.255`。** 数え上げなので、数そのものを確かめる。"""
    found = candidates(sweep, "192.168.0.103")
    assert len(found) == 254
    assert len(set(found)) == 254


def test_a_string_that_is_not_an_address_sweeps_nothing(sweep):
    """⛔ **名指しが住所でなければ、1つも返さない。** 勝手に歩き出さないためである。"""
    for text in ("", "loom", "192.168.0", "192.168.0.103x", "192.168.0.300",
                 "192.168.0.1.2"):
        assert candidates(sweep, text) == [], f"{text!r} で歩き出した"


def test_the_walk_survives_both_ends_of_the_subnet(sweep):
    """⚠️ **端の住所でも、範囲の外へ出ない。**"""
    found = candidates(sweep, "192.168.0.1")
    assert found[:3] == ["192.168.0.1", "192.168.0.2", "192.168.0.3"]
    assert "192.168.0.0" not in found
    found = candidates(sweep, "192.168.0.254")
    assert found[:2] == ["192.168.0.254", "192.168.0.253"]
    assert "192.168.0.255" not in found


# ---------------------------------------------------------------------------
# 名乗り。⛔ **なければ、3333 を持つ何者でも体を動かす。**
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("line", ["loom", "loom ", "loom stackchan"])
def test_the_hosts_greeting_is_a_loom_word(sweep, line):
    """✅ **ホストは `loom` を最初の1行に書く**（`Link.accept`）。"""
    assert is_loom(sweep, line) is True


@pytest.mark.parametrize("line", ["", "loomish", " loom", "LOOM", "hello", "loomx"])
def test_another_word_is_not_this_host(sweep, line):
    """⛔ **接頭辞では一致させない。** `loomish` を名乗る何かは、このホストではない。"""
    assert is_loom(sweep, line) is False


# ---------------------------------------------------------------------------
# 綴り。⚠️ **切れた住所は、別のどこかへの住所である。**
# ---------------------------------------------------------------------------


def test_an_address_round_trips(sweep):
    """⚠️ `(address >> 24) & 0xFF` の順序を、綴りで確かめる。"""
    done = subprocess.run([str(sweep), "format", str(0xC0A80067), "20"],
                          capture_output=True, text=True)
    assert done.returncode == 0
    length, text = done.stdout.strip().split(" ", 1)
    assert text == "192.168.0.103"
    assert int(length) == len(text)


def test_a_buffer_too_small_returns_zero_and_not_a_cut_address(sweep):
    """⛔ **`192.168.0.` は住所ではない。** 0 を返し、綴りを信じさせない。"""
    done = subprocess.run([str(sweep), "format", str(0xC0A80067), "8"],
                          capture_output=True, text=True)
    assert done.returncode == 0
    assert done.stdout.strip() == "0"


# ---------------------------------------------------------------------------
# 掃き出しを起こしてよい瞬間。⛔ **2026-10-23、これが無いまま板は404の住所を
# 「3秒足らずで試した」**——経路が無いだけで、住所は何も悪くなかった。
# ---------------------------------------------------------------------------


def ask(sweep_binary: pathlib.Path, routed: bool, now: int, last: int,
        every: int = 30_000_000) -> str:
    done = subprocess.run(
        [str(sweep_binary), "sweep", "1" if routed else "0", str(now), str(last),
         str(every)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    return done.stdout.strip()


def test_a_body_without_a_route_does_not_doubt_the_address(sweep):
    """⛔ **経路が無いなら、住所の一覧は何も語らない。**

    ⚠️ 起動直後、`dial::begin()` は電波が繋がる前に走る。そのとき `connect` は
    **0 ms で `ENETUNREACH`** を返す——**相手が居ないのではない、経路が無い**。
    ⇒ **期限が来ていても、掃き出しは走らない。**
    """
    assert ask(sweep, False, 100, 0) == "no-route"
    assert ask(sweep, False, 60_000_000, 1) == "no-route"


def test_the_first_failure_with_a_route_is_due(sweep):
    """✅ **一度も掃いていないなら、期限は来ている。**"""
    assert ask(sweep, True, 100, 0) == "now"


def test_a_second_sweep_waits_for_the_interval(sweep):
    """⚠️ **30 秒は選んだ数である**——測った数ではない。**それでも、失敗のたびに
    254 の住所を叩くのは、回線ではなくこちらの焦りを測っている。**"""
    every = 30_000_000
    assert ask(sweep, True, 1 + every, 1, every) == "now"        # ちょうど期限
    assert ask(sweep, True, every, 1, every) == "too-soon"       # 1 µs 早い
    assert ask(sweep, True, 1 + every * 2, 1, every) == "now"    # 間隔を過ぎた
    assert ask(sweep, True, 100_000_000, 1, every * 4) == "too-soon"


def test_the_clock_going_backwards_is_not_a_reason_to_sweep(sweep):
    """⛔ **時計は状態である。** 戻った値を「期限が来た」と読まない。"""
    assert ask(sweep, True, 10, 50_000_000) == "too-soon"
