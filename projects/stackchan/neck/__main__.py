# -*- coding: utf-8 -*-
"""**首を、エンジンの軌道で動かす入口。** リポジトリの根から:

    python3 -m projects.stackchan.neck \\
        --port /dev/cu.usbmodem101 \\
        --start 80 500 --end 350 500 \\
        --duration 0.6 --period 0.02 --hold 0.6

⛔ **このファイルは外の世界を読む**——時計と、ポートと、`argv` である
（`projects/**/__main__.py` は縁であり、`tests/test_pet_purity.py` が名指しで除く）。
**純粋な半分は `motion.py` に在り、そこは `time` も `os` も読まない。**

⚠️ **書く経路はデーモンと同じである**——1行ごとに `os.open` / `os.write` / `os.close`、
**ポートを持たない。** フレームの間、`bench` と `idf.py` はポートの持ち主のままである。
（`pyserial` は開いた拍子に DTR と RTS を立て、この基板を再起動する——測ったことである。）

⛔ **黙って終わらない。** 開けなかった行は1つ目で止め、終了コード 1 で終わる。
**送ったつもりの列を、送らなかった列として残さない。**

⚠️ **`--hold` が要るのは、基板が 500 ms の沈黙でトルクを落とすからである**
（`main/main.cpp` の見張り）。動きが終わってすぐ黙ると、首はその場で自由になる。
**この数は呼ぶ側のものであり、既定はその場の判断である。**
"""
from __future__ import annotations

import argparse
import os
import sys
import time

from engine.backend.protocol_stackchan import FrameRefused
from engine.backend.protocol_stackchan_pose import Pose

from .motion import Motion, motion

#: ⚠️ **この基板が受け取った刻みである**——2026-10-18、20 ms × 678 姿勢、断られたもの0。
#: ⛔ **機体の数ではない。** 変えてよいが、変えたことは測り直すまで主張にならない。
DEFAULT_PERIOD = 0.02

#: ⚠️ **暫定である。** 最初に詰めるのはこの数であり、著者の目が決める。
DEFAULT_DURATION = 0.6

#: ⚠️ **基板の 500 ms より長いこと。** 短いと、動きの終わりでトルクが落ちる。
DEFAULT_HOLD = 0.6


def _wait_until(deadline: float) -> float:
    """**絶対の期限まで待ち、超過した秒を返す。**

    ⚠️ **相対の `sleep(period)` を重ねない。** 1行ごとの誤差が積もり、
    **20 ms と言いながら 25 ms で流れる**——それは送った列ではなく、送りたかった列である。

    ⛔ **「遅れた」を真偽で返さない。** 期限にちょうど着くのは遅刻ではなく、
    最初の標本（`t = 0`）は**必ずその瞬間に居る**——真偽で返すと、その1行が常に遅刻になる。
    超過を秒で返し、意味は呼ぶ側が決める。
    """
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            return -remaining
        time.sleep(min(remaining, 0.1))


def _write(path: str, line: bytes) -> bool:
    """**1行を、開いて、書いて、閉じる。** ⛔ 半分書けた行は成功ではない。"""
    fd = os.open(path, os.O_WRONLY | os.O_NOCTTY)
    try:
        written = os.write(fd, line)
    finally:
        os.close(fd)
    return written == len(line)


def _stream(port: str, plan: Motion, hold: float) -> int:
    """**標本の時刻を追って書き、最後の姿勢を `hold` 秒だけ保つ。**"""
    start = time.monotonic()
    late = 0
    for step in plan.steps:
        # ⚠️ **半周期を超えて遅れた行だけを数える**——期限ちょうどは遅刻ではない。
        if _wait_until(start + step.t) > plan.period / 2.0:
            late += 1
        try:
            ok = _write(port, step.line)
        except OSError as exc:
            print(f"neck: {port}: {exc.strerror}", file=sys.stderr)
            return 1
        if not ok:
            print(f"neck: {port}: short write", file=sys.stderr)
            return 1

    last = plan.last.line
    end = start + plan.duration + hold
    held = 0
    while True:
        now = time.monotonic()
        if now >= end:
            break
        try:
            if not _write(port, last):
                print(f"neck: {port}: short write", file=sys.stderr)
                return 1
        except OSError as exc:
            print(f"neck: {port}: {exc.strerror}", file=sys.stderr)
            return 1
        held += 1
        _wait_until(now + plan.period)

    print(
        f"neck: {plan.count} poses over {plan.duration:.2f} s,"
        f" then {held} held ({hold:.2f} s), {late} late, to {port}",
        file=sys.stderr,
    )
    return 0


def _dry_run(plan: Motion) -> int:
    """**線へ出さず、出したはずの行を stdout へ。** ⚠️ バイト列そのままである。"""
    out = sys.stdout.buffer
    for step in plan.steps:
        out.write(step.line)
    out.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="projects.stackchan.neck",
        description="Move machine 2's neck along an engine trajectory.",
    )
    parser.add_argument("--port", help="write the pose lines here (e.g. /dev/cu.usbmodem101)")
    parser.add_argument("--dry-run", action="store_true",
                        help="write the lines to stdout instead of a port")
    parser.add_argument("--start", type=int, nargs=2, required=True,
                        metavar=("YAW", "PITCH"), help="tenths of a degree, e.g. --start 80 500")
    parser.add_argument("--end", type=int, nargs=2, required=True,
                        metavar=("YAW", "PITCH"), help="tenths of a degree, e.g. --end 350 500")
    parser.add_argument("--duration", type=float, default=DEFAULT_DURATION)
    parser.add_argument("--period", type=float, default=DEFAULT_PERIOD)
    parser.add_argument("--hold", type=float, default=DEFAULT_HOLD)
    parser.add_argument("--profile", default="min-jerk", choices=("min-jerk", "trapezoid"))
    args = parser.parse_args(argv)

    if bool(args.port) == bool(args.dry_run):
        parser.error("name exactly one of --port or --dry-run")

    starts = Pose(yaw_tenths=args.start[0], pitch_tenths=args.start[1])
    ends = Pose(yaw_tenths=args.end[0], pitch_tenths=args.end[1])
    try:
        plan = motion(starts, ends, args.duration, args.period, profile=args.profile)
    except FrameRefused as exc:
        print(f"neck: refused: {exc}", file=sys.stderr)
        return 2
    except (TypeError, ValueError) as exc:
        print(f"neck: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        return _dry_run(plan)
    return _stream(args.port, plan, args.hold)


if __name__ == "__main__":
    raise SystemExit(main())
