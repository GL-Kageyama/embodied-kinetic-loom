# -*- coding: utf-8 -*-
"""**画面の顔が、vendor の既定スキンの形と滑らかさになっていることを、実際に描いて確かめる。**

⛔ **なぜ要るか。** 基板の `face_bitmap.cpp` は、vendor の LVGL 実装
（`skins/default/eyes.cpp` / `mouth.cpp`）の**形と数値を手で写した**ものである。
⚠️ **写しは、黙ってずれる**——ずれたことを、画面を見るまで誰も言わない。
⇒ **このファイルが C++ をコンパイルして走らせ、描かれた画素そのものを訊く。**

訊くのは次の性質:

- **口は、矩形である**——どの顔でも、塗られた画素は1つの矩形を隙間なく埋める。
  ⚠️ **Pet の5つは vendor の既定の棒である**——90 x 6、同じ場所に 540 画素。
  ⛔ **この機体の3語（2026-10-24）は、幅と高さがそれぞれ違う**——ただし矩形のままである。
- **2つの目は、鏡像である**——vendor は右目に回転の符号を反転させる。
- ⚠️ **通常時の目だけは、vendor の形ではない**（0.19.53）——著者の要望
  「通常時の目の形は、単純な⚫︎がいいな」で、重み 75 のまぶたを払った円盤になり、
  **上下が釣り合う**ことを測る。⛔ **残る4つの Pet の顔は vendor の数値のままである。**
- **目と口の外は、黒である**（`secondaryColor`）。
- **眠い顔の目は、最も閉じている**——重み 35 は 75 より覆われる。
- **縁は滑らかである**——0 でも 255 でもない中間の値を持つ画素が、円の縁に在る。
  ⛔ **これが無ければ、20 px の円は階段である**——一度そうなって、著者が見つけた。
- **まばたきは目だけを閉じる**——口は1バイトも動かず、両目とも同時に覆われる。
- **眠い顔は、まばたきしない**——`can_blink` が `sleepy` と `kNone` に偽を返す。

## ⛔ このファイルが確かめないこと

- **パネルには何も届かない。** ここに SPI も I2C も無い。
- **LVGL を走らせて比べてもいない。** 比べているのは vendor の**数値**と、
  この描画器が出す形である。⛔ 数値を写し間違えれば、この検査は緑のまま
  vendor と違う顔を描く——だから数値の出典を `face_bitmap.cpp` に書いてある。
- **色は測っていない。** ここが読むのは被覆（0..255）であり、光の色を掛けるのは
  `display::Push` である（`tests/test_stackchan_light_colour.py` がその表を見る）。
- **3つの新しい語が、その語に見えるか。** ⛔ それは著者の目の判定であり、
  `bench face` が1つずつ出す。ここが言えるのは**8つが8つの違う絵である**ことまでである
  （`happy` と `greeting` を除けば7つ）。
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
    reason="この環境に C++ のコンパイラが無い——描画器は走らせない",
)

#: **各顔について: 明るい画素・中間の画素・指紋・口の矩形・左右の目の画素・
#: 鏡像のずれ・決め打ちの画素。** 判定は Python 側で行う。
#:
#: ⚠️ **口の矩形は、目を除いた画素から測る。** 2026-10-24 まで口は90 x 6と決め打ち
#: だったが、その日この機体の3語が幅と高さを動かすようになった——**決め打ちをやめ、
#: 矩形そのものを訊く**（塗られた画素が矩形を隙間なく埋めること、外に何も無いこと）。
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

bool InEye(int x, int y) {
  const bool in_left = x >= 78 && x <= 102 && y >= 92 && y <= 116;
  const bool in_right = x >= 218 && x <= 242 && y >= 92 && y <= 116;
  return in_left || in_right;
}

// 眉の箱——2026-10-24 に `focused` が着けた。⛔ 目より上に在るので、目とは別に
// 名指さないと「口」の測定が眉を飲み込む（実際に最初は飲み込んだ）。
bool InBrow(int x, int y) {
  const bool in_left = x >= 75 && x <= 105 && y >= 76 && y <= 92;
  const bool in_right = x >= 215 && x <= 245 && y >= 76 && y <= 92;
  return in_left || in_right;
}

// 明るい画素が最初に現れる行。⛔ 眉の傾きを、数ではなく**端の高さ**で測るため。
int TopRow(const std::vector<uint8_t>& grey, int x0, int x1, int y0, int y1) {
  for (int y = y0; y <= y1; ++y) {
    for (int x = x0; x <= x1; ++x) {
      if (At(grey, x, y) >= 128) {
        return y;
      }
    }
  }
  return -1;
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

// The mouth, measured rather than assumed: the bounding box of everything lit
// outside the eyes.
struct Mouth {
  int left = 0;
  int right = -1;
  int top = 0;
  int bottom = -1;
  bool present() const { return right >= left && bottom >= top; }
  int area() const {
    return present() ? (right - left + 1) * (bottom - top + 1) : 0;
  }
  bool holds(int x, int y) const {
    return present() && x >= left && x <= right && y >= top && y <= bottom;
  }
};

Mouth MeasureMouth(const std::vector<uint8_t>& grey) {
  Mouth mouth;
  bool any = false;
  for (int y = 0; y < face_bitmap::kHeight; ++y) {
    for (int x = 0; x < face_bitmap::kWidth; ++x) {
      if (InEye(x, y) || InBrow(x, y) || At(grey, x, y) == 0) {
        continue;
      }
      if (!any) {
        mouth.left = x;
        mouth.right = x;
        mouth.top = y;
        mouth.bottom = y;
        any = true;
        continue;
      }
      if (x < mouth.left) mouth.left = x;
      if (x > mouth.right) mouth.right = x;
      if (y < mouth.top) mouth.top = y;
      if (y > mouth.bottom) mouth.bottom = y;
    }
  }
  return mouth;
}

int Solid(const std::vector<uint8_t>& grey, const Mouth& mouth) {
  int n = 0;
  for (int y = mouth.top; y <= mouth.bottom; ++y) {
    for (int x = mouth.left; x <= mouth.right; ++x) {
      n += At(grey, x, y) == 255;
    }
  }
  return n;
}

}  // namespace

int main() {
  const Face faces[9] = {Face::kNone,    Face::kCurious,  Face::kGreeting,
                         Face::kHappy,   Face::kAngry,    Face::kSleepy,
                         Face::kFocused, Face::kWatching, Face::kStartled};
  const char* const names[9] = {"none",    "curious",  "greeting",
                                "happy",   "angry",    "sleepy",
                                "focused", "watching", "startled"};
  std::vector<uint8_t> grey(face_bitmap::kBytes);
  for (int i = 0; i < 9; ++i) {
    face_bitmap::render(faces[i], grey.data());
    const Mouth mouth = MeasureMouth(grey);

    int bright = 0;
    int partial = 0;
    std::uint32_t hash = 2166136261u;
    for (int b = 0; b < face_bitmap::kBytes; ++b) {
      bright += grey[b] >= 128;
      partial += grey[b] > 0 && grey[b] < 255;
      hash = (hash ^ grey[b]) * 16777619u;
    }

    const int left = Bright(grey, 78, 92, 102, 116);
    const int right = Bright(grey, 218, 92, 242, 116);
    const int eye_edge = Dim(grey, 78, 92, 102, 116) + Dim(grey, 218, 92, 242, 116);
    // The normal face's eye is a plain disc since 2026-10-20: its box is filled
    // the same above and below the centre row (y = 104).
    const int top = Bright(grey, 80, 94, 100, 103);
    const int bottom = Bright(grey, 80, 104, 100, 113);

    // Mirror check about the vertical through x = 160. ⚠️ Pixel `x` covers
    // [x, x+1), so its mirror is `319 - x`, not `320 - x` — the off-by-one
    // that put the eyes half a pixel away from the mouth.
    int mismatched = 0;
    for (int y = 76; y <= 116; ++y) {
      for (int x = 78; x <= 102; ++x) {
        mismatched += At(grey, x, y) != At(grey, 319 - x, y);
      }
    }

    // Everything outside the eyes and the mouth's own box must stay black.
    int outside = 0;
    for (int y = 0; y < face_bitmap::kHeight; ++y) {
      for (int x = 0; x < face_bitmap::kWidth; ++x) {
        if (!InEye(x, y) && !InBrow(x, y) && !mouth.holds(x, y)) {
          outside += At(grey, x, y) != 0;
        }
      }
    }

    std::printf("FACE %s\n", names[i]);
    std::printf("BRIGHT %d\n", bright);
    std::printf("PARTIAL %d\n", partial);
    std::printf("HASH %08x\n", hash);
    std::printf("MOUTHLEFT %d\n", mouth.left);
    std::printf("MOUTHRIGHT %d\n", mouth.right);
    std::printf("MOUTHTOP %d\n", mouth.top);
    std::printf("MOUTHBOTTOM %d\n", mouth.bottom);
    std::printf("MOUTHAREA %d\n", mouth.area());
    std::printf("MOUTHSOLID %d\n", Solid(grey, mouth));
    std::printf("LEFT %d\n", left);
    std::printf("RIGHT %d\n", right);
    std::printf("EYE_EDGE %d\n", eye_edge);
    std::printf("TOP %d\n", top);
    std::printf("BOTTOM %d\n", bottom);
    std::printf("MIRROR_MISMATCH %d\n", mismatched);
    std::printf("OUTSIDE %d\n", outside);
    const int brow = Bright(grey, 75, 76, 105, 92) + Bright(grey, 215, 76, 245, 92);
    std::printf("BROW %d\n", brow);
    std::printf("BROW_LEFT_OUTER %d\n", TopRow(grey, 78, 84, 74, 93));
    std::printf("BROW_LEFT_INNER %d\n", TopRow(grey, 96, 102, 74, 93));
    // ⚠️ 右の窓は左の鏡である——`x` の鏡は `319 - x` なので、左の 78..84 は
    //    235..241、96..102 は 217..223。ずれた窓で測ると、鏡像が1行ずれて見える。
    std::printf("BROW_RIGHT_INNER %d\n", TopRow(grey, 217, 223, 74, 93));
    std::printf("BROW_RIGHT_OUTER %d\n", TopRow(grey, 235, 241, 74, 93));

    // Pinned pixels: the lid's weight, read where it shows.
    std::printf("P %d %d %d\n", 90, 96, At(grey, 90, 96));
    std::printf("P %d %d %d\n", 90, 112, At(grey, 90, 112));
    std::printf("P %d %d %d\n", 90, 104, At(grey, 90, 104));

    // The blink: the same drawing with both lids shut.
    face_bitmap::render_blink(faces[i], grey.data());
    int blink_sum = 0;
    int blink_bright = 0;
    int blink_mouth = 0;
    int mouth_moved = 0;
    for (int y = mouth.top; y <= mouth.bottom; ++y) {
      for (int x = mouth.left; x <= mouth.right; ++x) {
        blink_mouth += At(grey, x, y) == 255;
      }
    }
    for (int y = 0; y < face_bitmap::kHeight; ++y) {
      for (int x = 0; x < face_bitmap::kWidth; ++x) {
        blink_sum += At(grey, x, y);
        blink_bright += At(grey, x, y) >= 128;
      }
    }
    // Compare the mouth's box against the open drawing: the blink must not move
    // one byte of it. Re-rendered from scratch here so the comparison is exact.
    face_bitmap::render(faces[i], grey.data());
    std::vector<uint8_t> open_box;
    for (int y = mouth.top; y <= mouth.bottom; ++y) {
      for (int x = mouth.left; x <= mouth.right; ++x) {
        open_box.push_back(static_cast<uint8_t>(At(grey, x, y)));
      }
    }
    face_bitmap::render_blink(faces[i], grey.data());
    std::size_t k = 0;
    for (int y = mouth.top; y <= mouth.bottom; ++y) {
      for (int x = mouth.left; x <= mouth.right; ++x) {
        mouth_moved += At(grey, x, y) != open_box[k] ? 1 : 0;
        ++k;
      }
    }
    std::printf("BLINKSUMMED %d\n", blink_sum);
    std::printf("BLINKBRIGHT %d\n", blink_bright);
    std::printf("BLINKMOUTH %d\n", blink_mouth);
    std::printf("MOUTHMOVED %d\n", mouth_moved);
    std::printf("BLINKLEFT %d\n", Bright(grey, 78, 92, 102, 116));
    std::printf("BLINKRIGHT %d\n", Bright(grey, 218, 92, 242, 116));
    std::printf("CANBLINK %d\n", face_bitmap::can_blink(faces[i]) ? 1 : 0);
  }
  return 0;
}
"""

