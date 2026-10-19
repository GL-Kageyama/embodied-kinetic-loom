# -*- coding: utf-8 -*-
"""**判定の後処理。** `Decision` を受け取り、`Decision` を返す。

⛔ **段階表を2つ持たない。** 段階・顔・身振り・音・1秒の体の下限・90秒・
静かな時間は、すべて `projects.stackchan` のものである。この層が足すのは
**光の選び方と、失敗の長さと、起きたときの1語だけ**である。

## 1. 作業の光（`working` のあいだだけ）

| work | 光 |
|---|---|
| `write` | ⚠️ 0.19.47 で自分の語を得る。いまは `dim` |
| `run` | ⚠️ 0.19.47 で自分の語を得る。いまは `dim` |
| `read` / `search` / `plan` / `other` / 知らされていない | `dim` |

⚠️ **滞留 `WORK_DWELL` 秒。** 光は5秒に1回より速く変わらない——
**道具のたびに色が変われば、それは鏡であり、相棒ではない**（`behaviors.py` の決定）。
⛔ **`working` へ入ることは滞留に数えない。** 章の出入りは即座である。
✅ **だから、最初の `write` はすぐ見える**——入った時刻を「5秒前」として数える。

## 2. 失敗の長さ

⚠️ **1回の失敗は、いままで完全に見えなかった**——3回続かないと何も出ないからである。
- **1回** → `alert` を `FAILURE_FLASH_SECONDS` だけ点し、作業の光へ戻る。
- **3回連続** → 既存の `concern`（`alert` を持続）。**語は増やさない。長さで区別する。**

⇒ **期限が1つ増える**（`_flash_until`）。**新しい刻みは発明しない**——
`tick(at)` は既にある（`behaviors.py`）。デーモンは、部屋の期限とこの期限の
**早い方**で目を覚ませばよい。

## 3. 起きたときの1語

⚠️ **90秒黙ったあと、次の事象で起きるとき、いまは顔と光だけが変わる。**
⇒ **`pip` を1つ足す。** ⛔ **身振りは足さない**——体の下限（1秒）を
この層が二重に持つことになる。**音は体の下限に従わない**（既存の規則）。

⚠️ **「起きた」を知るために、この層は1ビットだけ覚える**——直前の判定が
`resting` だったかどうかである。⛔ **事象も時計も増やさない**：`Decision` は
段階をすでに運んでいる。**覚えるのは、それを見た結果だけである。**
⛔ **`face` では見分けられない**——`blocked` を抜ける事象も顔を連れてくる
（`Companion._evidence` の `CLEARS_BLOCKED` の枝）。⇒ **顔が名乗るのは
「起きた」ではなく「変わった」である。**

## 4. 賑やかさのダイヤル

| presence | 作業の光 | 失敗の点滅 | 起きた `pip` |
|---|---|---|---|
| `quiet` | 常に `dim` | 無し | 無し |
| `normal` | あり | あり | あり |
| `lively` | あり（滞留2秒） | あり | あり |

⛔ **既存の `--motion` / `--sound` は独立のままである。** このダイヤルは
**この層が足したチャンネルだけ**を閉じる。
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from projects.stackchan.behaviors import (
    BODY_NONE,
    CONCERN,
    Decision,
    Focus,
    Light,
    Phase,
)

from . import work as work_words

# ---------------------------------------------------------------------------
# 賑やかさ。⚠️ 閉じた3語である。
# ---------------------------------------------------------------------------

PRESENCE_QUIET = "quiet"
PRESENCE_NORMAL = "normal"
PRESENCE_LIVELY = "lively"

PRESENCES: tuple[str, ...] = (PRESENCE_QUIET, PRESENCE_NORMAL, PRESENCE_LIVELY)

#: ⚠️ **既定は「ふつう」である**（著者の裁定、2026-10-20）。
DEFAULT_PRESENCE = PRESENCE_NORMAL

#: ⚠️ **製品の決定であり、測定値ではない。** 作業の光は5秒に1回より速く変わらない。
WORK_DWELL = 5.0

#: ⚠️ **賑やかな側の滞留であり、これも測定値ではない。**
LIVELY_DWELL = 2.0

#: ⚠️ **製品の決定であり、測定値ではない。** 1回の失敗は2秒だけ見える。
FAILURE_FLASH_SECONDS = 2.0

#: ⚠️ **この層が足す理由の語である。** `behaviors.DECISION_REASONS` の外に在る——
#: **向こうは向こうの閉じた集合であり、ここはここの集合である。**
#: ⛔ **「観測した」でないのは、点滅が尽きたのが観測ではないからである。**
FLASHED = "flashed"

#: ⚠️ **作業の語から光への写像である。** ⛔ **0.19.46 では `write` と `run` も `dim`**——
#: 2つの新しい光の語は、codec・schema・ファームウェアと**同じ日に**入る（0.19.47）。
#: **語だけ先に増やせば、基板は枠ごと拒む。**
WORK_LIGHTS: dict[str, Light] = {
    "write": Light.DIM,
    "run": Light.DIM,
}

#: ⚠️ **知らされていない作業の光である。**
WORK_LIGHT_OTHER = Light.DIM

#: ⚠️ **起きたときの1語である。**
WAKE_SOUND = "pip"


@dataclass
class Presence:
    """**部屋を1つ持ち、判定を1つ返す。** 時計も環境も読まない。

    ⚠️ **`room` は `Focus` である**——**窓が2つ以上あっても、首は1本のままである。**
    この層は、その上に光と失敗と挨拶を重ねる。
    """

    presence: str = DEFAULT_PRESENCE
    room: Focus = field(default_factory=Focus)
    _work: str | None = field(default=None, init=False)
    _showing: Light | None = field(default=None, init=False)
    _changed_at: float = field(default=0.0, init=False)
    _flash_until: float | None = field(default=None, init=False)
    #: ⚠️ **直前の判定が `resting` だったか。** 起きたことを言うための1ビットである。
    _resting: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.presence not in PRESENCES:
            raise ValueError(self.presence)

    @property
    def dwell(self) -> float:
        """**このダイヤルの滞留である。**"""
        return LIVELY_DWELL if self.presence == PRESENCE_LIVELY else WORK_DWELL

    @property
    def held(self) -> str | None:
        """**いま見ている窓。** ⚠️ 部屋のものであり、この層のものではない。"""
        return self.room.held

    @property
    def deadline(self) -> float | None:
        """**次に目を覚ますべき時刻。** ⚠️ **部屋の期限と点滅の期限の早い方である。**

        ⛔ **どちらか一方だけが在るときは、それを返す。** `None` は
        「期限が無い」であり、0 ではない。
        """
        room = self.room.deadline
        if room is None:
            return self._flash_until
        if self._flash_until is None:
            return room
        return min(room, self._flash_until)

    # -- 事象 ---------------------------------------------------------------

    def offer(self, session: str, event: str, at: float,
              quiet: bool = False, work: str | None = None) -> Decision:
        """**窓を名乗る事象を1つ受け取り、判定を返す。**

        ⚠️ **`work` は、その事象が運ぶときだけ来る**（`work.WORK_EVENTS`）。
        ⛔ **知らない語は覚えない**——覚えれば、次の判定がその語で光る。
        """
        if work in work_words.WORK_WORDS and work_words.carries_work(event):
            self._work = work
        return self._apply(self.room.offer(session, event, at, quiet=quiet), at, quiet)

    def tick(self, at: float) -> Decision | None:
        """**事象の無い時刻を1つ進める。** ⚠️ **変わらなければ `None`。**

        ⚠️ **部屋の刻みが先である。** 段階が動いたときは、その1行だけを返す——
        点滅が同時に尽きていても、**消えた光を戻す相手はもう `working` に居ない。**
        """
        base = self.room.tick(at)
        if base is not None:
            self._flash_until = None
            return self._apply(base, at, quiet=False)
        return self._flash_tick(at)

    # -- 部品 ---------------------------------------------------------------

    def _apply(self, decision: Decision, at: float, quiet: bool) -> Decision:
        """**判定を通し、通した結果から「起きていたか」を1ビットだけ覚える。**"""
        result = self._decide(decision, at, quiet)
        self._resting = result.phase is Phase.RESTING
        return result

    def _decide(self, decision: Decision, at: float, quiet: bool) -> Decision:
        if self._woke(decision):
            decision = self._greet(decision, quiet)

        if decision.phase is not Phase.WORKING:
            self._showing = None
            self._flash_until = None
            return decision

        if decision.reason == CONCERN:
            # ⛔ **3回連続の失敗である。** 既存の持続を、この層は上書きしない。
            # ⚠️ **前の点滅の期限も捨てる**——捨てなければ、2回目の失敗が置いた
            #    2秒後の刻みが、**持続している `alert` を `dim` へ戻してしまう。**
            self._flash_until = None
            self._showing = Light.ALERT
            return decision

        if decision.event == "PostToolUseFailure":
            if self.presence == PRESENCE_QUIET:
                self._showing = Light.DIM
                return replace(decision, light=Light.DIM)
            self._showing = Light.ALERT
            self._flash_until = at + FAILURE_FLASH_SECONDS
            return replace(decision, light=Light.ALERT)

        if self.presence == PRESENCE_QUIET:
            self._showing = Light.DIM
            return replace(decision, light=Light.DIM)

        wanted = self._wanted()
        if self._showing is None:
            # ⚠️ **章の出入りは滞留に数えない。** 入った時刻を「滞留の1つ前」に置く——
            #    そうすれば、最初の write はすぐ見える。
            self._showing = wanted
            self._changed_at = at - self.dwell
        elif wanted is not self._showing and at - self._changed_at >= self.dwell:
            self._showing = wanted
            self._changed_at = at

        return replace(decision, light=self._showing)

    def _wanted(self) -> Light:
        return WORK_LIGHTS.get(self._work, WORK_LIGHT_OTHER)

    def _woke(self, decision: Decision) -> bool:
        """**休息から起きたか。** ⚠️ **この層が覚えている1ビットである。**

        ⛔ **`Decision` の顔では測れない**——`blocked` を抜ける事象も顔を連れてくる。
        見るのは**直前に `resting` だったか**だけであり、遷移そのものは
        `_greet` が `sound` の欄で断る（挨拶は自分の音を持っている）。
        """
        return self._resting and decision.event is not None

    def _greet(self, decision: Decision, quiet: bool) -> Decision:
        """**起きたことに、1語だけ返す。** ⛔ **身振りは返さない。**

        ⚠️ **音のチャンネルが切られていれば鳴らない**（`--sound off`）。
        **静かな時間も同じ1つの値になる**——`behaviors.Companion._sound` と同じ規則である。
        """
        if self.presence == PRESENCE_QUIET:
            return decision
        if not self.room.companion.sound or quiet:
            return decision
        if decision.sound is not None:
            return decision
        return replace(decision, sound=WAKE_SOUND)

    def _flash_tick(self, at: float) -> Decision | None:
        """**点滅が尽きた時刻を1行にする。** ⚠️ **尽きていなければ `None`。**

        ⛔ **状態を変えていない刻みを返さない**——空の行は、ログを水増しするだけである。
        """
        if self._flash_until is None or at < self._flash_until:
            return None
        self._flash_until = None
        light = self._wanted()
        self._showing = light
        self._changed_at = at
        return Decision(
            event=None,
            phase=Phase.WORKING,
            face=None,
            light=light,
            gesture=None,
            body=BODY_NONE,
            sound=None,
            sent=False,
            reason=FLASHED,
        )


__all__ = [
    "PRESENCE_QUIET",
    "PRESENCE_NORMAL",
    "PRESENCE_LIVELY",
    "PRESENCES",
    "DEFAULT_PRESENCE",
    "WORK_DWELL",
    "LIVELY_DWELL",
    "FAILURE_FLASH_SECONDS",
    "FLASHED",
    "WORK_LIGHTS",
    "WORK_LIGHT_OTHER",
    "WAKE_SOUND",
    "Presence",
]
