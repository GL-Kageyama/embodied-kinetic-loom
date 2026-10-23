#include "face_bitmap.h"

#include <cmath>
#include <cstring>

namespace {

// ⛔ The drawing is the vendor's default skin, not one of ours — **with one
//    exception, written where it happens**: the normal face's eye is a plain
//    disc since 2026-10-20, by the author's word (`StyleFor`). Every other
//    number below is lifted from `vendor-src/StackChan/firmware/main/stackchan/
//    avatar/skins/default/` (M5Stack, MIT, git 1b57655): `eyes.cpp` and
//    `mouth.cpp`. The vendor draws it with LVGL containers; this file draws the
//    same shapes with a rasterizer, because this firmware carries no LVGL.
//
//    ⚠️ What is copied: the two eye centres, the eye size for `setSize(0)`, the
//    mouth size for `setWeight(0)`, and the six emotion pairs (weight, rotation)
//    from `DefaultEyes::setEmotion`. ⛔ What is not: the eyelid's *animation*,
//    the blink, the breath, and the mouth's speech motion — none of those is
//    here, and none of them is a face.
//
//    ⚠️ LVGL anti-aliases its circles; a 1-bit renderer did not, and the first
//    face on the screen was a staircase the author could see. The coverage of
//    each pixel is sampled 8 x 8 below, which is how the smoothness comes back
//    without the library.

// `_eye_pos = Vector2i(-70, -16)` — offsets from the panel's centre (320x240).
constexpr int kEyeOffsetX = 70;
constexpr int kEyeOffsetY = -16;

// `_mouth_pos = Vector2i(0, 26)`.
constexpr int kMouthOffsetY = 26;

// `setSize(0)` maps -100..100 to 8..32: 0 lands on 20 px.
constexpr int kEyeSize = 20;

// `setWeight(0)` maps 0..100 to 90..60 wide and 6..50 high, radius 0..16:
// weight 0 is a flat bar 90 x 6, radius 0. That is the default mouth.
constexpr int kMouthWidth = 90;
constexpr int kMouthHeight = 6;

// Samples per axis, per pixel. 8 x 8 gives 65 grey levels — enough that the
// staircase is gone, and cheap because only the eyes carry edges.
constexpr int kSamples = 8;

// ⛔ **There is no vertical adjustment here, and the reason it was proposed is
//    recorded.** On 2026-10-18 the author reported the whole drawing sitting two
//    rows low, and a `-2` was written here on their word. The photograph they
//    then sent showed why that reading was wrong: the panel was receiving each
//    eight-row chunk of the frame while the DMA was still reading the previous
//    one, so *every shape had a copy eight rows below it* — a mouth drawn as two
//    lines, and a stray line under each eye. ⚠️ The two rows were a piece of that
//    tear, not a placement. The tear is fixed in `display.cpp`; this file draws
//    the vendor's rows exactly (eyes 94..113, mouth 143..148). ⛔ Do not add an
//    offset here to chase a symptom that belongs to the wire.



// The eyelid is a square of the eye's own size, aligned centre and pushed up by
// `weight` percent of that size. Weight 100 lifts it clear; weight 0 covers the
// eye completely. ⚠️ The vendor computes this in `DefaultEyes::setWeight`.
//
// ⚠️ **The mouth is two more numbers, and they were added on 2026-10-24** so that
//    a face can carry something an eye reads without a new renderer. ⛔ The five
//    Pet faces keep the vendor's `setWeight(0)` bar — 90 x 6 — and the three
//    words this body added each get their own rectangle. **A mouth is a
//    rectangle and stays one**: no curve, no speech motion, no radius. That is
//    the vendor's own default at weight 0, and it is the one shape this file
//    draws without supersampling because LVGL draws no edge on it either.
struct Style {
  int weight;        // 0..100 — how much of the eye the lid leaves open
  int rotation;      // tenths of a degree, as LVGL takes it
  int mouth_width;   // px, centred on the panel's centre line
  int mouth_height;  // px
};

// `DefaultEyes::setEmotion`, verbatim: Neutral (100, 0), Happy (72, 1550),
// Angry (70, 450), Sad (70, -400), Doubt (75, 0), Sleepy (35, -50).
// ⚠️ The five words of this repository map onto those six as below. `greeting`
//    and `happy` are the same drawing on purpose — that is the host's decision,
//    and this file does not split it.
//
// ⛔ **The last three rows are not the vendor's, and they are not measurements.**
//    They are this body's words (2026-10-24), and each one is a guess at what an
//    eye will read as that word — ⚠️ **the entries in `startled` and `watching`
//    are a widened or deepened mouth, not a new shape**, because a new shape is
//    a thing only the author's eye can approve. Which word a drawing is, is
//    asked one at a time by `bench face`.
Style StyleFor(Face face) {
  switch (face) {
    case Face::kHappy:
    case Face::kGreeting:
      return {72, 1550, kMouthWidth, kMouthHeight};
    case Face::kAngry:
      return {70, 450, kMouthWidth, kMouthHeight};
    case Face::kCurious:
      // ⛔ **This row is no longer the vendor's.** `Doubt` is (75, 0): a disc
      //    with its top five rows cut flat by the lid. On 2026-10-20 the author
      //    asked for a plain filled circle in the normal state — 「通常時の目の
      //    形は、単純な⚫︎がいいな」. Weight 100 is `DefaultEyes::setWeight`'s
      //    other end: the lid is lifted clear of the disc, so the eye is the
      //    disc. ⚠️ **The other faces keep the vendor's numbers**, and this is
      //    the one row where the drawing differs from the skin — by a word.
      //    ⚠️ A blink is still weight 0, which covers this disc completely.
      return {100, 0, kMouthWidth, kMouthHeight};
    case Face::kSleepy:
      return {35, -50, kMouthWidth, kMouthHeight};
    // ——— この機体の3語（2026-10-24）。
    //
    // `focused` — 書き物の最中。**目を半分閉じ、口を小さく結ぶ。** 重さ55は
    //   `sleepy` の35より開いていて、`curious` の100より閉じている——**眠りでは
    //   なく集中**を狙った位置である。口は既定の3分の2。
    case Face::kFocused:
      return {55, 0, 60, 6};
    // `watching` — コマンドが走っている最中。**目はほぼ開いたまま、口が広い。**
    //   重さ88は「少し細めた」であって、眠りにも驚きにも寄らない。
    case Face::kWatching:
      return {88, 0, 132, 6};
    // `startled` — 失敗の2秒。**目は丸く、口は開いている。** 口の高さ20は
    //   `setWeight` の 6..50 の内側であり、動かすのは幅と高さの2つだけである。
    case Face::kStartled:
      return {100, 0, 36, 20};
    case Face::kNone:
      break;
  }
  return {100, 0, kMouthWidth, kMouthHeight};
}

constexpr float kDegreesToRadians = 3.14159265f / 180.0f;

// One eye: a white disc, with the black lid cut out of it. ⚠️ The lid is part of
// the container LVGL rotates, so it is the *inverse-rotated* sample that is
// tested against an axis-aligned square.
void DrawEye(uint8_t* grey, int cx, int cy, const Style& style, int sign) {
  const float angle =
      static_cast<float>(sign * style.rotation) * 0.1f * kDegreesToRadians;
  const float c = std::cos(angle);
  const float s = std::sin(angle);

  const float radius = kEyeSize / 2.0f;
  const float half = kEyeSize / 2.0f;
  // ⚠️ Integer, like the vendor: `DefaultEyes::setWeight` computes
  //    `-map_range(weight, 0, 100, 0, height)` with `int` arithmetic, so weight
  //    72 lifts the lid by 14, not 14.4. A fractional lid here is a lid the
  //    vendor does not have.
  const float lid_offset =
      -static_cast<float>(style.weight * kEyeSize / 100);

  // The disc's radius bounds every white pixel; the box only needs a margin.
  const int reach = kEyeSize / 2 + 1;
  constexpr float kStep = 1.0f / kSamples;

  for (int y = cy - reach; y <= cy + reach; ++y) {
    if (y < 0 || y >= face_bitmap::kHeight) {
      continue;
    }
    for (int x = cx - reach; x <= cx + reach; ++x) {
      if (x < 0 || x >= face_bitmap::kWidth) {
        continue;
      }
      int covered = 0;
      // ⚠️ Pixel `x` covers `[x, x+1)`, not `[x-0.5, x+0.5)`. The mouth fills
      //    integer indices directly, and the eyes did not — so the eyes sat half
      //    a pixel right and down of the mouth, and the author saw a shift
      //    rather than a stair. Same convention, both shapes.
      for (int sy = 0; sy < kSamples; ++sy) {
        const float fy = static_cast<float>(y) + (sy + 0.5f) * kStep;
        for (int sx = 0; sx < kSamples; ++sx) {
          const float fx = static_cast<float>(x) + (sx + 0.5f) * kStep;
          const float dx = fx - static_cast<float>(cx);
          const float dy = fy - static_cast<float>(cy);
          const float qx = c * dx + s * dy;
          const float qy = -s * dx + c * dy;

          const bool in_disc = qx * qx + qy * qy <= radius * radius;
          const bool in_lid = qx >= -half && qx <= half &&
                              qy >= lid_offset - half && qy <= lid_offset + half;
          if (in_disc && !in_lid) {
            ++covered;
          }
        }
      }
      grey[y * face_bitmap::kWidth + x] =
          static_cast<uint8_t>(covered * 255 / (kSamples * kSamples));
    }
  }
}

// ⚠️ The vendor's mouth is a container with radius 0 at weight 0: a crisp
//    rectangle, where LVGL itself draws no anti-aliased edge. Its corners and
//    sides land on pixel boundaries, so it is filled solid. ⚠️ **Since
//    2026-10-24 the size comes from the face's `Style`** — a rectangle is still
//    a rectangle, and only its two numbers move.
void DrawMouth(uint8_t* grey, const Style& style) {
  const int cx = face_bitmap::kWidth / 2;
  const int cy = face_bitmap::kHeight / 2 + kMouthOffsetY;
  const int left = cx - style.mouth_width / 2;
  const int top = cy - style.mouth_height / 2;
  for (int y = top; y < top + style.mouth_height; ++y) {
    if (y < 0 || y >= face_bitmap::kHeight) {
      continue;
    }
    if (left < 0 || left + style.mouth_width > face_bitmap::kWidth) {
      continue;
    }
    std::memset(grey + y * face_bitmap::kWidth + left, 255, style.mouth_width);
  }
}

}  // namespace

