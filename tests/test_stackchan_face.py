# -*- coding: utf-8 -*-
"""**画面の顔が、vendor の既定スキンの形と滑らかさになっていることを、実際に描いて確かめる。**

⛔ **なぜ要るか。** 基板の `face_bitmap.cpp` は、vendor の LVGL 実装
（`skins/default/eyes.cpp` / `mouth.cpp`）の**形と数値を手で写した**ものである。
⚠️ **写しは、黙ってずれる**——ずれたことを、画面を見るまで誰も言わない。
⇒ **このファイルが C++ をコンパイルして走らせ、描かれた画素そのものを訊く。**

訊くのは5つの性質:

- **口は、vendor の既定の棒である**——90 x 6、どの感情でも同じ場所に 540 画素、隙間なし。
- **2つの目は、鏡像である**——vendor は右目に回転の符号を反転させる。
- **目と口の外は、黒である**（`secondaryColor`）。
- **眠い顔の目は、最も閉じている**——重み 35 は 75 より覆われる。
- **縁は滑らかである**——0 でも 255 でもない中間の値を持つ画素が、円の縁に在る。
  ⛔ **これが無ければ、20 px の円は階段である**——一度そうなって、著者が見つけた。

## ⛔ このファイルが確かめないこと

- **パネルには何も届かない。** ここに SPI も I2C も無い。
- **LVGL を走らせて比べてもいない。** 比べているのは vendor の**数値**と、
  この描画器が出す形である。⛔ 数値を写し間違えれば、この検査は緑のまま
  vendor と違う顔を描く——だから数値の出典を `face_bitmap.cpp` に書いてある。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE = REPO_ROOT / "projects" / "stackchan-firmware"
MAIN = FIRMWARE / "main"
BITMAP = MAIN / "face_bitmap.cpp"

COMPILER = shutil.which("clang++") or shutil.which("g++")

pytestmark = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——描画器は走らせられない",
)

#: **各顔について: 明るい画素・中間の画素・指紋・口の画素・左右の目の画素・
#: 鏡像のずれ・決め打ちの画素。** 判定は Python 側で行う。
HARNESS = r"""
#include "command_frame.h"
#include "face_bitmap.h"
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include <vector>

namespace {

int At(const std::vector<uint8_t>& grey, int x, int y) {
  return grey[y * face_bitmap::kWidth + x];
}

int Bright(const std::vector<uint8_t>& grey, int x0, int y0, int x1, int y1) {
  int n = 0;
  for (int y = y0; y <= y1; ++y) {
    for (int x = x0; x <= x1; ++x) {
      n += At(grey, x, y) >= 128;
    }
  }
  return n;
}

int Dim(const std::vector<uint8_t>& grey, int x0, int y0, int x1, int y1) {
  int n = 0;
  for (int y = y0; y <= y1; ++y) {
    for (int x = x0; x <= x1; ++x) {
      const int v = At(grey, x, y);
      n += v > 0 && v < 255;
    }
  }
  return n;
}

}  // namespace

