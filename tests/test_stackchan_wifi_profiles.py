# -*- coding: utf-8 -*-
"""**複数の網を持つ表を、実際にコンパイルして確かめる。**

⛔ **なぜ要るか。** 2026-11-08 まで、この体は `esp_wifi_set_config` が保つ
**ひとつの設定**しか持てなかった。別の場所で `bench wifi join` すれば
**前の網は消えた**——持ち運ぶたびに、両端でパスワードを打ち直すことになる。
⇒ **表を作った。** 保存形式、追加・更新・削除、順番、そして
**どの試行がどの行を訊くか**を、ここで当てる。

## 何を確かめるか

1. **表**——追加は末尾、同じ SSID は**その場で更新**、満杯は拒否、
   32 文字の SSID は通り 33 は通らない、63 文字の psk は通り 64 は通らない。
2. **順番**——`remove` の後も残りは元の順で、`index_for` は
   **1 始まりの試行**を `tries` ごとに行送りする。
3. **保存形式**——往復して同じ表に戻り、壊れた blob
   （版が違う・切れている・行数が多い・NUL が無い）は**丸ごと拒否**される。
   ⛔ **半端に読んだ表を試すと、誰も打っていないパスワードで繋ぎにいく。**
4. **配線**——`wifi.cpp` が NVS の名前空間を持ち、ドライバの1組を
   最初の行として取り込み、`index_for` で行を回すことをソースから読む。

## ⛔ このファイルが確かめないこと

- **`wifi.cpp` はビルドしない。** ESP-IDF を要求するのでここでは走らない。
- **機体にもネットワークにも何も届かない。** 本当に2つの場所で繋がるかは、
  **2つの場所で測る以外に道が無い。**
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
SOURCE = MAIN / "wifi_profiles.cpp"
HEADER = MAIN / "wifi_profiles.h"
WIFI = MAIN / "wifi.cpp"
CONSOLE = MAIN / "main.cpp"
CMAKE = MAIN / "CMakeLists.txt"

COMPILER = shutil.which("clang++") or shutil.which("g++")

needs_compiler = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——判定は走らせられない",
)

#: **表を受け取り、答えを一つ出す器。** 状態は一つのプロセスの中だけに置く。
HARNESS = r"""
#include "wifi_profiles.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

void Dump(const wifi_profiles::Table& table) {
  std::printf("count=%u", static_cast<unsigned>(table.count));
  for (uint8_t i = 0; i < table.count; ++i) {
    std::printf(" [%s|%s]", table.rows[i].ssid, table.rows[i].psk);
  }
  std::printf("\n");
}

void DumpAdd(wifi_profiles::Add value) {
  switch (value) {
    case wifi_profiles::Add::kAdded: std::printf("added "); break;
    case wifi_profiles::Add::kUpdated: std::printf("updated "); break;
    case wifi_profiles::Add::kFull: std::printf("full "); break;
    case wifi_profiles::Add::kBadSsid: std::printf("badssid "); break;
    case wifi_profiles::Add::kBadPsk: std::printf("badpsk "); break;
  }
}

//: "ssid:psk" -> two NUL-terminated pieces inside `buffer`. A token with no
//: colon is an ssid with an empty psk, which is an open network.
void Split(char* token, char** ssid, char** psk) {
  char* colon = std::strchr(token, ':');
  if (colon == nullptr) {
    *ssid = token;
    *psk = token + std::strlen(token);
    return;
  }
  *colon = 0;
  *ssid = token;
  *psk = colon + 1;
}

void PrintHex(const uint8_t* data, std::size_t length) {
  for (std::size_t i = 0; i < length; ++i) {
    std::printf("%02x", data[i]);
  }
}

