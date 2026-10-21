# -*- coding: utf-8 -*-
"""**規則 —— いま声をかける価値があるか。** 純粋で、O(1) で、時計を読まない。

⚠️ **規則は表に並ぶ。規則を足すことは、語を足すことである**（§16）——
`candidates.KINDS` に1行、`render.LINES` に1行、ここに1関数。

⛔ **出荷する語は3種である。** `verification-gap` / `fan-out` / `probe-only` は
**測って落とした**（§10.2）——規則の正しさと、規則が鳴ることは別である。
`verification-gap` はこのホストで一度も鳴らなかった。

⚠️ **`long-stretch` は種ではなく、`turn-review` の証拠である**（決定12）。
⛔ **連続25回は25回の道具を要するので、`Stop` で閉じたターンなら
`tools >= 25` が必ず立つ。** ゆえに連続だけのターンは存在しない——
`META_WIDE_TOOLS` と `META_STREAK` が同じ数であることが、その条件である。

⛔ **25回の境目は「呼び出し25回」で置く。** 事象25行（`PreToolUse`＋`PostToolUse`）
で数えれば、**12回の呼び出しで鳴ってしまう。**
"""
from __future__ import annotations

from dataclasses import replace

from .budget import TTL_SECONDS
from .candidates import LONG_AT, Candidate
from .trace import Moment, Trace

#: **180秒。** ⚠️ 閉じたターンの上位3件が 185 / 199 / 209 秒であり、その手前。
#: ⚠️ **感度は鈍い**——120秒にしても live の候補は 13→14、配送は 3→3（§19.5）。
META_TURN_SECONDS = 180.0

#: **呼び出し25回。** ⚠️ **`META_STREAK` と同じ数に保つ**（吸収の条件）。
#: 10に下げると候補は 13→16、50・80に上げても 13——**上げる側は効かない。**
META_WIDE_TOOLS = 25

#: **失敗2回。** ⚠️ 3回にすると0件になる。既存の `CONCERN_AFTER_FAILURES = 3` は
#: **光の規則**であり、言葉はもっと早く出てよい。
META_FAILURES = 2

#: **連続25回。** ⚠️ 数そのものは `candidates.LONG_AT` に在る——**数は1つ、名前が2つ。**
#: `render` も同じ数を見る。
META_STREAK = LONG_AT


def context_pressure(trace: Trace, moment: Moment) -> Candidate | None:
    """**ターン内に `PreCompact` が1回以上。** 前の部分が視界から出た、という証拠。"""
    turn = moment.turn
    if moment.event != "PreCompact" or turn.compactions < 1:
        return None
    if "context-pressure" in turn.fired:
        return None
    turn.fired.add("context-pressure")
    return Candidate(
        kind="context-pressure",
        evidence={"compactions": turn.compactions},
        expires_after=TTL_SECONDS,
    )


def turn_review(trace: Trace, moment: Moment) -> Candidate | None:
    """**閉じたターンが180秒以上、または呼び出し25回以上。**

    ⚠️ **`SessionEnd` は振り返らない。** 去る窓に声をかけても、聞く人がいない。
    ⚠️ **`Stop` を出さずに次のプロンプトで閉じたターンも、既定では振り返らない**
    （`Trace.interrupted` が数える）。§19.4 の実測では live 18/59・11h 11/30 が
    その形であり、**振り返る版は候補 +4/+4・配送 +0 であった**——声は増えず、
    枠だけが埋まる。
    """
    if not moment.closed or moment.event == "SessionEnd":
        return None
    turn = moment.turn
    if "turn-review" in turn.fired:
        return None
    span = moment.at - turn.start
    if span < META_TURN_SECONDS and turn.tools < META_WIDE_TOOLS:
        return None
    turn.fired.add("turn-review")
    return Candidate(
        kind="turn-review",
        evidence={
            "seconds": int(span),
            "tools": turn.tools,
            "longest": turn.longest,
            # ⚠️ **25回に満たなければ語は null である。** そうしなければ、
            # すべての振り返りが「3回続いてる」と言う（§11.1）。
            "word": turn.word if turn.longest >= META_STREAK else None,
        },
        expires_after=TTL_SECONDS,
    )


def failure_loop(trace: Trace, moment: Moment) -> Candidate | None:
    """**ターン内の失敗が2回以上。** ⚠️ **鳴るのは2回目であり、3回目ではない。**"""
    turn = moment.turn
    if moment.event != "PostToolUseFailure" or turn.failures < META_FAILURES:
        return None
    if "failure-loop" in turn.fired:
        return None
    turn.fired.add("failure-loop")
    return Candidate(
        kind="failure-loop",
        evidence={"failures": turn.failures},
        expires_after=TTL_SECONDS,
    )


#: ⚠️ **規則の表である。** 並びは語彙の並びと同じ——**規則が語を生むのではない、
#: 語に規則が1つずつ在る。**
RULES = (context_pressure, failure_loop, turn_review)


def evaluate(
    trace: Trace, moment: Moment, eager: bool = False
) -> tuple[Candidate, ...]:
    """**その瞬間に立つ候補。** ⚠️ **同じターンで同じ語は1回だけである。**

    ⚠️ **`eager` は `--meta eager` のときだけ真である。** そのとき
    `failure-loop` の強さが `high` になり、`Stop` の `additionalContext` で
    渡る（§12.2）。⛔ **割り込みの値段は、1ターンではなく、そのターンの答えである。**
    """
    out = []
    for rule in RULES:
        candidate = rule(trace, moment)
        if candidate is None:
            continue
        if eager and candidate.kind == "failure-loop":
            candidate = replace(candidate, priority="high")
        out.append(candidate)
    return tuple(out)


def observe(
    trace: Trace,
    session: str,
    event: str,
    at: float,
    work: str | None = None,
    eager: bool = False,
) -> tuple[Candidate, ...]:
    """**事象を1つ食わせ、立った候補を返す。** 縁が呼ぶのはこの1つである。

    ⚠️ **`trace.observe` と `evaluate` を分けて置く。** 分けておけば、
    「事象は数えたが規則は当てない」を試験できる——**規則を止めた日に、
    台帳まで止まったかを言える。**
    """
    moment = trace.observe(session, event, at, work)
    if moment is None:
        return ()
    return evaluate(trace, moment, eager=eager)


__all__ = [
    "META_TURN_SECONDS",
    "META_WIDE_TOOLS",
    "META_FAILURES",
    "META_STREAK",
    "RULES",
    "context_pressure",
    "turn_review",
    "failure_loop",
    "evaluate",
    "observe",
]
