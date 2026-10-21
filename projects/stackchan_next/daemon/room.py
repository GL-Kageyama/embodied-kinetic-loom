# -*- coding: utf-8 -*-
"""**新しい層の部屋。** ソケットも時計も知らない。

⛔ **`projects.stackchan.daemon.room` の写しではない。** 向こうは2語の要求を
読み、`Focus(Companion(...))` を1つ持つ。こちらは**3語目 `work` を読み**、
その上に `Presence` を1枚重ねる——**段階表・90秒・1秒の体の下限・窓の規則・
静かな時間は、すべて向こうのものである**（`projects/stackchan_next/__init__.py`
の約束）。⇒ **規則が2つ在る状態を作らない。**

⚠️ **1行は1つの事象であり、鍵は3つまでである:**

    {"session": "<session_id>", "event": "<hook_event_name>", "work": "<6語>"}

⛔ **知らない鍵は拒む。** 無視するだけなら `prompt` が同乗できる——**同乗でき
ないことが、この層のプライバシーである。**

⚠️ **`work` は任意である。** 載るのは `work.WORK_EVENTS` の事象だけであり、
⚠️ **縁が確かめるのは語の綴りだけである**——**その語がこの事象で意味を持つか
を決めるのは `Presence` であり**、そこでは載っていない語は覚えない
（`tests/test_stackchan_next_presence.py`）。⛔ **縁が同じ規則を2つ目に持てば、
片方が黙って緩んだ日に、もう片方が鳴らない。**

⚠️ **拒否の符号は、向こうの閉じた集合をそのまま使う。** 新しい符号を発明しない
——**知らない語は「値が悪い」であり、「鍵が知らない」ではない。**
"""
from __future__ import annotations

import json

from projects.stackchan import hooks
from projects.stackchan.behaviors import (
    DEFAULT_MOTION,
    DEFAULT_SOUND,
    Companion,
    Decision,
    Focus,
)
from projects.stackchan.daemon.room import CLIENT_TIMEOUT, MAX_LINE, BadRequest  # noqa: F401

from .. import work as work_words
from ..presence import DEFAULT_PRESENCE, PRESENCES, Presence

#: ⚠️ **必須の2語である。** 向こうと同じ綴りであり、同じ意味である。
REQUIRED_KEYS: frozenset[str] = frozenset({"session", "event"})

#: ⚠️ **この層が足す1語である。** 増やすことは、フックの契約を増やすことである
#: （`client.py` の `SOURCE_FIELDS` と対）。
OPTIONAL_KEYS: frozenset[str] = frozenset({"work"})

#: ⚠️ **1行に載ってよい鍵の全部である。**
REQUEST_KEYS: frozenset[str] = REQUIRED_KEYS | OPTIONAL_KEYS


def socket_path(uid: int) -> str:
    """**ソケットの場所。** ⚠️ **既存のデーモンとは別の場所である。**

    ⛔ **`/tmp` の下である**（macOS の `sun_path` は104バイト）。⚠️ **uid を
    値として受ける**——この関数は環境を読まない。⇒ **2つのデーモンが並走
    できる**のは、綴りが2つあるからではなく、**この1つの prefix が違う**からである。
    """
    return f"/tmp/ekl-stackchan-next-{uid}.sock"


def meta_socket_path(uid: int) -> str:
    """**メタのソケットの場所。** ⚠️ **体のソケットとは別の1本である**（決定11）。

    ⛔ **相乗りしない。** 体の `handle()` は枠を書いて基板の受理を待つので、
    その返事は中央 890ms である——**いちばん声をかけたい瞬間に落ちる**（§19.1）。
    ⇒ **同じプロセスに、2本目のソケットと2本目の糸を置く。**

    ⚠️ **綴りはここに1つだけ在る。** フック（Phase 4）もデーモンも、この関数を通る——
    **2か所に書けば、片方だけが直る日が来る。**
    """
    return f"/tmp/ekl-stackchan-meta-{uid}.sock"


def mouth_socket_path(uid: int) -> str:
    """**口のソケットの場所。** ⚠️ **3本目であり、体ともメタとも別である。**

    ⛔ **相乗りしない。** 体の `handle()` は枠を書いて基板の受理を待ち（中央 890ms）、
    メタのソケットは**閉じた3語**しか読まない（§8.1）。⇒ **文という自由な欄を、
    閉じた2本のどちらかへ足さない**——足せば、「`prompt` は同乗できない」という
    この層のプライバシーが、**スキーマの水準で偽になる**（§8.2）。**口は3本目である。**

    ⚠️ **綴りはここに1つだけ在る。** デーモンも口（`stackchan_next.mouth`）も、
    この関数を通る。
    """
    return f"/tmp/ekl-stackchan-mouth-{uid}.sock"