int HexValue(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

//: Hex text -> bytes. Answers false on an odd or non-hex string so a test
//: cannot compare against a blob it did not really describe.
bool ParseHex(const char* text, uint8_t* out, std::size_t capacity,
              std::size_t* length) {
  const std::size_t text_length = std::strlen(text);
  if (text_length % 2 != 0 || text_length / 2 > capacity) return false;
  for (std::size_t i = 0; i < text_length / 2; ++i) {
    const int high = HexValue(text[i * 2]);
    const int low = HexValue(text[i * 2 + 1]);
    if (high < 0 || low < 0) return false;
    out[i] = static_cast<uint8_t>(high * 16 + low);
  }
  *length = text_length / 2;
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc == 2 && std::strcmp(argv[1], "bounds") == 0) {
    std::printf("%u %zu %zu %zu\n", static_cast<unsigned>(wifi_profiles::kMax),
                wifi_profiles::kSsidMax, wifi_profiles::kPskMax,
                wifi_profiles::kEncodedMax);
    return 0;
  }

  if (argc == 6 && std::strcmp(argv[1], "indexfor") == 0) {
    std::printf("%u\n", static_cast<unsigned>(wifi_profiles::index_for(
        static_cast<uint8_t>(std::atoi(argv[2])),
        static_cast<uint8_t>(std::atoi(argv[3])),
        static_cast<uint32_t>(std::strtoul(argv[4], nullptr, 10)),
        static_cast<uint32_t>(std::strtoul(argv[5], nullptr, 10)))));
    return 0;
  }

  if (argc >= 2 && std::strcmp(argv[1], "run") == 0) {
    wifi_profiles::Table table;
    wifi_profiles::clear(table);
    for (int i = 2; i < argc; ++i) {
      char token[256];
      std::strncpy(token, argv[i], sizeof(token) - 1);
      token[sizeof(token) - 1] = 0;
      char* verb = token;
      char* rest = std::strchr(token, ':');
      if (rest == nullptr) {
        std::printf("op? %s\n", token);
        continue;
      }
      *rest = 0;
      ++rest;

      if (std::strcmp(verb, "add") == 0 || std::strcmp(verb, "addnil") == 0) {
        char* ssid = nullptr;
        char* psk = nullptr;
        Split(rest, &ssid, &psk);
        const wifi_profiles::Add result = wifi_profiles::add(
            table, ssid, std::strcmp(verb, "addnil") == 0 ? nullptr : psk);
        DumpAdd(result);
        Dump(table);
      } else if (std::strcmp(verb, "remove") == 0) {
        std::printf("%d ", wifi_profiles::remove(table, rest) ? 1 : 0);
        Dump(table);
      } else if (std::strcmp(verb, "index") == 0) {
        std::printf("%d\n", wifi_profiles::index_of(table, rest));
      } else {
        std::printf("op? %s\n", verb);
      }
    }
    return 0;
  }

  if (argc >= 2 && std::strcmp(argv[1], "enc") == 0) {
    wifi_profiles::Table table;
    wifi_profiles::clear(table);
    for (int i = 2; i < argc; ++i) {
      char token[256];
      std::strncpy(token, argv[i], sizeof(token) - 1);
      token[sizeof(token) - 1] = 0;
      char* ssid = nullptr;
      char* psk = nullptr;
      Split(token, &ssid, &psk);
      wifi_profiles::add(table, ssid, psk);
    }
    uint8_t blob[wifi_profiles::kEncodedMax];
    const std::size_t length =
        wifi_profiles::encode(table, blob, sizeof(blob));
    if (length == 0) {
      std::printf("REFUSED\n");
      return 0;
    }
    std::printf("OK %zu ", length);
    PrintHex(blob, length);
    std::printf("\n");
    return 0;
  }

  if (argc >= 3 && std::strcmp(argv[1], "encsmall") == 0) {
    wifi_profiles::Table table;
    wifi_profiles::clear(table);
    for (int i = 3; i < argc; ++i) {
      char token[256];
      std::strncpy(token, argv[i], sizeof(token) - 1);
      token[sizeof(token) - 1] = 0;
      char* ssid = nullptr;
      char* psk = nullptr;
      Split(token, &ssid, &psk);
      wifi_profiles::add(table, ssid, psk);
    }
    uint8_t blob[wifi_profiles::kEncodedMax];
    const std::size_t capacity =
        static_cast<std::size_t>(std::strtoul(argv[2], nullptr, 10));
    const std::size_t length = wifi_profiles::encode(table, blob, capacity);
    std::printf("%zu\n", length);
    return 0;
  }

  if (argc == 3 && std::strcmp(argv[1], "dec") == 0) {
    uint8_t blob[512];
    std::size_t length = 0;
    if (!ParseHex(argv[2], blob, sizeof(blob), &length)) {
      std::printf("BADHEX\n");
      return 0;
    }
    wifi_profiles::Table table;
    wifi_profiles::clear(table);
    //: A sentinel row, to prove a refused decode leaves the table alone.
    std::strcpy(table.rows[0].ssid, "untouched");
    table.count = 1;
    if (!wifi_profiles::decode(table, blob, length)) {
      std::printf("REFUSED count=%u first=%s\n",
                  static_cast<unsigned>(table.count), table.rows[0].ssid);
      return 0;
    }
    std::printf("OK ");
    Dump(table);
    return 0;
  }

  return 100;
}
"""


@pytest.fixture(scope="module")
def runner(tmp_path_factory) -> pathlib.Path:
    if COMPILER is None:  # pragma: no cover - guarded by the mark as well
        pytest.skip("no C++ compiler")
    directory = tmp_path_factory.mktemp("wifi-profiles")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "profiles"
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
class TestTheTable:
    """**どの網が、どの順で入るか。**"""

    def test_the_bounds_are_the_header_s_own_numbers(self, runner):
        #: kRowBytes = 33 + 64 = 97; 2 + 4 × 97 = 390.
        assert call(runner, "bounds") == "4 32 63 390"

    def test_a_new_network_goes_to_the_end(self, runner):
        assert call(runner, "run", "add:home:one", "add:cafe:two") == (
            "added count=1 [home|one]\n"
            "added count=2 [home|one] [cafe|two]"
        )

    def test_the_same_ssid_is_updated_in_place(self, runner):
        # ⚠️ 場所は順番である。打ち直したパスワードは、新しい網ではない。
        assert call(runner, "run", "add:home:one", "add:cafe:two",
                    "add:home:new") == (
            "added count=1 [home|one]\n"
            "added count=2 [home|one] [cafe|two]\n"
            "updated count=2 [home|new] [cafe|two]"
        )

    def test_a_fifth_network_is_refused(self, runner):
        out = call(runner, "run", "add:a:1", "add:b:2", "add:c:3", "add:d:4",
                   "add:e:5")
        assert out.splitlines()[-1] == "full count=4 [a|1] [b|2] [c|3] [d|4]"

    def test_an_update_still_works_when_full(self, runner):
        out = call(runner, "run", "add:a:1", "add:b:2", "add:c:3", "add:d:4",
                   "add:d:new")
        assert out.splitlines()[-1] == "updated count=4 [a|1] [b|2] [c|3] [d|new]"

    def test_an_empty_ssid_is_refused(self, runner):
        assert call(runner, "run", "add::psk") == "badssid count=0"

    def test_an_ssid_of_32_is_taken_and_33_is_not(self, runner):
        taken = call(runner, "run", "add:" + "s" * 32 + ":p")
        refused = call(runner, "run", "add:" + "s" * 33 + ":p")
        assert taken.startswith("added count=1")
        assert refused == "badssid count=0"

    def test_a_psk_of_63_is_taken_and_64_is_not(self, runner):
        #: ⛔ 64 はドライバの配列の幅であって、文字数ではない。ここで断るのは、
        #: 以前の `join` が 64 を受け取って 63 に切り詰めていたからである。
        taken = call(runner, "run", "add:net:" + "p" * 63)
        refused = call(runner, "run", "add:net:" + "p" * 64)
        assert taken.startswith("added count=1")
        assert refused == "badpsk count=0"

    def test_a_null_psk_is_an_open_network(self, runner):
        assert call(runner, "run", "addnil:open:") == "added count=1 [open|]"

    def test_removing_keeps_the_order_of_the_rest(self, runner):
        assert call(runner, "run", "add:a:1", "add:b:2", "add:c:3",
                    "remove:b") == (
            "added count=1 [a|1]\n"
            "added count=2 [a|1] [b|2]\n"
            "added count=3 [a|1] [b|2] [c|3]\n"
            "1 count=2 [a|1] [c|3]"
        )

    def test_removing_a_stranger_answers_false(self, runner):
        assert call(runner, "run", "add:a:1", "remove:zzz").splitlines()[-1] == \
            "0 count=1 [a|1]"

    def test_index_finds_a_row_and_misses_the_rest(self, runner):
        assert call(runner, "run", "add:a:1", "add:b:2", "index:b",
                    "index:zzz").splitlines()[-2:] == ["1", "-1"]


@needs_compiler
class TestTheRotation:
    """**どの試行が、どの行を訊くか。**"""

    def test_one_row_is_never_left(self, runner):
        for attempt in ("1", "2", "3", "4", "99"):
            assert call(runner, "indexfor", "1", "0", attempt, "2") == "0"

    def test_two_tries_per_row_then_the_next(self, runner):
        #: tries=2, start=0, count=2: 1–2 → 0, 3–4 → 1, 5–6 → 0.
        assert [call(runner, "indexfor", "2", "0", a, "2")
                for a in ("1", "2", "3", "4", "5", "6")] == \
            ["0", "0", "1", "1", "0", "0"]

    def test_the_turn_wraps_from_the_last_row(self, runner):
        assert [call(runner, "indexfor", "2", "1", a, "2")
                for a in ("1", "2", "3", "4")] == ["1", "1", "0", "0"]

    def test_three_rows_move_one_at_a_time(self, runner):
        assert [call(runner, "indexfor", "3", "0", a, "2")
                for a in ("1", "3", "5", "7")] == ["0", "1", "2", "0"]

    def test_an_empty_table_answers_zero(self, runner):
        assert call(runner, "indexfor", "0", "0", "5", "2") == "0"

    def test_attempt_zero_is_the_starting_row(self, runner):
        assert call(runner, "indexfor", "2", "1", "0", "2") == "1"

    def test_no_tries_means_stay_put(self, runner):
        assert call(runner, "indexfor", "2", "0", "99", "0") == "0"


@needs_compiler
class TestTheBlob:
    """**保存形式が、書いた表をそのまま返すか。**"""

    def test_a_round_trip_returns_the_same_table(self, runner):
        out = call(runner, "enc", "home:one", "cafe:two")
        _, length, blob = out.split()
        assert int(length) == 2 + 2 * 97
        assert call(runner, "dec", blob) == \
            "OK count=2 [home|one] [cafe|two]"

    def test_an_empty_table_round_trips(self, runner):
        out = call(runner, "enc")
        assert out == "OK 2 0100"
        assert call(runner, "dec", "0100") == "OK count=0"

    def test_a_truncated_blob_is_refused_and_leaves_the_table_alone(self, runner):
        out = call(runner, "enc", "home:one", "cafe:two")
        _, _, blob = out.split()
        truncated = blob[:-10]
        assert call(runner, "dec", truncated) == \
            "REFUSED count=1 first=untouched"

    def test_an_unknown_version_is_refused(self, runner):
        out = call(runner, "enc", "home:one")
        _, _, blob = out.split()
        wrong = "02" + blob[2:]
        assert call(runner, "dec", wrong).startswith("REFUSED")

    def test_a_count_past_the_maximum_is_refused(self, runner):
        #: version 1, count 5, and not a byte of rows.
        assert call(runner, "dec", "0105").startswith("REFUSED")

    def test_a_slot_with_no_nul_is_refused(self, runner):
        #: version 1, count 1, 97 bytes of 'A' — no NUL in the ssid slot.
        assert call(runner, "dec", "0101" + "41" * 97).startswith("REFUSED")

    def test_a_buffer_too_small_is_a_refusal_not_an_empty_table(self, runner):
        #: one row is 2 + 97 = 99 bytes; 98 is a row that would not fit.
        assert call(runner, "encsmall", "98", "home:one") == "0"
        assert call(runner, "encsmall", "99", "home:one") == "99"


class TestTheWiring:
    """**配線をソースから読む。** ⛔ これはコンパイルではない。"""

    def test_the_table_has_a_namespace_of_its_own(self):
        text = WIFI.read_text(encoding="utf-8")
        assert 'kProfilesNamespace[] = "ekl_wifi"' in text
        assert 'kProfilesKey[] = "profiles"' in text

    def test_the_drivers_one_network_is_seeded_not_asked_for_again(self):
        text = WIFI.read_text(encoding="utf-8")
        assert "esp_wifi_get_config(WIFI_IF_STA" in text
        assert "RememberProfile(ssid, psk)" in text

    def test_the_retry_task_rotates_by_the_table_s_rule(self):
        text = WIFI.read_text(encoding="utf-8")
        assert "wifi_profiles::index_for(" in text
        assert "g_epoch != epoch" in text

    def test_the_console_can_add_and_forget(self):
        text = CONSOLE.read_text(encoding="utf-8")
        assert "wifi_probe::add(ssid, psk)" in text
        assert "wifi_probe::forget(ssid)" in text
        assert "bench wifi add <ssid> [psk]" in text
        assert "bench wifi forget <ssid>" in text

    def test_the_module_is_in_the_build(self):
        assert '"wifi_profiles.cpp"' in CMAKE.read_text(encoding="utf-8")

    def test_no_psk_is_printed_in_the_wifi_source(self):
        #: ⛔ 表は psk を運ぶ。運んだ先で印刷しないことを、印刷の綴りで読む。
        text = WIFI.read_text(encoding="utf-8")
        assert 'printf("wifi: trying \\"%s\\" (%u of %u)\\n", profile.ssid' in text
        assert "profile.psk)" not in text
