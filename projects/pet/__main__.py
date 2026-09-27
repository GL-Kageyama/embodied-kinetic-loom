# -*- coding: utf-8 -*-
"""**見るための入口。** `python3 -m projects.pet`（リポジトリの根から走らせる）。

⛔ **このファイルは、このリポジトリで `time` を import してよい唯一の場所である。**
`engine/` は `time` を import しない（`tests/test_purity.py`）——**ループは時計を
呼ぶ側から受け取る。** **その「呼ぶ側」が、ここである。**
⚠️ **`tests/test_pet_purity.py` は、このファイルだけを名指しで除く**——
**除いたことが検査の中に書いてある**（[[measured-scope-vs-claimed-scope]]）。

⚠️ **この入口は、決定 A を目で見るために在る。**
**「保って「猫」と名乗る」は、描いてみないと確かめられない。**
"""
from __future__ import annotations

import argparse
import sys
import time

from .expressions import State
from .screen import Screen


class RealClock:
    """⚠️ **本物の時計。** `engine/backend/cycle.py` の `Clock` と同じ2つを持つ。"""

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m projects.pet",
        description="Pet の顔を端末に出す——⛔ 運動は出さない（Core はまだ繋がっていない）",
    )
    parser.add_argument(
        "--state",
        choices=[state.value for state in State],
        default=None,
        help="1つだけ出して終わる。省略すると5つを順に回す",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.5,
        help="回すときの間隔（秒）。既定 1.5",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help=(
            "同期更新（CSI ? 2026 h/l）を使う。"
            "⚠️ 端末が対応しているかは測っていないので、既定では使わない"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    screen = Screen(sys.stdout, synchronised=args.sync)
    clock = RealClock()

    try:
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
