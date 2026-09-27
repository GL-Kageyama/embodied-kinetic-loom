# -*- coding: utf-8 -*-
"""**見るための入口。** `python3 -m projects.pet`（リポジトリの根から走らせる）。

⛔ **このファイルは、このリポジトリで外の世界を読んでよい唯一の場所である。**
`engine/` は `time` も `os` も import しない（`tests/test_purity.py`）——
**ループは時計を呼ぶ側から受け取り、言語は環境から受け取る。**
**その「呼ぶ側」が、ここである。**
⚠️ **`tests/test_pet_purity.py` は、このファイルだけを名指しで除く**——
**除いたことが検査の中に書いてある**。

⚠️ **この入口は、決定 A を目で見るために在る。**
**「保って「猫」と名乗る」は、描いてみないと確かめられない。**

✅ **2026-09-28、運動が繋がった。** `--motion <名>` は、
**`motions/<名>.json` の `Motion Intent` を読み、軌道を計算し、門を通し、
Mock へ送りながら、同じ時計で顔を出す。**
⛔ **送り先は Mock であって、機体ではない**（シリアル層は機体の世代待ち）。

✅ **同日、外の世界を読むものが1つ増えた。** この入口は `os.environ` を読む——
**言語を決めるためである**（`--lang` > 環境変数 > `en`）。**核はこれを読めない。**
⚠️ **文は1つもここに無い。** 雛形は `locales/`、引くのは `strings.py`、
報告を組むのは `report.py` である。
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from engine.backend.mock import MockBox

from . import strings
from .expressions import State
from .motion import demo_rig, load_expression, perform
from .report import report
from .screen import CLOSE, Screen


class RealClock:
    """⚠️ **本物の時計。** `engine/backend/cycle.py` の `Clock` と同じ2つを持つ。"""

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def language_of(argv: list[str]) -> str:
    """**言語だけを先に読む。** ⛔ **これが要る理由。**

    ヘルプの文そのものが翻訳されるので、**本物の parser を組む前に言語が要る。**
    ゆえに、ここで `--lang` だけを読む——**知らない引数は素通しする**（`parse_known_args`）。
    ⚠️ **環境を読むのはこの関数の呼ぶ側である**（`strings.resolve` は値しか受け取らない）。
    """
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--lang", default=None)
    known, _ = pre.parse_known_args(argv)
    return strings.resolve(known.lang, os.environ.get(strings.ENV_VAR))


def build_parser(lang: str) -> argparse.ArgumentParser:
    """⚠️ **`lang` を引数で受ける。** 既定へ落ちる道を作らないためである。"""
    def t(name: str) -> str:
        return strings.text("pet_cli", name, lang)

    parser = argparse.ArgumentParser(prog="python3 -m projects.pet",
                                     description=t("description"))
    parser.add_argument(
        "--state",
        choices=[state.value for state in State],
        default=None,
        help=t("help_state"),
    )
    parser.add_argument("--motion", default=None, help=t("help_motion"))
    parser.add_argument("--interval", type=float, default=1.5, help=t("help_interval"))
    parser.add_argument("--sync", action="store_true", help=t("help_sync"))
    parser.add_argument("--lang", default=None, choices=list(strings.SUPPORTED),
                        help=t("help_lang"))
    return parser


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    lang = language_of(raw)
    args = build_parser(lang).parse_args(raw)
    screen = Screen(sys.stdout, synchronised=args.sync)
    clock = RealClock()

    try:
        if args.motion is not None:
            rig = demo_rig()
            # ⚠️ **顔も運動も、同じ時計から出る。** それが [06] §11-8 の規則である。
            # ⚠️ **箱のモーターは、対応が届いている数だけである**——
            # **送らないモーターの位置を 0 として並べない。**
            take = perform(load_expression(args.motion), rig, clock=clock,
                           screen=screen, box=MockBox(motors=rig.motors()))
            # ⚠️ **`CLOSE` は画面のものである。** ここで改行を書くと、
            # **端末の作法が2箇所に住む。**
            print(CLOSE + report(take, args.motion, lang), end="")
            return 0

        if args.state is not None:
            screen.draw(State(args.state))
            return 0

        while True:
            for state in State:
                screen.draw(state)
                clock.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        # ⛔ **借りた端末を返す。** Ctrl-C でもここを通る。
        screen.close()


if __name__ == "__main__":
    raise SystemExit(main())