#: ⚠️ **vendor の口。** この5つは `setWeight(0)` の棒である。
VENDOR_MOUTH = (115, 204, 143, 148)
MOUTH_PIXELS = 90 * 6

DRAWN = ["curious", "greeting", "happy", "angry", "sleepy", "focused", "watching", "startled"]
PET = ["curious", "greeting", "happy", "angry", "sleepy"]
BODY = ["focused", "watching", "startled"]
#: ⚠️ `sleepy` はこのリストに入らない——`can_blink` が偽を返す。
BLINKABLE = ["curious", "greeting", "happy", "angry", "focused", "watching", "startled"]


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
    assert set(result) == {"none", *DRAWN}, f"9つの顔が出なかった: {sorted(result)}"
    return result


def test_none_is_blank(drawn):
    """⚠️ 空の画面は8つの顔のどれでもない——`none` は9つ目の顔ではない。"""
    assert drawn["none"]["bright"] == 0
    assert drawn["none"]["partial"] == 0
    assert drawn["none"]["mouthsolid"] == 0
    assert drawn["none"]["moutharea"] == 0


def test_every_face_has_pixels(drawn):
    for name in DRAWN:
        assert drawn[name]["bright"] > 0, f"{name} は明るい画素を持たない"


def test_every_mouth_is_one_solid_rectangle(drawn):
    """⛔ **口は矩形であり、隙間も飛び出しも無い**——8つの顔すべてで。

    ⚠️ ここが矩形そのものを訊くのは、2026-10-24 に口の幅と高さが顔ごとに
    動くようになったからである（`StyleFor`）。**決め打ちの90 x 6をやめ、
    「塗られた画素が矩形を埋め尽くす」という性質を測る。**
    """
    for name in DRAWN:
        row = drawn[name]
        assert row["moutharea"] > 0, f"{name} に口が無い"
        assert row["mouthsolid"] == row["moutharea"], (
            f"{name}: 口の矩形 {row['moutharea']} 画素のうち "
            f"{row['mouthsolid']} しか塗られていない"
        )


