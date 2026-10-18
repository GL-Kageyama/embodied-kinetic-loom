# -*- coding: utf-8 -*-
"""**デーモンの中核。** ソケットも時計も知らない。

⛔ **このファイルは外の世界を読まない。** `time` も `os` も `socket` も無い
（`tools/purity.py` の一覧）。⇒ **同じ行と同じ時刻を渡せば、同じ返事が返る。**
⚠️ **外の世界を読むのは隣の `__main__.py` である。**

⚠️ **1行は1つの事象であり、鍵は2つだけである:**

    {"session": "<session_id>", "event": "<hook_event_name>"}

⛔ **知らない鍵は拒む。** 無視するだけなら `prompt` が同乗できる——
**同乗できないことが、この層のプライバシーである**（`docs/stackchan-daemon.md`）。

⚠️ **クライアントは時刻を送らない。** 時刻は縁が単調時計から取り、
値としてここへ渡す。**層は時計を読まない**（`behaviors.py`）。
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

#: ⚠️ **この2つで全部である。** 増やすことは、契約を増やすことである。
REQUEST_KEYS: frozenset[str] = frozenset({"session", "event"})

#: ⛔ **閉じた集合である。** 断りの符号は、ここに在るものだけである。
REFUSAL_CODES: tuple[str, ...] = (
    "not-json",
    "not-an-object",
    "unknown-key",
    "missing-key",
    "bad-value",
    "unknown-event",
    "too-long",
)

#: ⚠️ **一番長い事象の名前は20字、窓の名前は不透明である。** 4 KiB は余裕であって、
#: 時刻の数ではない。⛔ **行はこの長さを超えたら読まずに断る。**
MAX_LINE = 4096

#: ⚠️ **1つの数であり、両端で使う。** フックはターンを塞いではならない。
#: ⛔ **クライアントが行を届けないうちに閉じる**——待ち続けるデーモンは、
#: 次の事象も受け取れない。
CLIENT_TIMEOUT = 0.1


def socket_path(uid: int) -> str:
    """**ソケットの場所。** ⚠️ **デーモンとクライアントが共有する、1つの綴りである。**

    ⛔ **`/tmp` の下である。** macOS の `sun_path` は104バイトであり、
    `/var/folders/…` の下の `$TMPDIR` は、長いユーザー名でそこへ届く。
    ⚠️ **uid を値として受ける**——この関数は環境を読まない。
    """
    return f"/tmp/ekl-stackchan-{uid}.sock"


class BadRequest(ValueError):
    """**読めない行。** `code` は `REFUSAL_CODES` のどれかである。"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def parse_request(line: str) -> tuple[str, str]:
    """**1行を、窓と事象に割る。** ⛔ **読めない行は、理由の符号を付けて断る。**

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
    if set(payload) != REQUEST_KEYS:
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

    return session, event


def row(decision: Decision, at: float, session: str | None) -> dict:
    """**返事の1行。** ⚠️ **欄の並びは `Decision.as_row` に1つだけ在る。**"""
    return {"ok": True, **decision.as_row(at, session)}


def refusal(code: str) -> dict:
    """**断りの1行。** ⛔ **事象として扱わない**——段階も顔も動かない。"""
    return {"ok": False, "error": code}


class Room:
    """**1つの部屋。** `Focus` と `Companion` を1つずつ持ち、時刻は値で受ける。

    ⚠️ **外の世界を読まないので、試験は時計を止めたまま走れる。**
    """

    def __init__(self, *, motion: bool = DEFAULT_MOTION, sound: bool = DEFAULT_SOUND) -> None:
        self._focus = Focus(Companion(motion=motion, sound=sound))

    @property
    def held(self) -> str | None:
        """**いま見ている窓。** `None` なら、まだ誰も見ていない。"""
        return self._focus.held

    @property
    def dropped(self) -> int:
        """**捨てた身振りの数。** 近すぎた身振りは、並べずに捨てる。"""
        return self._focus.companion.dropped

    @property
    def deadline(self) -> float | None:
        """**次に目を覚ますべき時刻。** `None` なら、事象だけを待つ。"""
        return self._focus.deadline

    def offer(self, session: str, event: str, at: float,
              quiet: bool = False) -> Decision:
        """**窓を名乗る事象を1つ受け取り、判定を返す。**

        ⚠️ **`quiet` は、縁が読んだ「静かな時間」である**（`quiet.py`）。
        ⛔ **ここで時計を読まない**——時刻は値で来る。**同じ値なら、同じ返事である。**
        """
        return self._focus.offer(session, event, at, quiet=quiet)

    def tick(self, at: float) -> Decision | None:
        """**事象の無い時刻を1つ進める。** 何も変わらなければ `None`。"""
        return self._focus.tick(at)


__all__ = [
    "REQUEST_KEYS",
    "REFUSAL_CODES",
    "MAX_LINE",
    "CLIENT_TIMEOUT",
    "socket_path",
    "BadRequest",
    "parse_request",
    "row",
    "refusal",
    "Room",
]
