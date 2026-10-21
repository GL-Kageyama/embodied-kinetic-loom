# -*- coding: utf-8 -*-
"""**第3層の台帳 —— 事象から、ターンと数を取り出す。** 時計もファイルも読まない。

⚠️ **観るのは、いま人が見ている窓の事象だけである。** 窓は `STEALS` で移る。
⛔ **その集合は第1層から import する。写さない**（設計 §10.5）——2か所に住めば、
片方が黙って緩んだ日に、もう片方が鳴らない。**第3層が第1層から読むのは、
この集合1つだけである。**

⛔ **「道具1回」は `PreToolUse` の1行である。** `PostToolUse` も数えると、
**1回の呼び出しが2回になる**（実測: `PreToolUse` 1,645 / `PostToolUse` 1,546）。
`work` は両方の事象に載るので、**連続の手数まで水増しされる**——
「25回」と言えば、実際は約12回の呼び出しである。⇒ **数えるのは `PreToolUse` だけ。**

⚠️ **`Stop` / `StopFailure` は窓を移さない。** 機械が終わったことは、
人がその窓を見ていることではない（第1層の `STEALS` の注と同じ理由）。
**ターンは閉じるが、窓は動かない。**

⚠️ **`SessionEnd` はターンを閉じるが、振り返らない。** 去る窓に声をかけても、
聞く人がいない（第1層が `SessionEnd` で鳴らなかったのと同じ理由である）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from projects.stackchan.behaviors import STEALS
from projects.stackchan_next.work import WORK_WORDS

#: ⚠️ **ターンを閉じる事象である。** 第1層の `STEALS` と違い、**窓は移さない**。
CLOSES: frozenset[str] = frozenset({"Stop", "StopFailure", "SessionEnd"})


@dataclass
class Turn:
    """**1つのターン。** 開始時刻と、そのターンで数えたものである。"""

    start: float
    tools: int = 0
    failures: int = 0
    compactions: int = 0
    word: str | None = None
    streak: int = 0
    longest: int = 0
    #: ⚠️ **同じターンで同じ語は1回だけ**（§10.1）。印はここに置く。
    fired: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Moment:
    """**規則が見る1つの瞬間。** 事象と、そのときのターンである。

    ⚠️ **`at` は値で来る。** この型は時計を持たない——**持てば、再生できない。**
    """

    event: str
    at: float
    session: str
    turn: Turn
    work: str | None = None
    opened: bool = False
    closed: bool = False


class Trace:
    """**窓とターンの状態。** 事象を1つ受け取り、見る価値のある瞬間だけを返す。

    ⚠️ **返さない事象は「無かった」のではない。** 背後の窓の事象は数えない、
    という規則の結果である（第1層の `distant` と同じ）。
    """

    def __init__(self) -> None:
        #: ⚠️ **いま人が見ている窓。** `STEALS` の事象だけで移る。
        self.held: str | None = None
        self.turns: dict[str, Turn] = {}
        self.prompts = 0
        self.closed = 0
        #: ⚠️ **`Stop` を出さずに次のプロンプトで閉じたターン。** 数えるが、
        #: 既定では振り返らない（`rules.py` の注）。
        self.interrupted = 0

    def observe(
        self,
        session: str,
        event: str,
        at: float,
        work: str | None = None,
    ) -> Moment | None:
        """**事象を1つ食わせ、規則が見るべき瞬間なら返す。**

        ⛔ **`work` は6語のどれかである。** 知らない語は**断る**——黙って
        `other` に落とせば、綴り違いが「なんらかの作業」として光り、誰も見ない
        （第2層の `work.py` が同じ理由で同じことを決めた）。
        """
        if isinstance(at, bool) or not isinstance(at, (int, float)):
            raise TypeError(f"at は数である: {at!r}")
        at = float(at)
        if work is not None and work not in WORK_WORDS:
            raise ValueError(f"作業の語彙に無い: {work!r}")

        if event in STEALS:
            self.held = session

        if event == "UserPromptSubmit":
            if session != self.held:
                return None
            self.prompts += 1
            old = self.turns.pop(session, None)
            if old is not None:
                self.interrupted += 1
            turn = Turn(start=at)
            self.turns[session] = turn
            return Moment(event=event, at=at, session=session, turn=turn,
                          work=work, opened=True)

        if event in CLOSES:
            turn = self.turns.pop(session, None)
            if turn is None:
                return None
            self.closed += 1
            if session != self.held:
                return None
            return Moment(event=event, at=at, session=session, turn=turn,
                          work=work, closed=True)

        if session != self.held:
            return None
        turn = self.turns.get(session)
        if turn is None:
            return None

        if event == "PreCompact":
            turn.compactions += 1
        elif event == "PreToolUse":
            turn.tools += 1
            if work is not None:
                if work == turn.word:
                    turn.streak += 1
                else:
                    turn.word = work
                    turn.streak = 1
                turn.longest = max(turn.longest, turn.streak)
        elif event == "PostToolUseFailure":
            turn.failures += 1
        else:
            # ⚠️ **`PostToolUse` はここへ来る。** `work` を運ぶが、**数えない**——
            # 数えれば1回の呼び出しが2回になる。
            return None

        return Moment(event=event, at=at, session=session, turn=turn, work=work)


__all__ = ["CLOSES", "Turn", "Moment", "Trace"]
