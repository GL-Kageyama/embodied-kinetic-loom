# -*- coding: utf-8 -*-
"""**切れた接続を、この体がもう一度求めるかどうかを、実際にコンパイルして確かめる。**

⛔ **なぜ要るか。** 2026-10-21 まで `main/wifi.cpp` は
`WIFI_EVENT_STA_START` で一度だけ `esp_wifi_connect()` を呼び、
`WIFI_EVENT_STA_DISCONNECTED` は理由を印刷して返っていた。**切れた接続は、
切れたままだった。** その日の実測——板は電源が入って `bench pos` に答え
（yaw 492 / pitch 773）、画面は暗く、`not associated, no ip` のまま 12 分
そこにいた。**dial は 18 回、接続は 0。**
⇒ **待ち時間の規則は `main/wifi_retry.h` に一文で置き、ここで数を当てる。**

## 何を確かめるか

1. **`wifi_retry::next`**——最初の待ちから倍々に伸び、最長で止まる。
   ⚠️ **天井を掛け算の前に置く**: `uint32_t` の天井近くで掛ければ巻き戻り、
   **2 秒ごとの再試行**という、このファイルが避けるために在るものになる。
2. **`wifi_retry::worth_printing`**——最初の三回は名乗り、以後は十回に一度。
   **理由を埋めないためである**（0.19.58 の註と同じ理由）。
3. **配線**——`wifi.cpp` の切断の枝がセマフォを与え、`RetryTask` が
   `esp_wifi_connect()` を呼び、セマフォとタスクが `esp_wifi_start()` より
   前に在る。⛔ **これはソースを読んでいるだけである**（下記）。

## ⛔ このファイルが確かめないこと

- **`wifi.cpp` はビルドしない。** ESP-IDF を要求するのでここでは走らない。
  **確かめるのは `wifi_retry.cpp` の判定と、`wifi.cpp` の配線の読みである。**
  ⇒ **この二つが揃って緑でも、機体が本当に再接続するかは分からない**——
  それは電波を切って待つ以外に測る道が無い。
- **機体にもネットワークにも何も届かない。**
- ⚠️ **コンパイラの無い環境では、判定の側だけを飛ばす**（`skipif`）。
  配線の読みはテキストなので、コンパイラが無くても走る。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN = REPO_ROOT / "projects" / "stackchan-firmware" / "main"
SOURCE = MAIN / "wifi_retry.cpp"
HEADER = MAIN / "wifi_retry.h"
WIFI = MAIN / "wifi.cpp"
CMAKE = MAIN / "CMakeLists.txt"

COMPILER = shutil.which("clang++") or shutil.which("g++")

needs_compiler = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——判定は走らせられない",
)

#: **一文を受け取り、答えを一つ出すだけの器。**
HARNESS = r"""
#include "wifi_retry.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(int argc, char** argv) {
  if (argc == 3 && std::strcmp(argv[1], "next") == 0) {
    std::printf("%u\n", static_cast<unsigned>(
        wifi_retry::next(static_cast<uint32_t>(std::strtoul(argv[2], nullptr, 10)))));
    return 0;
  }
  if (argc == 3 && std::strcmp(argv[1], "print") == 0) {
    std::printf("%d\n", wifi_retry::worth_printing(
        static_cast<uint32_t>(std::strtoul(argv[2], nullptr, 10))) ? 1 : 0);
    return 0;
  }
  if (argc == 2 && std::strcmp(argv[1], "bounds") == 0) {
    std::printf("%u %u\n", static_cast<unsigned>(wifi_retry::kMinMs),
                static_cast<unsigned>(wifi_retry::kMaxMs));
    return 0;
  }
  return 100;
}
"""


@pytest.fixture(scope="module")
def runner(tmp_path_factory) -> pathlib.Path:
    if COMPILER is None:  # pragma: no cover - guarded by the mark as well
        pytest.skip("no C++ compiler")
    directory = tmp_path_factory.mktemp("wifi-retry")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "retry"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-I", str(MAIN), "-o", str(binary),
         str(harness), str(SOURCE)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"
    return binary


def call(runner: pathlib.Path, *args: str) -> str:
    done = subprocess.run([str(runner), *args], capture_output=True, text=True)
    assert done.returncode == 0, f"器が落ちた: {done.returncode} {done.stderr}"
    return done.stdout.strip()


@needs_compiler
class TestTheWait:
    """**どれだけ待つか。**"""

    def test_the_first_wait_is_the_header_s_own_number(self, runner):
        assert call(runner, "bounds") == "2000 30000"

    def test_it_doubles_from_the_first(self, runner):
        # ⚠️ 二倍ずつ、四つ目までは天井より下。ここが崩れれば曲線ではない。
        assert call(runner, "next", "2000") == "4000"
        assert call(runner, "next", "4000") == "8000"
        assert call(runner, "next", "8000") == "16000"

    @pytest.mark.parametrize("asked", ["16000", "20000", "30000", "60000",
                                       "4294967295", "4294967294"])
    def test_it_never_passes_the_longest(self, runner, asked):
        # ⛔ 天井を掛け算の前に置く理由がここに在る。巻き戻れば 30000 ではなく
        #    小さな数が返り、再試行は 2 秒ごとの周回になる。
        assert call(runner, "next", asked) == "30000"

    @pytest.mark.parametrize("asked", ["0", "1", "500", "1999"])
    def test_a_short_wait_is_lifted_to_the_first(self, runner, asked):
        # ⚠️ 短い値は 0 でも最初の待ちになる。曲線の下に穴を空けない。
        assert call(runner, "next", asked) == "2000"

    def test_a_hundred_steps_never_decrease_and_never_exceed(self, runner):
        value = 2000
        seen = [value]
        for _ in range(100):
            value = int(call(runner, "next", str(value)))
            assert 2000 <= value <= 30000
            assert value >= seen[-1]
            seen.append(value)
        # ⇒ 伸びる、そして止まる。両方が一つの列で成り立つ。
        assert seen[0] < seen[-1] == 30000


@needs_compiler
class TestWhatEarnsALine:
    """**どの試行がコンソールに名乗るか。**"""

    @pytest.mark.parametrize("attempt", [1, 2, 3])
    def test_the_first_three_are_printed(self, runner, attempt):
        # ⚠️ 最初の三回が「再試行は在る」「何を待っているか」を言う。
        assert call(runner, "print", str(attempt)) == "1"

    @pytest.mark.parametrize("attempt", [4, 5, 9, 11, 19, 21])
    def test_the_rest_are_not_printed(self, runner, attempt):
        assert call(runner, "print", str(attempt)) == "0"

    @pytest.mark.parametrize("attempt", [10, 20, 100])
    def test_every_tenth_is_printed(self, runner, attempt):
        # ⚠️ 一夜を切れたまま過ごしても、行は数十であって数千ではない。
        assert call(runner, "print", str(attempt)) == "1"

    def test_zero_is_not_an_attempt(self, runner):
        # ⛔ `0 % 10 == 0` は、起きなかった試行に一台分の行を与える。
        assert call(runner, "print", "0") == "0"


class TestTheWiringInTheSource:
    """**`wifi.cpp` がその判定を使っているか。** ⚠️ **これはソースの読みである。**

    ⛔ ビルドしないので、**ここが緑でも `wifi.cpp` がコンパイルすることは
    確かめていない**。確かめるのは、切断の枝がセマフォを与えること、再試行の
    タスクが `esp_wifi_connect()` を呼ぶこと、そしてその二つが
    `esp_wifi_start()` より前に用意されることである。
    """

    @pytest.fixture
    def source(self) -> str:
        return WIFI.read_text(encoding="utf-8")

    @staticmethod
    def section(source: str, opening: str, closing: str) -> str:
        start = source.index(opening)
        end = source.index(closing, start)
        return source[start:end]

    def test_the_disconnect_branch_wakes_the_task(self, source):
        branch = self.section(
            source,
            "} else if (id == WIFI_EVENT_STA_DISCONNECTED) {",
            "void RetryTask(",
        )
        # ⚠️ 三つとも要る。理由を印刷すること（人が読むため）、住所を落とすこと
        #    （待つ側の条件）、そして起こすこと（この欠陥の本体）。
        assert "ReasonName(e->reason)" in branch
        assert "g_have_ip = false" in branch
        assert "xSemaphoreGive(g_dropped)" in branch

    def test_the_retry_task_asks_again(self, source):
        task = self.section(source, "void RetryTask(", "}  // namespace")
        assert "esp_wifi_connect();" in task
        # ⛔ 待ちの数は `wifi_retry` のものであって、ここに書いた数ではない。
        assert "wifi_retry::next(" in task
        assert "wifi_retry::kMinMs" in task
        assert "wifi_retry::worth_printing(" in task

    def test_the_task_is_ready_before_the_radio_starts(self, source):
        # ⚠️ 最初の切断は `esp_wifi_start()` の一秒後に来うる。そのとき
        #    `g_dropped` が null なら、起きるはずの目覚めが床に落ちる。
        semaphore = source.index("xSemaphoreCreateBinary()")
        task = source.index("xTaskCreate(&RetryTask")
        # ⚠️ `"esp_wifi_start()"` を裸で探すと、この順序を説明する註の側に
        #    当たる（2026-10-21 に実際に当たった）。**宣言の字まで含める。**
        start = source.index("if (esp_wifi_start()")
        assert semaphore < task < start

    def test_the_address_sets_the_flag_before_it_prints(self, source):
        handler = self.section(source, "void OnGotIp(", "}  // namespace")
        assert handler.index("g_have_ip = true") < handler.index(
            "wifi: connected ip=%s"
        )

    def test_the_old_comment_is_gone(self, source):
        # ⛔ 「一度だけ、再試行の輪は無し」は、2026-10-21 の欠陥そのものの
        #    言い換えだった。**註が規則を名乗り、規則が欠陥だった。**
        assert "One attempt, and no retry loop" not in source

    def test_the_header_and_the_object_are_named(self):
        assert HEADER.exists() and SOURCE.exists()
        assert "wifi_retry.h" in WIFI.read_text(encoding="utf-8")
        assert "wifi_retry.cpp" in CMAKE.read_text(encoding="utf-8")


def test_the_rule_is_written_once():
    """⚠️ 規則は一文で書かれ、ヘッダに置かれている——この工房の書き方。"""
    header = HEADER.read_text(encoding="utf-8")
    assert "kMinMs" in header and "kMaxMs" in header
    assert "uint32_t next(uint32_t waited_ms);" in header
    assert "bool worth_printing(uint32_t attempt);" in header
