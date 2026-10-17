# -*- coding: utf-8 -*-
"""**事象の語彙——Claude Code が名乗る33の名前と、その3つの扱い。**

⚠️ **名前はここで発明しない。** 33個は Claude Code のフック文書の表そのものである
（<https://code.claude.com/docs/en/hooks>、2026-10-18 に読んだ）。
⇒ **表が増えたら、この一覧は古くなる。** そのとき `classify()` は知らない名前を
`UnknownEvent` で断る——**黙って落とさないための、意図した罠である。**

⛔ **33は、3つに分かれる。** 「反応する／しない」の2つではない。

| 種類 | 数 | この層は何をするか |
|---|---|---|
| `transition` | 6 | **段階を変える。** 顔・光・身振りの記号が動く |
| `evidence` | 12 | **読む。** 失敗の連続、待ちの終わり。⛔ 体では表さない |
| `ignored` | 15 | **何も読まない。** それでも生存の証拠である |

⛔ **`ignored` は「届いていない」ではない。** **33のすべてが idle の時計を戻す**——
**長いツールの実行中にロボットが眠らないのは、この規則のためである。**
⚠️ **「反応しない」は「表さない」であって、「見ていない」ではない。**

⛔ **空欄を作らない。** 33のどれにも `why` の符号を付ける。
「書かなかった」ではなく「書かないと決めた、この理由で」である——
**空欄は他人の既定で埋まる。**

符号は15。**どれも文ではなく、閉じた集合である。**

| 符号 | 意味 |
|---|---|
| `session-opens` | セッションが始まった |
| `prompt` | 人の問いが届いた。ターンが開く |
| `waiting` | 機械が人を待っている。**唯一の割り込みである** |
| `turn-over` | ターンが終わった |
| `turn-failed` | ターンが API エラーで死んだ |
| `session-closes` | セッションが去る |
| `tool-call` | 道具の呼び出しは、ターンが生きている証拠である |
| `failure-counted` | 失敗は数える。⛔ 1回では鳴らさない |
| `wait-ended` | 待ちが終わった（拒否も終わりである） |
| `attention` | 注意を求める合図。**体では表さない** |
| `display` | 表示中ずっと鳴る。始まりを持たない |
| `inside-a-turn` | ターンの内側。合図は外側の `Stop` である |
| `context` | セッションの文脈が変わった。体の出来事ではない |
| `same-prompt` | `UserPromptSubmit` の直後に鳴る。同じ問いである |
| `no-behavior` | 数を伴う振る舞いが、まだ無い |

⛔ **`no-behavior` は「振る舞いが無い」ではなく「数を伴う振る舞いが無い」である。**
**語彙は対応表であり、対応表に無い語は語彙に無い**（`references/README.md`）。
⇒ **数を書かずに語を足せば、語彙を1つ増やしたことになる。** それはしない。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# 33 — 文書の表の順に並べる。並びは意味を持たないが、差分は読める。
# ---------------------------------------------------------------------------

EVENTS: tuple[str, ...] = (
    "SessionStart",
    "Setup",
    "UserPromptSubmit",
    "UserPromptExpansion",
    "PreToolUse",
    "PermissionRequest",
    "PermissionDenied",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
    "Notification",
    "MessageDisplay",
    "SubagentStart",
    "SubagentStop",
    "TaskCreated",
    "TaskCompleted",
    "Stop",
    "StopFailure",
    "TeammateIdle",
    "InstructionsLoaded",
    "ConfigChange",
    "CwdChanged",
    "DirectoryAdded",
    "FileChanged",
    "WorktreeCreate",
    "WorktreeRemove",
    "PreCompact",
    "PostCompact",
    "PreModelSwitch",
    "PostModelSwitch",
    "Elicitation",
    "ElicitationResult",
    "SessionEnd",
)


class Kind(Enum):
    """**事象の扱い。** ⛔ **2つではない。**"""

    TRANSITION = "transition"
    EVIDENCE = "evidence"
    IGNORED = "ignored"


# ---------------------------------------------------------------------------
# 6 — 段階を変える。
# ---------------------------------------------------------------------------

TRANSITIONS: tuple[str, ...] = (
    "SessionStart",
    "UserPromptSubmit",
    "PermissionRequest",
    "Stop",
    "StopFailure",
    "SessionEnd",
)

# ---------------------------------------------------------------------------
# 12 — 読む。体では表さない。
# ---------------------------------------------------------------------------

EVIDENCE: tuple[str, ...] = (
    "PreToolUse",
    "PermissionDenied",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
    "Notification",
    "MessageDisplay",
    "SubagentStart",
    "SubagentStop",
    "TaskCreated",
    "TaskCompleted",
    "TeammateIdle",
)

# ---------------------------------------------------------------------------
# 15 — 何も読まない。それでも生存の証拠である。
# ---------------------------------------------------------------------------

IGNORED: tuple[str, ...] = (
    "Setup",
    "UserPromptExpansion",
    "InstructionsLoaded",
    "ConfigChange",
    "CwdChanged",
    "DirectoryAdded",
    "FileChanged",
    "WorktreeCreate",
    "WorktreeRemove",
    "PreCompact",
    "PostCompact",
    "PreModelSwitch",
    "PostModelSwitch",
    "Elicitation",
    "ElicitationResult",
)

REASON_CODES: tuple[str, ...] = (
    "session-opens",
    "prompt",
    "waiting",
    "turn-over",
    "turn-failed",
    "session-closes",
    "tool-call",
    "failure-counted",
    "wait-ended",
    "attention",
    "display",
    "inside-a-turn",
    "context",
    "same-prompt",
    "no-behavior",
)

#: ⛔ **33のすべてに符号がある。** 空欄は無い。
WHY: dict[str, str] = {
    # 遷移
    "SessionStart": "session-opens",
    "UserPromptSubmit": "prompt",
    "PermissionRequest": "waiting",
    "Stop": "turn-over",
    "StopFailure": "turn-failed",
    "SessionEnd": "session-closes",
    # 証拠
    "PreToolUse": "tool-call",
    "PostToolUse": "tool-call",
    "PostToolBatch": "tool-call",
    "PostToolUseFailure": "failure-counted",
    "PermissionDenied": "wait-ended",
    "Notification": "attention",
    "MessageDisplay": "display",
    "SubagentStart": "inside-a-turn",
    "SubagentStop": "inside-a-turn",
    "TeammateIdle": "inside-a-turn",
    "TaskCreated": "inside-a-turn",
    "TaskCompleted": "inside-a-turn",
    # 無視
    "Setup": "context",
    "InstructionsLoaded": "context",
    "ConfigChange": "context",
    "CwdChanged": "context",
    "DirectoryAdded": "context",
    "FileChanged": "context",
    "WorktreeCreate": "context",
    "WorktreeRemove": "context",
    "UserPromptExpansion": "same-prompt",
    "PreCompact": "no-behavior",
    "PostCompact": "no-behavior",
    "PreModelSwitch": "no-behavior",
    "PostModelSwitch": "no-behavior",
    "Elicitation": "no-behavior",
    "ElicitationResult": "no-behavior",
}

#: ⚠️ **1つの表から引く。** 2つ目の分類表を作らない。
KINDS: dict[str, Kind] = (
    {event: Kind.TRANSITION for event in TRANSITIONS}
    | {event: Kind.EVIDENCE for event in EVIDENCE}
    | {event: Kind.IGNORED for event in IGNORED}
)


@dataclass(frozen=True)
class Reaction:
    """**1つの事象の分類。** `kind` が `IGNORED` でも、生存の証拠ではある。"""

    event: str
    kind: Kind
    why: str


class UnknownEvent(KeyError):
    """**一覧に無い名前。** 黙って `no-behavior` に落とすと、表が増えたことが見えなくなる。"""


def classify(event: str) -> Reaction:
    """**名前を1つ受け取り、分類を返す。** 知らない名前は断る。"""
    if event not in EVENTS:
        raise UnknownEvent(event)
    return Reaction(event=event, kind=KINDS[event], why=WHY[event])


__all__ = [
    "EVENTS",
    "Kind",
    "TRANSITIONS",
    "EVIDENCE",
    "IGNORED",
    "REASON_CODES",
    "WHY",
    "KINDS",
    "Reaction",
    "UnknownEvent",
    "classify",
]
