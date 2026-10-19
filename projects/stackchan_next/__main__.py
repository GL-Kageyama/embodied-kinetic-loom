# -*- coding: utf-8 -*-
"""**焼く前の入口（新しい層）。** `python3 -m projects.stackchan_next`（リポジトリの根から）。

⛔ **このファイルは外の世界を読む**——言語のためだけである
（`projects/**/__main__.py` は縁であり、`tests/test_pet_purity.py` が名指しで除く）。
⛔ **時計は読まない。** 時刻は `--event` の台本として渡す。
⇒ **同じ台本は同じ列を印字する。**

## 台本の書き方

| 書き方 | 意味 |
|---|---|
| `UserPromptSubmit@0` | 事象（窓は `main`） |
| `win2:PreToolUse@1` | 窓を名乗る |
| `PreToolUse[write]@3` | **作業の語を載せる** |

⚠️ **作業の語は角括弧である。** `PreToolUse:write@3` と書けば窓の名前になり、
**静かに別の台本になる**——だから綴りを分けてある。

⛔ **`--work` という旗は無い。** 作業の語は事象に属するものであり、
**台本の行に書かれていなければ、その事象は作業を運んでいない。**
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from projects.pet import strings
from projects.pet.expressions import FACES, State
from projects.stackchan import hooks
from projects.stackchan.behaviors import (
    DEFAULT_MOTION,
    DEFAULT_SESSION,
    DEFAULT_SOUND,
    Companion,
    Focus,
)

from . import work as work_words
from .presence import (
    DEFAULT_PRESENCE,
    PRESENCES,
    Presence,
)

TIME_WIDTH = 9
SESSION_WIDTH = 8
EVENT_WIDTH = 20
WORK_WIDTH = 6
PHASE_WIDTH = 9
FACE_WIDTH = 9
LIGHT_WIDTH = 8
SOUND_WIDTH = 5


def language_of(argv: list[str]) -> str:
    """**言語だけを先に読む。** ⚠️ **環境を読むのはこの入口である。**"""
    return strings.language_of(argv, os.environ.get(strings.ENV_VAR))


def _event(text: str) -> tuple[str, str, str | None, float]:
    """`NAME`、`NAME[work]`、`SESSION:NAME`、`NAME@秒` を割る。

    ⚠️ **角括弧が先である。** 窓の名前と作業の語は、別の欄である。
    """
    head, sep, at = text.partition("@")
    work: str | None = None
    if head.endswith("]") and "[" in head:
        head, _, work = head[:-1].partition("[")
        if work not in work_words.WORK_WORDS:
            raise argparse.ArgumentTypeError(
                f"not one of {work_words.WORK_WORDS}: {work!r}"
            )
    session, colon, name = head.partition(":")
    if not colon:
        session, name = DEFAULT_SESSION, head
    if not session or not name:
        raise argparse.ArgumentTypeError(
            f"not NAME, NAME[work], NAME@SECONDS or SESSION:NAME@SECONDS: {text!r}"
        )
    try:
        return session, name, work, float(at) if sep else 0.0
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a time: {at!r}") from None


def _switch(text: str) -> bool:
    """`on` / `off` を真偽に。⛔ **数ではない**——チャンネルの開閉である。"""
    value = text.strip().lower()
    if value not in ("on", "off"):
        raise argparse.ArgumentTypeError(f"not on or off: {text!r}")
    return value == "on"


def build_parser(lang: str) -> argparse.ArgumentParser:
    """⚠️ **`lang` を引数で受ける。** 既定へ落ちる道を作らないためである。"""
    def t(name: str) -> str:
        return strings.text("stackchan_cli", name, lang)

    parser = argparse.ArgumentParser(prog="python3 -m projects.stackchan_next",
                                     description=t("description"))
    parser.add_argument("--presence", default=DEFAULT_PRESENCE, choices=list(PRESENCES),
                        help=t("help_presence"))
    parser.add_argument("--motion", type=_switch, default=DEFAULT_MOTION,
                        metavar="on|off", help=t("help_motion"))
    parser.add_argument("--sound", type=_switch, default=DEFAULT_SOUND,
                        metavar="on|off", help=t("help_sound"))
    parser.add_argument("--event", type=_event, action="append", default=[],
                        help=t("help_event"))
    parser.add_argument("--json", action="store_true", help=t("help_json"))
    parser.add_argument("--lang", default=None, choices=list(strings.SUPPORTED),
                        help=t("help_lang"))
    return parser


def trace(events: list[tuple], presence: str, motion: bool, sound: bool) -> list[dict]:
    """**台本を1本走らせる。**

    ⚠️ **事象の時刻に、まず刻みを1つ打つ。** 前の表情や点滅がその時刻で尽きていれば、
    **その失効が1行として出る**——見えないところで光や顔が戻ると、台本が読めない。

    ⛔ **身振りは記号のままである。** `sent` はどの行でも `False` である。
    """
    room = Presence(
        presence=presence,
        room=Focus(Companion(motion=motion, sound=sound)),
    )
    rows: list[dict] = []
    previous: float | None = None

    for session, name, work, at in events:
        if previous is not None and at < previous:
            raise ValueError(previous, at)
        previous = at

        expired = room.tick(at)
        if expired is not None:
            rows.append(_row(expired, at, None, None))
        rows.append(_row(room.offer(session, name, at, work=work), at, session, work))

    if events:
        last = events[-1][3]
        slept = room.tick(last + 91.0)
        if slept is not None:
            rows.append(_row(slept, last + 91.0, None, None))

    return rows


def _row(decision, at: float, session: str | None, work: str | None) -> dict:
    """⚠️ **欄の並びは `Decision.as_row` に1つだけ在る。** ここは作業の語を足すだけである。"""
    row = decision.as_row(at, session)
    row["work"] = work
    return row


def trace_lines(rows: list[dict]) -> list[str]:
    """**選ばれた顔は、絵でも出す。** ⚠️ 変わらない顔は `-` である。"""
    lines = [
        f"{'at':>{TIME_WIDTH}}  {'who':<{SESSION_WIDTH}}  {'event':<{EVENT_WIDTH}}  "
        f"{'work':<{WORK_WIDTH}}  {'phase':<{PHASE_WIDTH}}  {'face':<{FACE_WIDTH}}  "
        f"{'light':<{LIGHT_WIDTH}}  {'snd':<{SOUND_WIDTH}}  reason"
    ]
    for row in rows:
        session = row["session"] or "(tick)"
        event = row["event"] or "-"
        face = row["face"] or "-"
        work = row["work"] or "-"
        sound = row["sound"] or "-"
        lines.append(
            f"{row['at']:>{TIME_WIDTH}.3f}  {session:<{SESSION_WIDTH}}  "
            f"{event:<{EVENT_WIDTH}}  {work:<{WORK_WIDTH}}  "
            f"{row['phase']:<{PHASE_WIDTH}}  {face:<{FACE_WIDTH}}  "
            f"{row['light']:<{LIGHT_WIDTH}}  {sound:<{SOUND_WIDTH}}  "
            f"{row['reason']}"
        )
        if row["face"] is not None:
            lines.extend(f"  {line}" for line in FACES[State(row["face"])])
    return lines


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    lang = language_of(raw)
    args = build_parser(lang).parse_args(raw)

    if not args.event:
        sys.stderr.write("no --event: this entry point has no table of its own\n")
        return 2

    try:
        rows = trace(args.event, args.presence, args.motion, args.sound)
    except hooks.UnknownEvent as exc:
        sys.stderr.write(f"unknown event: {exc.args[0]!r}\n")
        return 2
    except ValueError as exc:
        previous, at = exc.args
        sys.stderr.write(
            f"the script runs backwards: {at!r} comes after {previous!r}\n"
        )
        return 2

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    print("\n".join(trace_lines(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