int main() {
  const Face faces[6] = {Face::kNone,   Face::kCurious, Face::kGreeting,
                         Face::kHappy,  Face::kAngry,   Face::kSleepy};
  const char* const names[6] = {"none", "curious", "greeting",
                                "happy", "angry", "sleepy"};
  std::vector<uint8_t> grey(face_bitmap::kBytes);
  for (int i = 0; i < 6; ++i) {
    face_bitmap::render(faces[i], grey.data());

    int bright = 0;
    int partial = 0;
    std::uint32_t hash = 2166136261u;
    for (int b = 0; b < face_bitmap::kBytes; ++b) {
      bright += grey[b] >= 128;
      partial += grey[b] > 0 && grey[b] < 255;
      hash = (hash ^ grey[b]) * 16777619u;
    }

    // The mouth: 90 wide, 6 high, centred at (160, 146). Every pixel is solid.
    int mouth = 0;
    for (int y = 143; y <= 148; ++y) {
      for (int x = 115; x <= 204; ++x) {
        mouth += At(grey, x, y) == 255;
      }
    }
    const int left = Bright(grey, 78, 92, 102, 116);
    const int right = Bright(grey, 218, 92, 242, 116);
    const int eye_edge = Dim(grey, 78, 92, 102, 116) + Dim(grey, 218, 92, 242, 116);

    // Mirror check about the vertical through x = 160. ⚠️ Pixel `x` covers
    // [x, x+1), so its mirror is `319 - x`, not `320 - x` — the off-by-one
    // that put the eyes half a pixel away from the mouth.
    int mismatched = 0;
    for (int y = 92; y <= 116; ++y) {
      for (int x = 78; x <= 102; ++x) {
        mismatched += At(grey, x, y) != At(grey, 319 - x, y);
      }
    }

    // Everything outside the eyes and the mouth must stay black.
    int outside = 0;
    for (int y = 0; y < face_bitmap::kHeight; ++y) {
      for (int x = 0; x < face_bitmap::kWidth; ++x) {
        const bool in_left = x >= 78 && x <= 102 && y >= 92 && y <= 116;
        const bool in_right = x >= 218 && x <= 242 && y >= 92 && y <= 116;
        const bool in_mouth = x >= 115 && x <= 204 && y >= 143 && y <= 148;
        if (!in_left && !in_right && !in_mouth) {
          outside += At(grey, x, y) != 0;
        }
      }
    }

    std::printf("FACE %s\n", names[i]);
    std::printf("BRIGHT %d\n", bright);
    std::printf("PARTIAL %d\n", partial);
    std::printf("HASH %08x\n", hash);
    std::printf("MOUTH %d\n", mouth);
    std::printf("LEFT %d\n", left);
    std::printf("RIGHT %d\n", right);
    std::printf("EYE_EDGE %d\n", eye_edge);
    std::printf("MIRROR_MISMATCH %d\n", mismatched);
    std::printf("OUTSIDE %d\n", outside);

    // Pinned pixels: the lid's weight, read where it shows.
    std::printf("P %d %d %d\n", 90, 96, At(grey, 90, 96));
    std::printf("P %d %d %d\n", 90, 112, At(grey, 90, 112));
    std::printf("P %d %d %d\n", 90, 104, At(grey, 90, 104));
  }
  return 0;
}
"""

MOUTH_PIXELS = 90 * 6
DRAWN = ["curious", "greeting", "happy", "angry", "sleepy"]


@pytest.fixture(scope="module")
def drawn(tmp_path_factory) -> dict[str, dict]:
    directory = tmp_path_factory.mktemp("face-bitmap")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "face"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-I", str(MAIN), "-I", str(FIRMWARE),
         "-o", str(binary), str(harness), str(BITMAP)],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"

    output = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
    result: dict[str, dict] = {}
    current: dict | None = None
    for line in output.stdout.splitlines():
        if line.startswith("FACE "):
            name = line.split()[1]
            current = {"probes": {}}
            result[name] = current
        elif line.startswith("P "):
            _, x, y, value = line.split()
            current["probes"][(int(x), int(y))] = int(value)
        elif line.startswith("HASH "):
            current["hash"] = line.split()[1]
        else:
            key, value = line.split()
            current[key.lower()] = int(value)
    assert set(result) == {"none", *DRAWN}, f"6つの顔が出なかった: {sorted(result)}"
    return result


def test_none_is_blank(drawn):
    """⚠️ 空の画面は5つの顔のどれでもない——`none` は6つ目の顔ではない。"""
    assert drawn["none"]["bright"] == 0
    assert drawn["none"]["partial"] == 0
    assert drawn["none"]["mouth"] == 0


def test_every_face_has_pixels(drawn):
    for name in DRAWN:
        assert drawn[name]["bright"] > 0, f"{name} は明るい画素を持たない"


def test_the_mouth_is_the_vendors_bar(drawn):
    """⛔ 口は 90 x 6 の棒で、どの感情でも同じ場所に、隙間なくある。

    ⚠️ **vendor の既定では、感情は目だけを変える**——`DefaultEyes::setEmotion` は
    あっても `DefaultMouth::setEmotion` は無い。口が感情ごとに動いたら、それは
    写しではなく創作である。
    """
    for name in DRAWN:
        assert drawn[name]["mouth"] == MOUTH_PIXELS, f"{name} の口が {drawn[name]['mouth']} 画素"


def test_the_two_eyes_are_mirror_images(drawn):
    """⛔ 右目は左目の鏡像である——vendor は右目に回転の符号を反転させる。"""
    for name in DRAWN:
        assert drawn[name]["mirror_mismatch"] == 0, f"{name} の二つの目が鏡像でない"


def test_nothing_is_lit_outside_the_eyes_and_the_mouth(drawn):
    """⚠️ 背景は黒である——目と口の外に画素があれば、それは誰も描いていない。"""
    for name in DRAWN:
        assert drawn[name]["outside"] == 0, f"{name}: 目と口の外に {drawn[name]['outside']} 画素"


def test_the_edges_are_smooth(drawn):
    """⛔ **円の縁に、白でも黒でもない画素が要る。**

    一度これを落とした——1 bit で描いた顔は階段で、著者が「ギザギザ」と言った。
    ⚠️ ここが 0 に戻れば、見た目も階段に戻る。
    """
    for name in DRAWN:
        assert drawn[name]["eye_edge"] > 0, (
            f"{name}: 円の縁に中間の画素が1つも無い——1 bit に戻っている"
        )
    # ⚠️ 開いた目ほど縁は長い。sleepy はまぶたが大半を覆うので、数で比べない。
    # ⛔ 数は画素格子に依存する（半径 10 の円が格子に乗った日で 80）。ここで
    #    縛るのは「縁が在る」ことだけであり、正確な数ではない。
    assert drawn["curious"]["eye_edge"] > 50, (
        f"curious の縁の中間画素が {drawn['curious']['eye_edge']} 個しかない"
    )


def test_the_sleepy_eyes_are_the_most_closed(drawn):
    """⚠️ 重み 35 の目は、重み 75 の目より覆われている——眠さは白い面積で測れる。"""
    assert drawn["sleepy"]["bright"] < drawn["curious"]["bright"], (
        f"sleepy {drawn['sleepy']['bright']} / curious {drawn['curious']['bright']}"
    )


def test_the_lid_follows_the_vendors_weight(drawn):
    """⛔ まぶたの量を、見える場所で測る。

    - `curious`（Doubt: 重み 75, 回転 0）: 目の上端 y=96 は覆われ、下端 y=112 は白い。
    - `sleepy`（Sleepy: 重み 35）: 中心 y=104 まで覆われ、y=112 はまだ白い。
    """
    assert drawn["curious"]["probes"][(90, 96)] == 0, "curious の上まぶたが開いている"
    assert drawn["curious"]["probes"][(90, 112)] > 0, "curious の下が白くない"
    assert drawn["sleepy"]["probes"][(90, 104)] == 0, "sleepy の目が閉じていない"
    assert drawn["sleepy"]["probes"][(90, 112)] > 0, "sleepy の下が白くない"


def test_the_shared_figure_is_shared_on_screen_too(drawn):
    """⚠️ **`happy` と `greeting` は同じ顔である**——ホストが決めたことであり、
    画面はそれを勝手に2つに分けない。⛔ 残る4つは、どの2つも違う絵である。
    """
    key = lambda name: f"{drawn[name]['hash']}:{drawn[name]['bright']}"
    assert key("happy") == key("greeting"), "同じ顔が画面では別の絵になっている"

    distinct = {key(name) for name in ("happy", "curious", "angry", "sleepy")}
    assert len(distinct) == 4, "4つの異なる絵になるはずである"
