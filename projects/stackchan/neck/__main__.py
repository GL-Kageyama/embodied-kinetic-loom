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
from engine.trajectory.profile import Spring

from .gestures import (
    DEFAULT_DURATION,
    DEFAULT_HOLD,
    DEFAULT_PERIOD,
    DEFAULT_SHARPNESS,
)
from .motion import Motion, motion
from .stream import Stream


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
    """**標本の時刻を追って書き、最後の姿勢を `hold` 秒だけ保つ。**

    ⚠️ **列を追う規則は `stream.py` に1つだけ在る。** デーモンも同じ規則で追う——
    **ここに2つ目の規則を書かない。**
    """
    stream = Stream(period=plan.period, hold=hold)
    stream.start(plan, time.monotonic())
    while True:
        line = stream.line(time.monotonic())
        if line is not None:
            try:
                ok = _write(port, line)
            except OSError as exc:
                print(f"neck: {port}: {exc.strerror}", file=sys.stderr)
                stream.stop(time.monotonic())
                return 1
            if not ok:
                print(f"neck: {port}: short write", file=sys.stderr)
                stream.stop(time.monotonic())
                return 1
            continue

        deadline = stream.deadline
        if deadline is None:
            break
        _wait_until(deadline)

    summary = stream.take_summary()
    assert summary is not None
    print(
        f"neck: {summary.applied} poses over {plan.duration:.2f} s,"
        f" then {summary.held} held ({hold:.2f} s), {summary.late} late, to {port}",
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
    parser.add_argument("--profile", default="min-jerk",
                        choices=("min-jerk", "trapezoid", "spring"))
    parser.add_argument("--sharpness", type=float, default=DEFAULT_SHARPNESS,
                        help="spring only: the shape parameter a (peak speed at u = 1/a)")
    args = parser.parse_args(argv)

    if bool(args.port) == bool(args.dry_run):
        parser.error("name exactly one of --port or --dry-run")

    starts = Pose(yaw_tenths=args.start[0], pitch_tenths=args.start[1])
    ends = Pose(yaw_tenths=args.end[0], pitch_tenths=args.end[1])
    profile = args.profile
    if profile == "spring":
        # ⚠️ **`spring` は名前だけでは決まらない**（`sharpness` を持つ）。ここで実体にする。
        try:
            profile = Spring(args.sharpness)
        except ValueError as exc:
            print(f"neck: {exc}", file=sys.stderr)
            return 2

    try:
        plan = motion(starts, ends, args.duration, args.period, profile=profile)
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