namespace {

// ⚠️ One renderer with the lid's weight as an argument, so that a blink and a
//    face are the same shapes in the same places. `weight < 0` means "the face's
//    own weight" — the vendor's `setWeight` is exactly this knob.
void RenderWith(Face face, uint8_t* grey, int weight) {
  std::memset(grey, 0, face_bitmap::kBytes);
  if (face == Face::kNone) {
    return;
  }

  Style style = StyleFor(face);
  if (weight >= 0) {
    style.weight = weight;
  }
  const int cx = face_bitmap::kWidth / 2;
  const int cy = face_bitmap::kHeight / 2 + kEyeOffsetY;
  // ⚠️ The vendor's `apply_style` negates the rotation for the right eye:
  //    `_is_left_eye ? rotation : -rotation`.
  DrawEye(grey, cx - kEyeOffsetX, cy, style, +1);
  DrawEye(grey, cx + kEyeOffsetX, cy, style, -1);
  DrawMouth(grey, style);
}

}  // namespace

void face_bitmap::render(Face face, uint8_t* grey) {
  RenderWith(face, grey, -1);
}

void face_bitmap::render_blink(Face face, uint8_t* grey) {
  // ⚠️ Weight 0 covers the eye completely (`StyleFor`'s own scale), so a blink
  //    is the same drawing with one integer at its other end. ⛔ The mouth does
  //    not move: a blink is an eye, not an expression.
  RenderWith(face, grey, 0);
}

bool face_bitmap::can_blink(Face face) {
  // ⛔ `sleepy` is nearly closed already (weight 35); closing it the rest of the
  //    way reads as falling asleep, not as blinking. `kNone` is not a face.
  return face != Face::kNone && face != Face::kSleepy;
}
