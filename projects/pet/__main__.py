# -*- coding: utf-8 -*-
"""**見るための入口。** `python3 -m projects.pet`（リポジトリの根から走らせる）。

⛔ **このファイルは、このリポジトリで `time` を import してよい唯一の場所である。**
`engine/` は `time` を import しない（`tests/test_purity.py`）——**ループは時計を
呼ぶ側から受け取る。** **その「呼ぶ側」が、ここである。**
⚠️ **`tests/test_pet_purity.py` は、このファイルだけを名指しで除く**——
**除いたことが検査の中に書いてある**。

⚠️ **この入口は、決定 A を目で見るために在る。**
**「保って「猫」と名乗る」は、描いてみないと確かめられない。**

✅ **2026-09-28、運動が繋がった。** `--motion <名>` は、
**`motions/<名>.json` の `Motion Intent` を読み、軌道を計算し、門を通し、
Mock へ送りながら、同じ時計で顔を出す。**
⛔ **送り先は Mock であって、機体ではない**（シリアル層は機体の世代待ち）。
"""
from __future__ import annotations

import argparse
import sys
import time

from engine.backend.mock import MockBox

from .expressions import State
from .motion import Take, demo_rig, load_expression, perform
from .screen import CLOSE, Screen


class RealClock:
    """⚠️ **本物の時計。** `engine/backend/cycle.py` の `Clock` と同じ2つを持つ。"""

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m projects.pet",
        description=(
            "Pet の顔を端末に出す。--motion を付けると、運動も走る"
            "——⛔ ただし送り先は Mock であって、機体ではない"
        ),
    )
    parser.add_argument(
        "--state",
        choices=[state.value for state in State],
        default=None,
        help="1つだけ出して終わる。省略すると5つを順に回す",
    )
    parser.add_argument(
        "--motion",
        default=None,
        help=(
            "motions/<名>.json の意図を走らせ、同じ時計で顔を出す。"
            "⚠️ 顔は --state ではなく、その名前の表情である"
        ),
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


def report(take: Take, name: str) -> str:
    """⚠️ **何が起きたかを1箇所に書く。** 緑を「成立した」と読ませないためである。"""
    if not take.ran:
        return (f"{name}: ⛔ 計画時に弾かれた——{take.refusal.reason}\n"
                "  ⇒ **1フレームも送っていない。**")

    lines = [
        f"{name}: {' → '.join(take.expression.words)}",
        f"  送った {len(take.sent)} フレーム、刻み {len(take.ticks)}、"
        f"門が保った回 {take.refusals}、諦めた刻み {take.skipped}",
        f"  いちばん遅れた刻み +{take.worst_lateness * 1000:.3f} ms",
        f"  箱の位置 {tuple(round(v, 1) for v in take.arrived)}",
        "  ⛔ 上限を1つも渡していない（すべて None）——"
        "枠（190〜833、実測）以外の検査は鳴っていない",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
            print(CLOSE + report(take, args.motion), end="")
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
