# -*- coding: utf-8 -*-
"""**部屋の外向きの状態。** `Decision` を、機体へ渡る枠（`Frame`）に変える。

⛔ **この層は送らない。** 送るのは伝送路であり、**それはまだ存在しない**——
だから `Frame` は値であり、行になっても、どこへも渡らない。

## いつ枠が出るか

⚠️ **「遷移のときだけ」を、事象の種類で数えない。** 段階は、6つの遷移事象のほかにも
動く——`blocked` の中の `PostToolUse` が `working` へ戻すように。⛔ **理由（`reason`）は
状態の変化を分割しない。** だからこの層は、**理由ではなく、状態そのものを見る**:

- **見せるものが変わったとき**——顔か光が、最後に伝えた値と違うとき;
- **身振りが選ばれたとき**——`Decision.gesture` は遷移でしか選ばれない。**首は遷移でしか動かない**;
- **プロセスで最初の判定のとき**——⚠️ **機体の状態は知られていない。** 1枠目は、
  部屋の状態を機体へ立てるためのものである。

⛔ **変わらない判定は、枠にならない。** それは流れを作らないための規則であり、
**20 ms の連続値ではない**という決定（2026-10-18）と同じものである。

## 数を持たない

⛔ **`Frame` の3つの欄は、すべて語である**——`wire.FACES`・`wire.LIGHTS`・
`wire.GESTURES` のどれか、あるいは `None`。**数は1つも無い**（`engine/backend/protocol_stackchan.py`）。
⚠️ **語から数への変換は、この層の下でも上でもない**——それは、この個体を測った日に
書かれるものであり、まだ書かれていない。
"""
from __future__ import annotations

from dataclasses import dataclass

from projects.stackchan.behaviors import Decision


@dataclass(frozen=True)
class Frame:
    """**1つの枠。** ⛔ **3つの欄とも語であり、数ではない。**

    ⚠️ `face` が `None` なら「変えない」であり、`gesture` が `None` なら「動かない」である。
    **光は常に在る**——`light` は `None` にならない。
    """

    face: str | None
    light: str
    gesture: str | None


class Outbound:
    """**機体に最後に伝えた値を持つ。** 時計も、ソケットも、環境も読まない。

    ⚠️ **状態はこのクラスの中だけに在る**——デーモンが1つ持ち、プロセスと共に生まれ、
    プロセスと共に消える。**再起動は再開しない**（`docs/stackchan-daemon.md`）。
    """

    def __init__(self) -> None:
        self._face: str | None = None
        self._light: str | None = None

    @property
    def known(self) -> tuple[str | None, str | None]:
        """**最後に伝えた（顔、光）。** ⚠️ `None` は「まだ何も伝えていない」である。"""
        return (self._face, self._light)

    def frame(self, decision: Decision) -> Frame | None:
        """**判定1つを、枠1つにする。変わるものが無ければ `None`。**

        ⚠️ **`Decision.face` が `None` のときは「変えない」であり、既知の顔を保つ。**
        光は常に現在の値である。
        """
        face = decision.face.value if decision.face is not None else self._face
        light = decision.light.value
        gesture = decision.gesture

        face_changed = face != self._face
        light_changed = light != self._light
        first = self._light is None

        self._face = face
        self._light = light

        if not (first or face_changed or light_changed or gesture is not None):
            return None

        return Frame(
            face=face if face_changed else None,
            light=light,
            gesture=gesture,
        )


__all__ = ["Frame", "Outbound"]
