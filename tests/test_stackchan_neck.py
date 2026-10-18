# -*- coding: utf-8 -*-
"""**首の動き——両端は厳密に、間はエンジンの軌道から。**

⛔ **ここが押さえるのは機構である。** 20 ms で流れた列が*滑らかに見えるか*は、
**このファイルの主張ではない**——それは著者の目が決める（`records/2026-10-18-the-gestures.md`）。
**このファイルが言うのは、送られる行が測った両端に着き、その間が補間されている、ということだけである。**
"""
from __future__ import annotations

import ast
import os
import pathlib
import subprocess
import sys
import time

import pytest

from engine.backend.protocol_stackchan_pose import Pose, decode
from projects.stackchan.neck import motion as motion_of

ROOT = pathlib.Path(__file__).resolve().parent.parent
NECK = ROOT / "projects" / "stackchan" / "neck" / "motion.py"

#: ⚠️ **2026-10-18 に測った五つの姿勢である**（`projects/stackchan-firmware/main/main.cpp`）。
#: ⛔ **ここへ写すのは、両端が動かないことを見るためであり、表の正本は基板の側である。**
MEASURED = {
    "look_up": Pose(80, 500),
    "look_side": Pose(350, 500),
    "rest": Pose(0, 30),
    "nod_down": Pose(80, 30),
    "recoil": Pose(-80, 700),
}


def _lines(plan) -> list[bytes]:
    return [step.line for step in plan.steps]


@pytest.mark.parametrize("name", sorted(MEASURED))
def test_the_ends_are_exactly_the_ones_named(name):
    """⛔ **丸め誤差で目標に届かない、という失敗を作らない。**"""
    starts = Pose(0, 500)
    ends = MEASURED[name]
    plan = motion_of(starts, ends, 0.6, 0.02)
    assert plan.steps[0].pose == starts
    assert plan.last.pose == ends


@pytest.mark.parametrize("name", sorted(MEASURED))
def test_every_line_round_trips_through_the_decoder(name):
    """**送る列は、基板が読む規則で読める列である。**"""
    plan = motion_of(Pose(0, 500), MEASURED[name], 0.6, 0.02)
    for step in plan.steps:
        assert decode(step.line) == step.pose


def test_the_step_count_follows_duration_over_period():
    plan = motion_of(Pose(0, 500), Pose(350, 500), 0.6, 0.02)
    assert plan.count == round(0.6 / 0.02) + 1


def test_the_times_are_the_engines_own():
    """⚠️ **送る側は `period` ではなく `Step.t` を追う**——だから時刻が契約である。"""
    plan = motion_of(Pose(0, 500), Pose(350, 500), 0.6, 0.02)
    times = [step.t for step in plan.steps]
    assert times[0] == 0.0
    assert times[-1] == pytest.approx(0.6)
    assert times == sorted(times)


def test_the_same_input_gives_the_same_bytes():
    """**同じ入力なら、同じビット列が出る。** 時刻も乱数も読まない。"""
    first = _lines(motion_of(Pose(-80, 700), Pose(350, 30), 0.45, 0.015))
    second = _lines(motion_of(Pose(-80, 700), Pose(350, 30), 0.45, 0.015))
    assert first == second


def test_no_sample_leaves_the_interval():
    """⛔ **行き過ぎない。** 補間は両端の間を埋めるのであり、越えるのではない。"""
    starts, ends = Pose(80, 500), Pose(350, 30)
    plan = motion_of(starts, ends, 0.6, 0.02)
    for step in plan.steps:
        assert min(starts.yaw_tenths, ends.yaw_tenths) <= step.pose.yaw_tenths
        assert step.pose.yaw_tenths <= max(starts.yaw_tenths, ends.yaw_tenths)
        assert min(starts.pitch_tenths, ends.pitch_tenths) <= step.pose.pitch_tenths
        assert step.pose.pitch_tenths <= max(starts.pitch_tenths, ends.pitch_tenths)


def test_a_moving_axis_never_turns_back():
    """**min-jerk は単調である。** 途中で戻る列は、別の動きである。"""
    plan = motion_of(Pose(0, 500), Pose(350, 500), 0.6, 0.02)
    yaw = [step.pose.yaw_tenths for step in plan.steps]
    assert yaw == sorted(yaw)


