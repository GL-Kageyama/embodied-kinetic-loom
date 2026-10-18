# -*- coding: utf-8 -*-
"""**身振りを、首の動きにする。** 五つの姿勢と、その間の埋め方だけを持つ。

⛔ **ここは時計もポートも読まない。** 姿勢の表と、間の長さの規則だけである。
⇒ **同じ始点と同じ身振りからは、同じ列が出る。**

⚠️ **表の正本は、基板の側にある**（`projects/stackchan-firmware/main/main.cpp` の
`kLookUpPosture` などの五つ）。ここはその**写し**である——ホストが姿勢の行を流すには、
行き先の数をホストも持たなければならない。
⛔ **写しであることを隠さない。** `tests/test_stackchan_neck.py` の
`test_the_firmware_table_and_this_one_agree` が `main.cpp` を読み、五つの数を突き合わせる——
**食い違った日に赤くなるのが、この写しの値打ちである。**

⚠️ **`nod` だけは2つの動きである。** 基板の `PlayGesture` も、下の点へ行ってから
`kLookUpPosture` へ戻る。⇒ **戻り先は `look_up` であり、6つ目の数ではない。**

⛔ **間の長さは、測った速さではなく、著者が受け入れた再生のものである**——
0.19.11 の三度目の再生は「1/3 の長さ」で、`かなり良い。これでOKだと思う。` だった。
その比はおよそ `degrees / 60` である（`records/2026-10-18-the-neck.md`）。
**下限の 0.2 秒は判断である**: それより短い動きは、補間ではなく1回の指令に見える。
"""
from __future__ import annotations

from engine.backend.protocol_stackchan_pose import Pose
from engine.trajectory.profile import Spring

from .motion import Motion, chain, motion

__all__ = [
    "POSTURES",
    "NOD_RETURN",
    "DEFAULT_SHARPNESS",
    "DEFAULT_PERIOD",
    "DEFAULT_DURATION",
    "DEFAULT_HOLD",
    "MIN_DURATION",
    "DEGREES_PER_SECOND",
    "posture",
    "ends",
    "duration_for",
    "plan",
]

#: ⚠️ **2026-10-18 に、著者の目が一つずつ決めた五つの姿勢である。** 度の10倍。
#: ⛔ **正本は `main.cpp`**——ここはホストの写しである。
#: ⚠️ **`nod` は下の点**であり、戻り先は `NOD_RETURN` である。
POSTURES: dict[str, tuple[int, int]] = {
    "look_up": (80, 500),
    "look_side": (350, 500),
    "rest": (0, 30),
    "nod": (80, 30),
    "recoil": (-80, 700),
}

#: ⚠️ **`nod` の2つ目の行き先である。** ⛔ 6つ目の数ではない——基板も同じ姿勢へ戻る。
NOD_RETURN = "look_up"

#: ⚠️ **純正ファームウェアのばねの、写した形である**（`servo.cpp` を読んだ、2026-10-18）。
#: 山は `u = 1/a`——`a = 5` なら動きの20%地点。**長さは `duration_for` が決める。**
#: ⛔ **この数は機体の数ではない。** 著者の目が決めるまで、暫定である。
DEFAULT_SHARPNESS = 5.0

#: ⚠️ **この基板が受け取った刻みである**——2026-10-18、20 ms × 678 姿勢、断られたもの0。
#: ⛔ **機体の数ではない。** 変えてよいが、変えたことは測り直すまで主張にならない。
DEFAULT_PERIOD = 0.02

#: ⚠️ **暫定である。** 縁の `--duration` の既定であり、身振りの長さではない——
#: **身振りの長さは `duration_for` が距離から決める。**
DEFAULT_DURATION = 0.6

#: ⚠️ **基板の 500 ms より長いこと。** 短いと、動きの終わりでトルクが落ちる。
DEFAULT_HOLD = 0.6

#: ⚠️ **判断である。** 短すぎる動きは、滑らかではなく、1回の指令に見える。
MIN_DURATION = 0.2

#: ⚠️ **著者が受け入れた再生の比である**（0.19.11、三度目の再生）。**測った上限ではない。**
DEGREES_PER_SECOND = 60.0


def posture(name: str) -> Pose:
    """**表の1行を、姿勢にする。** ⛔ 知らない名前は、発明せずに断る。"""
    try:
        yaw, pitch = POSTURES[name]
    except KeyError:
        raise ValueError(f"知らない身振りである: {name!r}") from None
    return Pose(yaw_tenths=yaw, pitch_tenths=pitch)


def ends(gesture: str) -> Pose:
    """**その身振りが終わる姿勢。** ⚠️ **最初の1回を基板に任せたとき、ここへ居る。**"""
    if gesture not in POSTURES:
        raise ValueError(f"知らない身振りである: {gesture!r}")
    return posture(NOD_RETURN if gesture == "nod" else gesture)


def duration_for(starts: Pose, ends: Pose) -> float:
    """**2つの姿勢の間の長さ。** ⚠️ **遅い方の軸が決める**——2軸は同じ時間で動く。

    ⛔ **斜辺では測らない。** サーボは各軸を自分の距離だけ動かすので、
    **時間を決めるのは、長く動く方の軸である。**
    """
    distance = max(
        abs(ends.yaw_tenths - starts.yaw_tenths),
        abs(ends.pitch_tenths - starts.pitch_tenths),
    ) / 10.0
    return max(MIN_DURATION, distance / DEGREES_PER_SECOND)


def plan(gesture: str, starts: Pose, *, period: float = DEFAULT_PERIOD,
         sharpness: float = DEFAULT_SHARPNESS) -> Motion:
    """**始点から、その身振りの終わりまでの列を組む。**

    ⚠️ **`nod` だけ2つの動きをつなぐ。** 継ぎ目は `chain` が1つに畳む。
    ⛔ **始点は呼ぶ側のものである**——このホストは首の位置を読まないので、
    **最後に命じた姿勢**が始点になる（`daemon/__main__.py` の `Neck`）。
    """
    if gesture not in POSTURES:
        raise ValueError(f"知らない身振りである: {gesture!r}")
    profile = Spring(sharpness)
    if gesture != "nod":
        target = posture(gesture)
        return motion(starts, target, duration_for(starts, target), period, profile=profile)
    down = posture("nod")
    back = posture(NOD_RETURN)
    return chain((
        motion(starts, down, duration_for(starts, down), period, profile=profile),
        motion(down, back, duration_for(down, back), period, profile=profile),
    ))