#: ⛔ **口の要求の鍵は1つだけである。** 文のほかに何も載せない——
#: **窓も事象も載せない**：口は体の1文であり、事象ではない（§22.10）。
VOICE_KEYS: frozenset[str] = frozenset({"text"})

#: ⚠️ **1文の長さの上限である（文字数）。** ⛔ **測った数ではなく、選んだ数である。**
#: 設計 §22.7 の案は 15 字であり、80 は「短い1文が3つ入る」長さである。
#: ⛔ **切り詰めない**——**切った文は、別の文である。** 長すぎる文は断る。
VOICE_MAX_CHARS = 80


def parse_voice(line: str) -> str:
    """**口の1行を、文に割る。** ⛔ **読めない行は、理由の符号を付けて断る。**

    ⚠️ **断りの符号は、体と同じ閉じた集合である**（`REFUSAL_CODES`）。
    新しい符号を発明しない——**知らない語は「値が悪い」である。**
    """
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        raise BadRequest("not-json") from None

    if not isinstance(payload, dict):
        raise BadRequest("not-an-object")

    if set(payload) - VOICE_KEYS:
        raise BadRequest("unknown-key")
    if set(payload) != VOICE_KEYS:
        raise BadRequest("missing-key")

    text = payload["text"]
    # ⚠️ **1行である。** ⛔ **改行を含む文を鳴らさない**——`say` は行を跨いで
    #    読み、**間の規則（`PAUSE_MS`）は句読点にしか無い**ので、改行は
    #    **規則の外の間**になる。
    if not isinstance(text, str) or "\n" in text or "\r" in text:
        raise BadRequest("bad-value")
    text = text.strip()
    if not text:
        raise BadRequest("bad-value")
    if len(text) > VOICE_MAX_CHARS:
        raise BadRequest("too-long")
    return text


def parse_request(line: str) -> tuple[str, str, str | None]:
    """**1行を、窓・事象・作業に割る。** ⛔ **読めない行は、理由の符号を付けて断る。**

    ⚠️ **時刻はここに無い。** クライアントは時計を持たない。
    """
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        raise BadRequest("not-json") from None

    if not isinstance(payload, dict):
        raise BadRequest("not-an-object")

    if set(payload) - REQUEST_KEYS:
        raise BadRequest("unknown-key")
    if not REQUIRED_KEYS <= set(payload):
        raise BadRequest("missing-key")

    session = payload["session"]
    event = payload["event"]
    if (
        not isinstance(session, str)
        or not isinstance(event, str)
        or not session
        or not event
    ):
        raise BadRequest("bad-value")

    try:
        hooks.classify(event)
    except hooks.UnknownEvent:
        raise BadRequest("unknown-event") from None

    work = payload.get("work")
    if work is None:
        return session, event, None
    if not isinstance(work, str) or work not in work_words.WORK_WORDS:
        # ⛔ **知らない語を `other` に落とさない**——落とせば、クライアントの
        #    綴りの誤りが「その他の作業」として静かに光る。
        raise BadRequest("bad-value")
    return session, event, work


class NextRoom:
    """**1つの部屋と1つの層。** 時刻は値で受けるので、試験は時計を止められる。"""

    def __init__(
        self,
        *,
        presence: str = DEFAULT_PRESENCE,
        motion: bool = DEFAULT_MOTION,
        sound: bool = DEFAULT_SOUND,
    ) -> None:
        if presence not in PRESENCES:
            raise ValueError(presence)
        self.presence = presence
        self._layer = Presence(
            presence=presence,
            room=Focus(Companion(motion=motion, sound=sound)),
        )

    @property
    def held(self) -> str | None:
        """**いま見ている窓。** ⚠️ 部屋のものであり、この層のものではない。"""
        return self._layer.held

    @property
    def dropped(self) -> int:
        """**捨てた身振りの数。**"""
        return self._layer.room.companion.dropped

    @property
    def deadline(self) -> float | None:
        """**次に目を覚ますべき時刻。** ⚠️ **部屋の期限と点滅の期限の早い方である。**"""
        return self._layer.deadline

    def offer(self, session: str, event: str, at: float,
              quiet: bool = False, work: str | None = None) -> Decision:
        """**事象を1つ受け取り、判定を返す。** ⚠️ **時刻は値で来る。**"""
        return self._layer.offer(session, event, at, quiet=quiet, work=work)

    def tick(self, at: float) -> Decision | None:
        """**事象の無い時刻を1つ進める。** 何も変わらなければ `None`。"""
        return self._layer.tick(at)


__all__ = [
    "REQUIRED_KEYS",
    "OPTIONAL_KEYS",
    "REQUEST_KEYS",
    "CLIENT_TIMEOUT",
    "MAX_LINE",
    "socket_path",
    "meta_socket_path",
    "mouth_socket_path",
    "VOICE_KEYS",
    "VOICE_MAX_CHARS",
    "parse_request",
    "parse_voice",
    "NextRoom",
]
