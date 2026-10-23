# -*- coding: utf-8 -*-
"""**光の語が、12個の灯と画面の両方で同じ色相になることを、実際に走らせて確かめる。**

⛔ **なぜ要るか。** 2026-10-24 まで色の表は `leds.cpp` の無名名前空間にあり、
画面はそれを読めなかった。著者の言葉は「光の色に合わせて、今の白抜きの表情を、
その光の色と同じにしよう」——⇒ **表は `light_colour.cpp` へ移り、`ScreenColour` が
その上に立った。** ⚠️ **写しを2つ持てば、部屋と顔は黙って食い違う。**
⇒ **このファイルが C++ をコンパイルして走らせ、2つの読みを訊く。**

測るのは4つ:

- **8語すべてに、灯の色と画面の色がある。**
- **画面の色は、灯の色と同じ色相である**——3つの比が同じ（丸めの範囲で）。
- **画面の最大の成分は 232 である**——⚠️ 選んだ数であり、測定ではない。
- ⛔ **`off` の画面は黒ではない。** `resting` は毎晩 `off` を送り、2026-10-24 に
  著者の目が**眠る顔が点いたまま**なのを見た。**黒に従う画面は、その絵を消していた。**

## ⛔ このファイルが確かめないこと

- **パネルには何も届かない**——ここに SPI も無い。測るのは表の値だけである。
- **その色が見て良いか。** ⛔ 8つの色はすべて**選択**であり、測定ではない。
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess

import pytest

from engine.backend import protocol_stackchan as wire

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIRMWARE = REPO_ROOT / "projects" / "stackchan-firmware"
MAIN = FIRMWARE / "main"

COMPILER = shutil.which("clang++") or shutil.which("g++")

pytestmark = pytest.mark.skipif(
    COMPILER is None,
    reason="この環境に C++ のコンパイラが無い——色の表は走らせられない",
)

HARNESS = r"""
#include "command_frame.h"
#include "light_colour.h"
#include <cstdio>