def test_the_step_sizes_rise_and_fall():
    """⚠️ **これが「硬くない」の機構的な意味である。** 端で小さく、中ほどで大きい。

    ⛔ **見た目の滑らかさではない。** 速度が 0 から始まり 0 で終わる、という形の主張である。
    """
    plan = motion_of(Pose(0, 500), Pose(350, 500), 0.6, 0.02)
    yaw = [step.pose.yaw_tenths for step in plan.steps]
    sizes = [b - a for a, b in zip(yaw, yaw[1:])]
    assert min(sizes) >= 0
    peak = sizes.index(max(sizes))
    assert len(sizes) // 3 <= peak <= 2 * len(sizes) // 3
    assert sizes[0] < max(sizes) / 3
    assert sizes[-1] < max(sizes) / 3


def test_a_channel_that_does_not_move_stays_exactly_there():
    """⛔ **動かない軸が `nan` にならない。** 台形のジャークは `inf` で、`0.0 * inf` は `nan`。"""
    plan = motion_of(Pose(0, 500), Pose(350, 500), 0.3, 0.02)
    assert {step.pose.pitch_tenths for step in plan.steps} == {500}


def test_a_motion_that_does_not_move_is_still_a_motion():
    plan = motion_of(Pose(80, 500), Pose(80, 500), 0.2, 0.02)
    assert {step.pose for step in plan.steps} == {Pose(80, 500)}


def test_a_trapezoid_reaches_the_same_ends_a_different_way():
    """⚠️ **プロファイルは族である。** 端は同じで、間が違う。"""
    straight = motion_of(Pose(0, 500), Pose(350, 500), 0.6, 0.02)
    fast = motion_of(Pose(0, 500), Pose(350, 500), 0.6, 0.02, profile="trapezoid")
    assert straight.steps[0].pose == fast.steps[0].pose
    assert straight.last.pose == fast.last.pose
    assert _lines(straight) != _lines(fast)


def test_a_pose_the_line_cannot_carry_is_refused():
    """⚠️ **プロトコルの枠は 1800**（機体の枠ではない）。ここで止まる。"""
    with pytest.raises(ValueError):
        motion_of(Pose(0, 500), Pose(1801, 500), 0.2, 0.02)


def test_a_period_that_is_not_positive_is_refused():
    with pytest.raises(ValueError):
        motion_of(Pose(0, 500), Pose(350, 500), 0.6, 0.0)


def _numbers(path: pathlib.Path) -> set[float]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    }


def test_the_pure_half_holds_no_machine_number():
    """⛔ **ゼロ点も、封筒も、床も、このファイルには無い。**

    残ってよい数は、単位の変換（10）と、標本の数え上げ（1, 2）と、0 だけである。
    """
    assert _numbers(NECK) <= {0, 1, 2, 10.0}


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "projects.stackchan.neck", *args],
        cwd=ROOT,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        check=False,
    )


def test_the_dry_run_writes_every_line_and_nothing_else():
    """**線へ出さずに、出したはずの列を見る。**"""
    result = _run("--dry-run", "--start", "0", "500", "--end", "350", "500",
                  "--duration", "0.2", "--period", "0.02")
    assert result.returncode == 0, result.stderr
    lines = [line + b"\n" for line in result.stdout.splitlines()]
    assert len(lines) == round(0.2 / 0.02) + 1
    poses = [decode(line) for line in lines]
    assert poses[0] == Pose(0, 500)
    assert poses[-1] == Pose(350, 500)


def test_waiting_returns_the_overshoot_and_not_a_verdict():
    """⛔ **期限にちょうど着くのは遅刻ではない。**

    2026-10-18、この関数は真偽を返していて、**「遅れた」としか言えない**形だった——
    最初の標本（`t = 0`）は必ずその瞬間に居るので、31行すべてが遅刻と数えられた。
    **常に同じことを言う計器は、計器ではない。**
    """
    from projects.stackchan.neck.__main__ import _wait_until

    began = time.monotonic()
    on_time = _wait_until(began + 0.02)
    assert time.monotonic() - began >= 0.015
    assert 0.0 <= on_time < 0.02

    behind = _wait_until(time.monotonic() - 0.05)
    assert behind >= 0.05


def test_the_edge_names_exactly_one_destination():
    result = _run("--start", "0", "500", "--end", "350", "500")
    assert result.returncode == 2
    assert b"exactly one of --port or --dry-run" in result.stderr


def test_the_edge_refuses_a_pose_the_line_cannot_carry():
    result = _run("--dry-run", "--start", "5000", "500", "--end", "350", "500")
    assert result.returncode == 2
    assert b"refused" in result.stderr
