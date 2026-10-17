# -*- coding: utf-8 -*-
"""**焼く前の入口。** `python3 -m projects.stackchan`（リポジトリの根から走らせる）。

⛔ **このファイルは外の世界を読む**——言語のためだけである
（`projects/**/__main__.py` は縁であり、`tests/test_pet_purity.py` が名指しで除く）。
⛔ **時計は読まない。** 時刻は `--event NAME@秒` の台本として渡す。
⇒ **同じ台本は同じ列を印字する。** 「焼く前に確かめられる」とは、そういう意味である。

⚠️ **窓を名乗る台本も書ける**——`--event 窓:NAME@秒`。窓を書かなければ `main` である。
**2つ以上の窓が在れば、注目は1つだけ持ち、外れにくい**（`behaviors.Focus`）——
**片方の窓の事象は、部屋を起きたままにして、何も表さない。**

⚠️ **この入口は、まだフックに繋がっていない。** フックは1事象につき1プロセスを起こすが、
`Companion` は1つのプロセスの中で段階と期限を持つ。
⇒ **その橋はまだ無い。** `README.md` の「フックにまだ要るもの」を読むこと。

⚠️ **台本の時刻は、戻ってはならない。** 戻った台本は、この層の前提
（時計は前へ進む）を破る——**黙って走らせず、断る。**
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from projects.pet import strings
from projects.pet.expressions import FACES, State

from . import hooks
from .behaviors import (
    DEFAULT_MOTION,
    DEFAULT_SESSION,
    DEFAULT_SOUND,
    IDLE_SECONDS,
    Companion,
    Decision,
    Focus,
)

SESSION_WIDTH = 8
EVENT_WIDTH = 20
PHASE_WIDTH = 9
FACE_WIDTH = 9
LIGHT_WIDTH = 8
BODY_WIDTH = 9
GESTURE_WIDTH = 7
TIME_WIDTH = 9


def language_of(argv: list[str]) -> str:
    """**言語だけを先に読む。** ⚠️ **環境を読むのはこの入口である**——
    `--lang` を読む規則は `projects.pet.strings` と1か所を共有する。
    """
    return strings.language_of(argv, os.environ.get(strings.ENV_VAR))


def _event(text: str) -> tuple[str, str, float]:
    """`NAME`、`NAME@秒`、`窓:NAME@秒` を、窓・名前・時刻に割る。

    ⚠️ **窓を書かなければ `main` である。** 1つの窓しか無い台本は、
    **この欄が増える前と同じに読める。**
    """
    head, sep, at = text.partition("@")
    session, colon, name = head.partition(":")
    if not colon:
        session, name = DEFAULT_SESSION, head
    if not session or not name:
        raise argparse.ArgumentTypeError(
            f"not NAME, NAME@SECONDS or SESSION:NAME@SECONDS: {text!r}"
        )
    try:
        return session, name, float(at) if sep else 0.0
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

    parser = argparse.ArgumentParser(prog="python3 -m projects.stackchan",
                                     description=t("description"))
    parser.add_argument("--motion", type=_switch, default=DEFAULT_MOTION,
                        metavar="on|off", help=t("help_motion"))
    parser.add_argument("--sound", type=_switch, default=DEFAULT_SOUND,
                        metavar="on|off", help=t("help_sound"))
    parser.add_argument("--event", type=_event, action="append", default=[],
                        help=t("help_event"))
    parser.add_argument("--table", action="store_true", help=t("help_table"))
    parser.add_argument("--json", action="store_true", help=t("help_json"))
    parser.add_argument("--lang", default=None, choices=list(strings.SUPPORTED),
                        help=t("help_lang"))
    return parser


def table() -> list[dict]:
    """**33の分類。** ⚠️ **分類そのものは `hooks.py` に1つだけ在る。**"""
    rows = []
    for event in hooks.EVENTS:
        reaction = hooks.classify(event)
        rows.append({
            "event": event,
            "kind": reaction.kind.value,
            "why": reaction.why,
        })
    return rows


def table_lines(rows: list[dict]) -> list[str]:
    lines = [f"{'event':<{EVENT_WIDTH}}  {'kind':<10}  why"]
    for row in rows:
        lines.append(f"{row['event']:<{EVENT_WIDTH}}  {row['kind']:<10}  {row['why']}")
    return lines


def _row(decision: Decision, at: float, session: str | None) -> dict:
    """⚠️ **欄の並びは `Decision.as_row` に1つだけ在る。** デーモンと同じ写しを使う。"""
    return decision.as_row(at, session)


def _entry(entry: tuple) -> tuple[str, str, float]:
    """**台本の1行を、窓・事象・時刻に揃える。** ⚠️ 窓の無い行は `main` である。"""
    if len(entry) == 3:
        return entry[0], entry[1], entry[2]
    name, at = entry
    return DEFAULT_SESSION, name, at


def trace(events: list[tuple], motion: bool, sound: bool) -> list[dict]:
    """**台本を1本走らせる。**

    ⚠️ **事象の時刻に、まず刻みを1つ打つ。** 前の表情がその時刻で尽きていれば、
    **その失効が1行として出る**——**見えないところで顔が戻ると、台本が読めない。**
    ⛔ **身振りは記号のままである。** `sent` はどの行でも `False` である。

    ⚠️ **行は窓を名乗る。** 2つ以上の窓が同じ台本に在るとき、
    **どちらの窓を見ているかは、判定の中身ではなく、行の並びでしか読めない。**
    """
    focus = Focus(Companion(motion=motion, sound=sound))
    rows: list[dict] = []
    previous: float | None = None

    for entry in events:
        session, name, at = _entry(entry)
        if previous is not None and at < previous:
            raise ValueError(previous, at)
        previous = at

        settled = focus.tick(at)
        if settled is not None:
            rows.append(_row(settled, at, None))
        rows.append(_row(focus.offer(session, name, at), at, session))

    if events:
        last = _entry(events[-1])[2]
        # ⚠️ **休息は、最後の事象から IDLE_SECONDS 後に1度だけ見せる。**
        slept = focus.tick(last + IDLE_SECONDS + 1.0)
        if slept is not None:
            rows.append(_row(slept, last + IDLE_SECONDS + 1.0, None))

    return rows


def trace_lines(rows: list[dict]) -> list[str]:
    """**選ばれた顔は、絵でも出す。** ⚠️ 変わらない顔は `-` である。"""
    lines = [
        f"{'at':>{TIME_WIDTH}}  {'who':<{SESSION_WIDTH}}  {'event':<{EVENT_WIDTH}}  "
        f"{'phase':<{PHASE_WIDTH}}  {'face':<{FACE_WIDTH}}  {'light':<{LIGHT_WIDTH}}  "
        f"{'body':<{BODY_WIDTH}}  {'gest':<{GESTURE_WIDTH}}  snd  reason"
    ]
    for row in rows:
        session = row["session"] or "(tick)"
        event = row["event"] or "-"
        face = row["face"] or "-"
        gesture = row["gesture"] or "-"
        lines.append(
            f"{row['at']:>{TIME_WIDTH}.3f}  {session:<{SESSION_WIDTH}}  "
            f"{event:<{EVENT_WIDTH}}  "
            f"{row['phase']:<{PHASE_WIDTH}}  {face:<{FACE_WIDTH}}  "
            f"{row['light']:<{LIGHT_WIDTH}}  {row['body']:<{BODY_WIDTH}}  "
            f"{gesture:<{GESTURE_WIDTH}}  {'yes' if row['sound'] else '-':<3}  "
            f"{row['reason']}"
        )
        if row["face"] is not None:
            lines.extend(f"  {line}" for line in FACES[State(row["face"])])
    return lines


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    lang = language_of(raw)
    args = build_parser(lang).parse_args(raw)
    show_table = args.table or not args.event

    try:
        rows = table() if show_table else trace(args.event, args.motion, args.sound)
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

    print("\n".join(table_lines(rows) if show_table else trace_lines(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