int main() {
  const Light lights[8] = {Light::kOff,     Light::kDim,   Light::kWriting,
                           Light::kBusy,    Light::kBreathe, Light::kWarm,
                           Light::kAlert,   Light::kError};
  const char* const names[8] = {"off",     "dim",   "writing", "busy",
                                "breathe", "warm",  "alert",   "error"};
  for (int i = 0; i < 8; ++i) {
    const light_colour::Rgb led = light_colour::LedColour(lights[i]);
    const light_colour::Rgb screen = light_colour::ScreenColour(lights[i]);
    std::printf("LIGHT %s %d %d %d %d %d %d\n", names[i], led.r, led.g, led.b,
                screen.r, screen.g, screen.b);
  }
  return 0;
}
"""

#: ⚠️ 選んだ数である（`light_colour.cpp`）。画面の色の最大の成分。
SCREEN_PEAK = 232


@pytest.fixture(scope="module")
def colours(tmp_path_factory) -> dict[str, dict[str, tuple[int, int, int]]]:
    directory = tmp_path_factory.mktemp("light-colour")
    harness = directory / "harness.cpp"
    harness.write_text(HARNESS, encoding="utf-8")
    binary = directory / "colour"
    done = subprocess.run(
        [COMPILER, "-std=c++17", "-Wall", "-I", str(MAIN), "-I", str(FIRMWARE),
         "-o", str(binary), str(harness), str(MAIN / "light_colour.cpp")],
        capture_output=True, text=True,
    )
    assert done.returncode == 0, f"コンパイルに失敗した:\n{done.stderr}"

    output = subprocess.run([str(binary)], capture_output=True, text=True, check=True)
    result: dict[str, dict[str, tuple[int, int, int]]] = {}
    for line in output.stdout.splitlines():
        parts = line.split()
        assert parts[0] == "LIGHT", line
        numbers = [int(value) for value in parts[2:]]
        result[parts[1]] = {
            "led": (numbers[0], numbers[1], numbers[2]),
            "screen": (numbers[3], numbers[4], numbers[5]),
        }
    return result


def test_every_light_word_has_both_colours(colours):
    """⚠️ **8語すべてに、灯の色と画面の色がある。**"""
    assert set(colours) == set(wire.LIGHTS)


def test_the_screen_keeps_the_leds_hue(colours):
    """⛔ **画面の色は、灯の色と同じ色相である**——3つの成分の比が同じ。

    ⚠️ 比で測るのは、画面が灯より明るいからである（同じ明るさでは、2.8インチの
    パネルの20 px の円は、にじみであって顔ではない）。⛔ 明るさが違うことは
    色相が違うことではない——**ここが落ちる日は、2つの色が別の色になった日である。**
    """
    for word in wire.LIGHTS:
        if word == "off":
            continue
        led = colours[word]["led"]
        screen = colours[word]["screen"]
        # a/b == c/d, cross-multiplied so that integer rounding cannot hide a swap.
        # ⚠️ With a tolerance of one unit of screen rounding: each channel is
        #    truncated to an integer, so 28*232/44 = 147.6 arrives as 147 and an
        #    exact cross-multiplication would call that a different hue. The bound
        #    is what two truncations can move, and no more.
        for i, j in ((0, 1), (0, 2), (1, 2)):
            tolerance = max(led[i], led[j])
            assert abs(screen[i] * led[j] - screen[j] * led[i]) <= tolerance, (
                f"{word}: 灯 {led} と画面 {screen} の色相が違う"
            )


def test_the_screens_brightest_channel_is_the_chosen_peak(colours):
    """⚠️ **画面の色は、最大の成分が 232 になるまで持ち上げてある。**

    ⛔ 232 は**選んだ数**である（`light_colour.cpp`）。ここが縛るのは「8語が
    同じ明るさで並ぶ」ことであり、その値が良いことではない。
    """
    for word in wire.LIGHTS:
        if word == "off":
            continue
        assert max(colours[word]["screen"]) == SCREEN_PEAK, (
            f"{word} の画面の色 {colours[word]['screen']} の最大が {SCREEN_PEAK} でない"
        )


def test_the_screen_is_not_the_leds_colour(colours):
    """⛔ **2つの読みは同じ値ではない**——同じなら、明るさを上げた意味が無い。"""
    for word in wire.LIGHTS:
        if word == "off":
            continue
        assert colours[word]["screen"] != colours[word]["led"], (
            f"{word} の画面と灯が同じ値である"
        )


def test_off_is_black_on_the_leds_and_not_on_the_screen(colours):
    """⛔ **`off` の画面は黒ではない。** ここが、この表で最も大事な1行である。

    `resting` は毎晩 `light: "off"` を送る。2026-10-24、著者は Mac を落とした夜に
    **休みの顔が5分ほど点いたまま**なのを見た（`records/2026-10-24-the-body-that-slept-itself.md`）。
    ⇒ **`off` を黒として写す画面は、その絵を消していた。** 例外は名指しである——
    `ScreenColour` の `off` は中立の灰であり、**色相の規則から外れる唯一の行**である。
    """
    assert colours["off"]["led"] == (0, 0, 0), "off の灯が黒でない"
    r, g, b = colours["off"]["screen"]
    assert (r, g, b) != (0, 0, 0), "off の画面が黒である——眠る顔が消える"
    assert r == g == b, f"off の画面が中立でない: {(r, g, b)}"


def test_the_frame_sets_the_colour_before_it_draws():
    """⚠️ **枠は、色を先に置いてから絵を描く。**

    ⛔ `show()` は押し出しを行うので、**その時点で色が決まっていなければ、
    新しい顔は古い色で1枚描かれる**。そして `face: null` の枠（光だけが動いた枠）は
    `tint()` が描き直す——**この2行が無ければ、絵は去った光の色を着たまま残る。**
    """
    source = (MAIN / "main.cpp").read_text(encoding="utf-8")
    body = source.split("void HandleFrame(const char* line, int length) {", 1)[1].split(
        "\n}", 1
    )[0]
    assert "display::tint(command.light);" in body, "枠が色を置いていない"
    assert body.index("display::tint") < body.index("display::show"), (
        "色より先に絵を描いている"
    )
