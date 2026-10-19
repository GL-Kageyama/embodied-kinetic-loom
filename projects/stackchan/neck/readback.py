# -*- coding: utf-8 -*-
"""**基板に、今どこに居るかを尋ねた答えを読む。** ⛔ **時計もポートも読まない**——綴りだけである。

⚠️ **尋ねる行は、この機体の bench が既に持っている**（`main.cpp` の `bench pos`）。
⛔ **新しい命令を発明しない。** 尋ねる綴りも、答える綴りも、基板の側に在る——
ここはその**写し**であり、`tests/test_stackchan_readback.py` が `main.cpp` の
`printf` を読み、同じ綴りであることを突き合わせる。

⛔ **度の欄を読まない。** `angle %d.%d` は、1度に満たない負の角で符号を落とす
（C の整数除算は 0 へ切り捨てるから、-5  tenths は `0.5` と印字される）。
⇒ **読むのは `raw` と `zero` であり、10分の1度へ戻す式は基板と同じである。**
⚠️ **その式は `(raw - zero) * 5 * 10 / 16`**——`srcs/16` の1カウントが 5/16 度である。
"""
from __future__ import annotations

import re

from engine.backend.protocol_stackchan_pose import Pose

__all__ = ["QUERY", "tenths", "answered", "parse", "verdict"]

#: **基板へ尋ねる1行。** ⚠️ **改行で終わる**——`fgets` は行で返る。
QUERY = b"bench pos\n"

#: ⚠️ **`bench: yaw raw 512, angle 2.5 deg (zero 504)` の形である。**
#: ⛔ **`angle` の欄は読むが、使わない**——負の小さな角で符号が落ちる。
_AXIS = re.compile(
    r"bench: (yaw|pitch) raw (-?\d+), angle -?\d+\.\d+ deg \(zero (-?\d+)\)"
)


#: ⚠️ **基板が「尋ねられた」と答えた印である。** `bench: yaw=ok pitch=no answer`
#: のように、**サーボが答えなかった場合も、この行は出る**——その2つを混ぜない。
_ANSWERED = re.compile(r"bench: (?:yaw|pitch)=")


def tenths(raw: int, zero: int) -> int:
    """**1カウントを、度の10分の1へ。** ⚠️ **基板と同じ切り捨て（0 へ向かう）である。**

    ⛔ **`//` をそのまま使わない。** Python の `//` は負で負の無限大へ切り捨てるので、
    `-3 // 16` は `-1` になる——**C の `-3 / 16` は `0` である。**
    1カウントの差が、この機体では 0.3 度である。
    """
    delta = (raw - zero) * 5 * 10
    return delta // 16 if delta >= 0 else -((-delta) // 16)


def answered(text: str) -> bool:
    """**基板が尋ねられて、何か答えたか。** ⛔ **姿勢が読めたことではない。**

    ⚠️ **この2つは別である**: `bench: yaw=no answer pitch=no answer` は
    **コンソールが答えた**（そしてサーボが答えなかった）——**沈黙とは違う。**
    ログがその区別を持たなければ、配線の故障とサーボの故障が同じ行になる。
    """
    return _ANSWERED.search(text) is not None


#: ⚠️ **基板が流しの終わりに印字する、自分の数である。**
#: `pose: %d applied, %d refused, %d clamped`（`main.cpp` の `PoseWatchdog`）。
#: ⛔ **ホストの `applied` とは別の数である**——基板は**受けた行をすべて数える**
#: （最後の姿勢の繰り返しも1行である）。デーモンの `applied` は予定の歩数であり、
#: 繰り返しは `held` に数える。**同じ名前の2つの数を、同じ欄に入れない。**
_VERDICT = re.compile(r"^pose: (\d+) applied, (\d+) refused, (\d+) clamped", re.M)


def verdict(text: str) -> dict | None:
    """**基板が自分の数で言った、最後の判定。** ⚠️ **印字が無ければ `None`。**

    ⚠️ **2026-10-19 に、この行が要ることが分かった。** その日、デーモンは
    `{"neck": "recoil", "applied": 18, ...}` と書いた——**送った行の数である**——
    そして次の探針は、頭が**1カウントも動いていない**ことを読んだ。
    **基板の側の数（断った・丸めた）は、そのとき誰にも読まれていなかった。**
    ⇒ **「送った」と「適用された」は別の問いであり、片方だけでは答えにならない。**

    ⚠️ **最後の1つを返す**——窓の中に2つの流しがあれば、新しい方が効いている。
    """
    found = None
    for match in _VERDICT.finditer(text):
        found = match
    if found is None:
        return None
    return {
        "applied": int(found.group(1)),
        "refused": int(found.group(2)),
        "clamped": int(found.group(3)),
    }


def parse(text: str) -> Pose | None:
    """**答えの1行か2行から、1つの姿勢。** ⚠️ **2軸そろわなければ `None`。**

    ⛔ **欠けた軸を 0 で埋めない。** 0 は `rest` の yaw であり、
    **「分からない」と同じ綴りになる**——その姿勢へ動けば、首は本物の 0 へ飛ぶ。
    """
    found: dict[str, int] = {}
    for match in _AXIS.finditer(text):
        found[match.group(1)] = tenths(int(match.group(2)), int(match.group(3)))
    if "yaw" not in found or "pitch" not in found:
        return None
    return Pose(yaw_tenths=found["yaw"], pitch_tenths=found["pitch"])
