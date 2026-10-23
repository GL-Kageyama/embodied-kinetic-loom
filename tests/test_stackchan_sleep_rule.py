# -*- coding: utf-8 -*-
"""**ホストが居なくなったとき、体がいつ眠り、いつ起きるかを、実際にコンパイルして確かめる。**

⛔ **なぜ要るか。** Mac は夜に落ち、板は壁コンセント給電でバッテリーを積んでいる。
2026-10-20 の実測では **USB を抜いたまま 9.5 時間**、画面まで生きた。⇒ **Mac の電源を
切っても板の電源は切れない。** これまで著者が手でスイッチを切っていた。

⚠️ **合図は「活動」ではなく「リンク」である。** 電源の入った Mac は、何もしていなくても
dial の接続を保つ。活動で眠る規則にすると、静かな午後にホストが起きているのに体が眠る。

## このファイルが確かめること

- **居れば即座に起きる**（眠っていた場合も）。
- **居なくなってから `after_us` までは眠らない**——Wi-Fi の瞬断やデーモンの再起動は
  その窓を秒で通り過ぎる（0.19.74 は再 dial を 0.3–4 秒と測った）。
- **`after_us` に達したら眠る**。境界そのものを確かめる。
- **窓の内側では状態が動かない**——眠っている体は、短い不在では起きない。
- **負の不在では眠らない**（時計をまだ読んでいないだけである）。
- 画面上の明るさの規則が **DLDO1 の1ビット**（`0x90` の bit 7）であり、他のレールを
  巻き込まないこと。⛔ `0x99` の電圧を下げるだけでは、パネルは光ったままである。

## ⛔ このファイルが確かめないこと

- **`main.cpp` も `display.cpp` もビルドしない。** IDF を要求するので、ここでは走らない。
  **確かめるのは `sleep_rule.cpp` の1つの関数と、源の綴りだけである。**
- **機体にもネットワークにも何も届かない。**
- ⚠️ **「暗くなった」はここでは確かめられない。** レジスタが書けたことと、目が暗いと
  言うことは別である——著者の目が決める。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE = REPO_ROOT / "projects" / "stackchan-firmware"
MAIN = FIRMWARE / "main"
SOURCE = MAIN / "sleep_rule.cpp"

COMPILER = shutil.which("clang++") or shutil.which("g++")

pytestmark = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——眠りの規則は走らせられない",
)

#: **1つの関数を、そのまま argv から呼ぶ器。** ⛔ 判定を器の中に書き写さない。
HARNESS = r"""
#include "sleep_rule.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(int argc, char** argv) {
  if (argc < 5) {
    return 100;
  }
  const sleep_rule::State now =
      std::atoi(argv[1]) != 0 ? sleep_rule::State::kAsleep : sleep_rule::State::kAwake;
  const bool present = std::atoi(argv[2]) != 0;
  const auto absent = static_cast<int64_t>(std::atoll(argv[3]));
  const auto after = static_cast<int64_t>(std::atoll(argv[4]));
  const sleep_rule::State next = sleep_rule::next(now, present, absent, after);
  std::printf("%s\n", next == sleep_rule::State::kAsleep ? "asleep" : "awake");
  return 0;
}
"""


@pytest.fixture(scope="module")
def rule(tmp_path_factory) -> pathlib.Path:
    directory = tmp_path_factory.mktemp("sleep-rule")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "rule"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-I", str(MAIN), "-o", str(binary),
         str(harness), str(SOURCE)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"
    return binary


def state(rule: pathlib.Path, now: str, present: bool, absent_us: int, after_us: int) -> str:
    done = subprocess.run(
        [str(rule), "1" if now == "asleep" else "0", "1" if present else "0",
         str(absent_us), str(after_us)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    return done.stdout.strip()


AFTER = 5 * 60 * 1000 * 1000  # 5 minutes, the number `main.cpp` chooses


# ---------------------------------------------------------------------------
# 居れば起きる。⛔ **これが非対称の半分である。**
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("now", ["awake", "asleep"])
def test_a_host_that_is_there_wakes_the_body(rule, now):
    """**接続が在れば、時計が何を言おうと起きている。**"""
    assert state(rule, now, True, 10**12, AFTER) == "awake"


def test_a_line_on_either_wire_counts_as_a_host(rule):
    """⚠️ **不在が窓の内側なら、居るのと同じ**——`RunLine` が不在の時計を戻す。"""
    assert state(rule, "awake", False, 0, AFTER) == "awake"


# ---------------------------------------------------------------------------
# 居なければ、窓のあとで眠る。
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("absent_us", [0, 1, 60 * 10**6, AFTER - 1])
def test_a_short_absence_does_not_darken_the_room(rule, absent_us):
    """⛔ **Wi-Fi の瞬断とデーモンの再起動は、この窓を秒で通り過ぎる。**

    0.19.74 の実測は 0.3–4 秒で再 dial した。⚠️ 30 秒の天井より長い窓にしてある。
    """
    assert state(rule, "awake", False, absent_us, AFTER) == "awake"


def test_the_window_ends_exactly_at_the_boundary(rule):
    """**`>=` である。** 境界の1マイクロ秒手前と、境界そのものを分けて確かめる。"""
    assert state(rule, "awake", False, AFTER - 1, AFTER) == "awake"
    assert state(rule, "awake", False, AFTER, AFTER) == "asleep"


def test_asleep_stays_asleep_inside_the_window(rule):
    """⚠️ **眠っている体は、短い不在では起きない。** 起きるのは接続だけである。"""
    assert state(rule, "asleep", False, 1, AFTER) == "asleep"
    assert state(rule, "asleep", False, AFTER + 10**9, AFTER) == "asleep"


def test_a_negative_absence_is_not_forever(rule):
    """⛔ **時計をまだ読んでいないだけの負の値で、体は眠らない。**"""
    assert state(rule, "awake", False, -1, AFTER) == "awake"
    assert state(rule, "awake", False, -10**12, AFTER) == "awake"


# ---------------------------------------------------------------------------
# 源の綴り。⛔ **規則に検査が無いのは、このリポジトリ自身の欠陥の定義である。**
# ---------------------------------------------------------------------------


def test_the_backlight_is_one_bit_of_the_ldo_register():
    """**DLDO1 は `0x90` の bit 7。** 他のレールを巻き込まない。

    ⚠️ `XPowersLib` の `enableDLDO1` は `0x90` の bit 7 を立てる。ベンダーの
    `0xBF` は bit 7 が立ったままなので、ここだけを落とす。
    """
    header = (MAIN / "display.h").read_text(encoding="utf-8")
    assert "bool backlight(bool on);" in header
    source = (MAIN / "display.cpp").read_text(encoding="utf-8")
    start = source.index("bool display::backlight")
    body = source[start:source.index("\n}\n", start)]
    assert "0x90" in body, "バックライトが LDO enable レジスタを見ていない"
    assert "0x80" in body, "bit 7 が DLDO1 ではない"
    assert "0x7F" in body, "落とすのが bit 7 だけではない"
    assert "0x99" not in body, "電圧を下げるだけでは、パネルは光ったままである"


def test_the_sleep_clock_is_the_link_and_the_wires():
    """**主ループが `SleepWatch` を呼び、`RunLine` が不在の時計を戻す。**"""
    source = (MAIN / "main.cpp").read_text(encoding="utf-8")
    assert "SleepWatch();" in source
    assert "dial::up()" in source
    assert "sleep_rule::next(" in source
    assert "kAsleepAfterUs = 5LL * 60 * 1000 * 1000" in source
    assert "NotePresent();" in source


def test_a_line_wakes_the_body_before_it_is_dispatched():
    """⛔ **暗い体に1行が届いたら、その行を捌く前に目を開ける。**

    ⚠️ `RunLine` の中の位置まで見る——`WakeNow` が `g_body` を取った**後**に
    あったら、払い出しの途中で画面が戻ることになる。そして `bench sleep` が
    在ること: 目で見るための入口が無ければ、規則は機械の上で確かめられない。
    """
    source = (MAIN / "main.cpp").read_text(encoding="utf-8")
    start = source.index("void RunLine(const char* line, int length) {")
    body = source[start:source.index("\n}\n", start)]
    assert "WakeNow();" in body, "1行が体を起こさない"
    assert body.index("WakeNow();") < body.index("xSemaphoreTake(g_body"), (
        "WakeNow が払い出しの後にある——暗いまま捌くことになる"
    )
    assert 'std::strncmp(args, "sleep", 5)' in source, "`bench sleep` が無い"
    assert "HoldDark();" in source, "`bench sleep` が保持を取らない——主ループが20 msで起こす"
    assert "kForcedHoldMs" in source, "保持の長さが名を持っていない"


def test_a_half_open_socket_is_noticed():
    """⛔ **`kickstart -k` の片側だけ閉じた接続を、25 秒で死んだと読む。**

    2026-10-21 の実測: `FIN_WAIT_1` のまま ACK が来ず、`DialTask` に読み取りの
    時限が無い。⚠️ この規則が無いと、体は一晩中点いたままになる。
    """
    source = (MAIN / "dial.cpp").read_text(encoding="utf-8")
    assert "SO_KEEPALIVE" in source
    assert "TCP_KEEPIDLE" in source
    assert "TCP_KEEPCNT" in source
    defaults = (FIRMWARE / "sdkconfig.defaults").read_text(encoding="utf-8")
    assert "CONFIG_LWIP_TCP_KEEPALIVE=y" in defaults, (
        "lwIP の既定は時間単位である——この行が無いと keepalive は測った間隔で走らない"
    )
