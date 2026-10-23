# -*- coding: utf-8 -*-
"""**判定の後処理。** `Decision` を受け取り、`Decision` を返す。

⛔ **段階表を2つ持たない。** 段階・顔・身振り・音・1秒の体の下限・90秒・
静かな時間は、すべて `projects.stackchan` のものである。この層が足すのは
**光の選び方と、失敗の長さと、起きたときの1語だけ**である。

## 1. 作業の光と顔（`working` のあいだだけ）

| work | 光 | 顔 |
|---|---|---|
| `write` | `writing` | `focused` |
| `run` | `busy` | `watching` |
| `read` / `search` / `plan` / `other` / 知らされていない | `dim` | `curious`（第1層のまま） |

⚠️ **光と顔は、同じ1つの判断で動く。** 滞留も、章の終わりに忘れることも、
背後の窓を通さないことも、**2つに共通である**——別々に数えれば、片方だけが
遅れた日に「光は動いたのに顔は前の作業」という枠が出る。
⛔ **顔の語はこの層が初めて増やしたものである**（2026-10-24、著者の
「3つ（＋失敗）」）。⇒ **語は codec・schema・ファームの3か所に同じ日に載せた**——
**語だけ先に送れば、基板は枠ごと拒み、光も身振りも一緒に落ちる。**

⚠️ **色はこの層のものではない。** 顔は光の色を着るが、その色を決めるのは
ファームの `main/light_colour.cpp` である——**1つの表を灯と画面が読む。**
⇒ ホストが送るのは語だけで、色は1バイトも渡らない。

⚠️ **滞留 `WORK_DWELL` 秒。** 光は5秒に1回より速く変わらない——
**道具のたびに色が変われば、それは鏡であり、相棒ではない**（`behaviors.py` の決定）。
⛔ **`working` へ入ることは滞留に数えない。** 章の出入りは即座である。
✅ **だから、最初の `write` はすぐ見える**——入った時刻を「5秒前」として数える。

⚠️ **語は部屋に1つであり、章に属する。** ⇒ **章が終われば忘れる**
（`closing` / `present` / `resting` / `greeting` へ出た時点で捨てる。
⛔ **`blocked` では捨てない**——許可待ちは章の途中であり、戻ったときに
同じ作業が続いているからである）。**忘れなければ、次の章は前の章の
最後の道具の色で開き**、しかもその色が**最初の道具の滞留を食う**——
✅ **2026-10-20 のデモが、実際にそれを起こした。**

⛔ **背後の窓の語は覚えない。** `Focus` は見ていない窓の事象を `distant` として
返すが、その語で光を選べば**見ている窓の光が背後の窓の道具で変わる**——
⚠️ **これも同じデモで起きた**（「背景の窓は何も変えない」という既存の規則に反する）。
⇒ **`distant` の判定は、この層を1行も通らない。**

⚠️ **窓ごとに語を持つ設計は選んでいない。** 部屋は1つであり、語も1つである。
⇒ **2つの窓が同時に作業しているとき、光は最後に見ている窓の道具に従う。**
⚠️ **奪った直後の章は、前の窓の語を最初の道具まで着ていることがある**——
`UserPromptSubmit` は `working` へ直接入り、`greeting` を通らないからである。
**窓ごとの正しさは測っていない。** ⛔ **ここで `Focus` の規則を写して先回りしない**
——写せば、片方が黙って緩んだ日に、もう片方が鳴らない。

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
    DISTANT,
    Decision,
    Focus,
    Light,
    Phase,
)
from projects.stackchan.faces import Face

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

#: ⚠️ **作業の語から光への写像である。** ✅ **0.19.47 に、2語が自分の光を得た**——
#: codec・schema・ファームウェア・`command_frame.cpp` と**同じ日**である。
#: ⛔ **語だけ先に増やせば、基板は枠ごと拒む。**
WORK_LIGHTS: dict[str, Light] = {
    "write": Light.WRITING,
    "run": Light.BUSY,
}

#: ⚠️ **知らされていない作業の光である。**
WORK_LIGHT_OTHER = Light.DIM

#: ⚠️ **作業の語から顔への写像である**（2026-10-24）。光の写像と同じ形をしている。
#: ⛔ **語は意味に対して付けた**——`focused` は「書いている最中」、`watching` は
#: 「何かが走っている」。⚠️ **形がその語に見えるかは著者の目が決める**（`bench face`）。
WORK_FACES: dict[str, Face] = {
    "write": Face.FOCUSED,
    "run": Face.WATCHING,
}

#: ⚠️ **知らされていない作業の顔である。** 第1層が `working` で出す顔と同じである——
#: ⛔ **「変えない」ではない。** 知らされていない作業に移ったとき、顔が前の作業の
#: まま残れば、**光は `dim` なのに顔は `focused`** という枠が出る。
WORK_FACE_OTHER = Face.CURIOUS

#: ⚠️ **1回の失敗の顔である。** 光（`alert`）と同じ2秒だけ出る。
FAILURE_FACE = Face.STARTLED

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
    #: ⚠️ **いま見えている顔である。** ⛔ 光と同じ1つの判断で動く（`_show`）。
    _showing_face: Face | None = field(default=None, init=False)
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

        ⚠️ **背後の窓の語は、覚えたあとで戻す。** 語は判定を選ぶ前に要る
        （この事象の光がその語で決まる）が、**その事象が見ている側でなければ
        覚えてはならない**——⚠️ **判定が `distant` を名乗った時点で分かる**ので、
        覚えた値を1つ前に戻す。⛔ **`Focus` の規則をここに写して先に判定しない**——
        写せば、片方が黙って緩んだ日に、もう片方が鳴らない。
        """
        remembered = self._work
        if work in work_words.WORK_WORDS and work_words.carries_work(event):
            self._work = work
        decision = self.room.offer(session, event, at, quiet=quiet)
        if decision.reason == DISTANT:
            self._work = remembered
        return self._apply(decision, at, quiet)

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
        if decision.reason == DISTANT:
            # ⛔ **見ていない窓の事象は、この層を1行も通らない。**
            #    通せば、背後の `run` が見ている窓の光を変え、背後の失敗が
            #    見ている窓の `alert` を点す——**「背景は何も変えない」に反する。**
            # ⚠️ **だが、光の欄は素通しできない。** `witness` は `Companion` の
            #    素の光（`working` なら `dim`）を運ぶので、そのまま返せば
            #    **枠が1つ出て、見えている光が `dim` へ落ちる。**
            #    ⇒ **いま見えている光を返す**——**状態は1つも動かさない。**
            if decision.phase is Phase.WORKING and self._showing is not None:
                # ⚠️ **顔も同じである。** `witness` は `Companion` の素の顔を運ぶので、
                #    そのまま返せば**顔だけが `curious` へ落ちる**——光と同じ理由である。
                return replace(decision, light=self._showing, face=self._showing_face)
            return decision

        if self._woke(decision):
            decision = self._greet(decision, quiet)

        if decision.phase is not Phase.WORKING:
            self._show(None, None)
            self._flash_until = None
            if decision.phase is not Phase.BLOCKED:
                # ⚠️ **章が終わったら語を忘れる。** 忘れなければ、次の章は
                #    前の章の最後の道具の色で開き、その色が最初の道具の滞留を食う。
                #    ⛔ **`blocked` は章の途中である**——許可待ちから戻ったとき、
                #    同じ作業が続いている。
                self._work = None
            return decision

        if decision.reason == CONCERN:
            # ⛔ **3回連続の失敗である。** 既存の持続を、この層は上書きしない。
            # ⚠️ **前の点滅の期限も捨てる**——捨てなければ、2回目の失敗が置いた
            #    2秒後の刻みが、**持続している `alert` を `dim` へ戻してしまう。**
            self._flash_until = None
            # ⚠️ **顔は塗り替えない。** 第1層の言い方と同じである——「怒らない。
            #    光だけが『引っかかっている』と言う」。⇒ 顔は作業の顔のまま、
            #    光だけが `alert` になる。**2つを同じ判断で置く**（`_show`）。
            self._show(Light.ALERT, self._wanted_face())
            return decision

        if decision.event == "PostToolUseFailure":
            if self.presence == PRESENCE_QUIET:
                self._show(Light.DIM, None)
                return replace(decision, light=Light.DIM)
            self._show(Light.ALERT, None)
            self._flash_until = at + FAILURE_FLASH_SECONDS
            return replace(decision, light=Light.ALERT, face=FAILURE_FACE)

        if self.presence == PRESENCE_QUIET:
            # ⛔ **静かな側は、この層が足したチャンネルを閉じる。** 光は `dim` に、
            #    この層が着せた顔は脱ぐ。⚠️ **しかし戻り値の顔は塗り替えない**——
            #    第1層の顔（挨拶・締め・`angry`・`sleepy`）はこの層のものではない。
            self._show(Light.DIM, None)
            return replace(decision, light=Light.DIM)

        wanted = self._wanted()
        if self._showing is None:
            # ⚠️ **章の出入りは滞留に数えない。** 入った時刻を「滞留の1つ前」に置く——
            #    そうすれば、最初の write はすぐ見える。
            self._show(wanted, self._wanted_face())
            self._changed_at = at - self.dwell
        elif wanted is not self._showing and at - self._changed_at >= self.dwell:
            self._show(wanted, self._wanted_face())
            self._changed_at = at

        return replace(decision, light=self._showing, face=self._showing_face)

    def _wanted(self) -> Light:
        return WORK_LIGHTS.get(self._work, WORK_LIGHT_OTHER)

    def _wanted_face(self) -> Face:
        return WORK_FACES.get(self._work, WORK_FACE_OTHER)

    def _show(self, light: Light | None, face: Face | None) -> None:
        """**光と顔を、1つの判断で置く。** ⛔ 別々に置けば、片方だけが古い枠が出る。"""
        self._showing = light
        self._showing_face = face

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
        # ⚠️ **光と同じ側へ戻す**——点滅のあいだに作業が変わっていれば、`run` である。
        #    ⛔ **「点滅の前に着ていた顔」を戻すと、2秒のあいだに語が動いた日に
        #    `light: busy` と `face: focused` が並ぶ枠が出る**（2026-10-24、実機で
        #    その枠が1つ出た——`write` → 失敗 → その2秒の間に `run`）。⇒ 戻すのは
        #    **そのとき欲しい顔**であり、この層のものである（`null` ではない）。
        face = self._wanted_face()
        self._show(light, face)
        self._changed_at = at
        return Decision(
            event=None,
            phase=Phase.WORKING,
            face=face,
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
    "WORK_FACES",
    "WORK_FACE_OTHER",
    "FAILURE_FACE",
    "WAKE_SOUND",
    "Presence",
]