def test_the_pets_five_keep_the_vendors_bar(drawn):
    """⛔ **Pet の5つの口は、vendor の既定の棒である**——90 x 6、同じ場所に 540 画素。

    ⚠️ **vendor の既定では、感情は目だけを変える**——`DefaultEyes::setEmotion` は
    あっても `DefaultMouth::setEmotion` は無い。口が感情ごとに動いたら、それは
    写しではなく創作である。**この機体の3語はそこから外れる。**
    """
    left, right, top, bottom = VENDOR_MOUTH
    for name in PET:
        row = drawn[name]
        assert (row["mouthleft"], row["mouthright"], row["mouthtop"], row["mouthbottom"]) == (
            left, right, top, bottom,
        ), f"{name} の口が vendor の位置に無い"
        assert row["mouthsolid"] == MOUTH_PIXELS, f"{name} の口が {row['mouthsolid']} 画素"


def test_the_three_new_mouths_are_their_own(drawn):
    """⚠️ **この機体の3語は、幅か高さが vendor の棒と違う**——でなければ語を足した意味がない。

    ⛔ **これは「その語に見える」ことの検査ではない。** 測っているのは
    **3つが3つとも違う矩形である**ことまでであり、良し悪しは著者の目が決める。
    """
    shapes = {
        name: (drawn[name]["mouthright"] - drawn[name]["mouthleft"] + 1,
               drawn[name]["mouthbottom"] - drawn[name]["mouthtop"] + 1)
        for name in BODY
    }
    assert len(set(shapes.values())) == 3, f"3つの口が重なっている: {shapes}"
    for name, shape in shapes.items():
        assert shape != (90, 6), f"{name} の口が vendor の棒のままである"


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

    - `sleepy`（Sleepy: 重み 35）: 中心 y=104 まで覆われ、y=112 はまだ白い。
    ⚠️ **`curious` はもう vendor のまぶたを持たない**——下の検査が、その代わりを
    測る（2026-10-20、著者の要望）。
    """
    assert drawn["sleepy"]["probes"][(90, 104)] == 0, "sleepy の目が閉じていない"
    assert drawn["sleepy"]["probes"][(90, 112)] > 0, "sleepy の下が白くない"


def test_the_normal_eye_is_a_plain_disc(drawn):
    """✅ **2026-10-20、著者の要望**: 通常時の目は単純な ● である。

    ⚠️ **vendor の `Doubt`（重み 75）は、上の5行をまぶたで切り落とした円盤である。**
    著者の言葉は「通常時の目の形は、単純な⚫︎がいいな」——⇒ 重み 100 は
    `DefaultEyes::setWeight` のもう一方の端であり、まぶたが円盤から離れる。

    - 目の上端 y=96 が白い（vendor の重みでは覆われていた）。
    - 中心 y=104 の上下で、白い画素の数が等しい——**対称でなければ、それは円ではない。**
    ⛔ **色や明るさは測っていない。** 測っているのは形だけである。
    """
    assert drawn["curious"]["probes"][(90, 96)] > 0, "curious の上端がまぶたで覆われている"
    assert drawn["curious"]["top"] == drawn["curious"]["bottom"], (
        f"curious の目が上下で釣り合っていない: "
        f"{drawn['curious']['top']} / {drawn['curious']['bottom']}"
    )
    assert drawn["curious"]["top"] > 0


def test_the_watching_face_also_wears_the_disc(drawn):
    """✅ **2026-10-24、著者の「処理中も目は丸がいい」**——`watching` の目は
    `curious` と同じ円盤であり、違うのは**口の広さだけ**である。

    ⛔ この顔は 0.19.80 では重み88で描かれていた——「少し細めた」目である。
    88は `focused`（当時55）と `curious`（100）の中間であり、**どの語の言い分でもない**。
    著者の目はそれを細めた目と読まず、丸を求めた。⇒ この顔が言うのは口の広さだけに
    なった。

    ⛔ **0.19.81 はここに「細めるのは `focused` の仕事」と書いた——その前提は同日の
    うちに崩れた**（著者の「眉毛ある時も丸目がいいな」で `focused` も丸になった）。
    ⇒ いまは**この機体が足した3語のどれも、目を細めない。**
    """
    watched = drawn["watching"]
    assert watched["probes"][(90, 96)] > 0, "watching の上端がまぶたで覆われている"
    assert watched["top"] == watched["bottom"], (
        f"watching の目が上下で釣り合っていない: {watched['top']} / {watched['bottom']}"
    )
    disc = ("left", "right", "top", "bottom", "eye_edge")
    assert tuple(watched[key] for key in disc) == tuple(
        drawn["curious"][key] for key in disc
    ), "watching の目が curious の円盤と同じでない"


def test_the_focused_face_wears_the_disc_under_its_brow(drawn):
    """✅ **2026-10-24、著者の「眉毛ある時も丸目がいいな」**——眉を着けたまま、
    目は `curious` と同じ円盤である。

    ⛔ 0.19.81 までの `focused` は重み55、「半分閉じた目」だった。眉が付いても
    それは残っていたが、著者の目は**眉があるときも丸**を選んだ。⇒ この顔が言うのは
    **眉と口の2つだけ**になる。⚠️ 丸めたのは目だけであり、口（60 x 6）は動いていない。
    """
    row = drawn["focused"]
    assert row["probes"][(90, 96)] > 0, "focused の上端がまぶたで覆われている"
    assert row["top"] == row["bottom"], (
        f"focused の目が上下で釣り合っていない: {row['top']} / {row['bottom']}"
    )
    disc = ("left", "right", "top", "bottom", "eye_edge")
    assert tuple(row[key] for key in disc) == tuple(
        drawn["curious"][key] for key in disc
    ), "focused の目が curious の円盤と同じでない"
    assert row["brow"] > 0, "focused が眉を落としている"
    assert row["mouthright"] - row["mouthleft"] + 1 == 60, "focused の口が動いている"


def test_only_the_focused_face_wears_a_brow(drawn):
    """✅ **2026-10-24、著者の「書いている時は、目の上に眉毛（緩やか斜め）をつけよう」**
    ——`focused` だけが眉を着け、形は `＼　／` である。

    ⚠️ **これは「その語に見える」ことの検査ではない。** 測っているのは
    **着けているのが1つの顔だけ**であることと、**傾きの向き**（外側が高く、
    内側が低い）までである。⛔ 太さ・長さ・間隔の良し悪しは著者の目が決める
    ——`bench face focused` がそれを出す。⛔ 4つの数は選んだ数であり、測った数ではない。
    """
    assert drawn["focused"]["brow"] > 0, "focused に眉が無い"
    for name in DRAWN:
        if name == "focused":
            continue
        assert drawn[name]["brow"] == 0, f"{name} が眉を着けている"

    row = drawn["focused"]
    # `＼` — 左の眉は、外側（左）の端が高く、内側（右）の端が低い。
    assert row["brow_left_outer"] >= 0 and row["brow_left_inner"] >= 0, (
        f"眉が見つからない: outer={row['brow_left_outer']} inner={row['brow_left_inner']}"
    )
    assert row["brow_left_inner"] - row["brow_left_outer"] >= 4, (
        f"左の眉が内側へ下っていない: outer={row['brow_left_outer']} "
        f"inner={row['brow_left_inner']}"
    )
    # `／` — 右の眉はその鏡像であり、内側の端が同じだけ低い。
    assert row["brow_right_inner"] - row["brow_right_outer"] >= 4, (
        f"右の眉が内側へ下っていない: inner={row['brow_right_inner']} "
        f"outer={row['brow_right_outer']}"
    )
    # ⚠️ 2本の眉は同じ高さに在る——片方だけ高いのは鏡像ではない。
    assert row["brow_left_outer"] == row["brow_right_outer"], (
        f"2本の眉の高さが違う: {row['brow_left_outer']} / {row['brow_right_outer']}"
    )


def test_a_blink_closes_both_eyes_and_leaves_the_mouth_alone(drawn):
    """⛔ **まばたきは目であり、9つ目の表情ではない。**

    - 両目とも覆われる——片方だけ閉じたら、それはまばたきではなく不具合である。
    - 口は1バイトも動かない——口は `setWeight` を持たない、目のためのつまみである。
    - 閉じた画面に残るのは口と眉だけである——⚠️ **眉はまばたきしない**（2026-10-24）:
      まぶたが下りるのは目であり、眉は表情のまま残る。
    - 閉じた絵は開いた絵と違う——重みを無視する描画器なら、ここで落ちる。
    """
    for name in BLINKABLE:
        row = drawn[name]
        assert row["blinkleft"] == 0, f"{name}: 左目が閉じていない"
        assert row["blinkright"] == 0, f"{name}: 右目が閉じていない"
        assert row["blinkmouth"] == row["mouthsolid"], (
            f"{name}: まばたきの口が {row['blinkmouth']} 画素"
        )
        assert row["mouthmoved"] == 0, f"{name}: まばたきで口が {row['mouthmoved']} 画素動いた"
        assert row["blinkbright"] == row["mouthsolid"] + row["brow"], (
            f"{name}: 閉じた画面に口と眉以外の明るい画素が "
            f"{row['blinkbright'] - row['mouthsolid'] - row['brow']} 個ある"
        )


def test_the_shared_figure_blinks_as_one(drawn):
    """⚠️ `happy` と `greeting` が同じ顔なら、閉じた絵も同じである。"""
    assert drawn["happy"]["blinkbright"] == drawn["greeting"]["blinkbright"]
    assert drawn["happy"]["mouthsolid"] == drawn["greeting"]["mouthsolid"]


def test_sleepy_and_none_do_not_blink(drawn):
    """⛔ **眠い顔はまばたきしない**——すでに重み 35 で閉じており、そこから
    閉じきるのは「眠る」であって「まばたく」ではない。`kNone` は顔ですらない。

    ⚠️ 判定は `face_bitmap::can_blink` に置いてある——`display.cpp` の中に
    置けば、ホストから訊けない規則になる。
    """
    assert drawn["sleepy"]["canblink"] == 0, "眠い顔がまばたきする"
    assert drawn["none"]["canblink"] == 0, "顔の無い画面がまばたきする"
    for name in BLINKABLE:
        assert drawn[name]["canblink"] == 1, f"{name} がまばたきしない"


def test_the_shared_figure_is_shared_on_screen_too(drawn):
    """⚠️ **`happy` と `greeting` は同じ顔である**——ホストが決めたことであり、
    画面はそれを勝手に2つに分けない。⛔ 残る7つは、どの2つも違う絵である。
    """
    key = lambda name: f"{drawn[name]['hash']}:{drawn[name]['bright']}"
    assert key("happy") == key("greeting"), "同じ顔が画面では別の絵になっている"

    others = ("curious", "angry", "sleepy", "focused", "watching", "startled")
    distinct = {key(name) for name in others}
    assert len(distinct) == len(others), "8つの語が8つの違う絵になっていない"
