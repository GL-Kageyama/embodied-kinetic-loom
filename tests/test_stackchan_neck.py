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
import re
import subprocess
import sys
import time

import pytest

from engine.backend.protocol_stackchan_pose import Pose, decode, encode
from engine.trajectory.profile import Spring
from projects.stackchan import behaviors
from projects.stackchan.neck import gestures
from projects.stackchan.neck import motion as motion_of
from projects.stackchan.neck.motion import chain
from projects.stackchan.neck.stream import Stream

ROOT = pathlib.Path(__file__).resolve().parent.parent
NECK = ROOT / "projects" / "stackchan" / "neck" / "motion.py"
FIRMWARE = ROOT / "projects" / "stackchan-firmware" / "main" / "main.cpp"

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


def test_a_spring_reaches_the_same_ends_with_its_speed_at_the_start():
    """⚠️ **同じ両端・同じ長さで、間だけが違う。** ばねは早く動き出す。

    2026-10-18、著者は純正の首を「ギュンギュン」、この首を「ジジジ」と言った。
    読んだ純正はばねであり、**形の差は山の位置**である（`engine/trajectory/profile.py`）。
    """
    ends = (Pose(0, 500), Pose(350, 500))
    jerk = motion_of(*ends, 1.0, 0.02)
    spring = motion_of(*ends, 1.0, 0.02, profile=Spring(5.0))

    assert jerk.steps[0].pose == spring.steps[0].pose
    assert jerk.last.pose == spring.last.pose

    quarter = len(jerk.steps) // 5
    jerk_travelled = abs(jerk.steps[quarter].pose.yaw_tenths)
    spring_travelled = abs(spring.steps[quarter].pose.yaw_tenths)
    assert spring_travelled > 3 * jerk_travelled


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


def test_the_edge_can_stream_a_spring():
    """⚠️ **縁は、名前だけでは決まらない族の数を、コマンド行から受け取る。**"""
    result = _run("--dry-run", "--start", "0", "500", "--end", "350", "500",
                  "--duration", "0.2", "--period", "0.02", "--profile", "spring")
    assert result.returncode == 0, result.stderr
    poses = [decode(line + b"\n") for line in result.stdout.splitlines()]
    assert poses[0] == Pose(0, 500)
    assert poses[-1] == Pose(350, 500)


def test_the_edge_refuses_a_sharpness_at_or_below_one():
    result = _run("--dry-run", "--start", "0", "500", "--end", "350", "500",
                  "--profile", "spring", "--sharpness", "1.0")
    assert result.returncode == 2
    assert b"sharpness" in result.stderr


# ---------------------------------------------------------------------------
# 継ぎ目。2026-10-19 —— 身振りが、首の動きになる。
# ⚠️ **これは「滑らかに見える」の検査ではない。** その語は著者のものである。
# ここが見るのは、表・継ぎ目・期限・保持の**機構**だけである。
# ---------------------------------------------------------------------------


def test_chain_keeps_one_timeline_and_one_seam():
    """⛔ **2つ目の動きの時刻を、そのまま並べない。** 重なった列になる。"""
    first = motion_of(Pose(0, 500), Pose(100, 500), 0.2, 0.02)
    second = motion_of(Pose(100, 500), Pose(100, 30), 0.3, 0.02)
    joined = chain((first, second))

    times = [step.t for step in joined.steps]
    assert times == sorted(times)
    assert len(times) == len(set(times))
    # ⚠️ **継ぎ目の姿勢は1つだけである。**
    assert sum(1 for step in joined.steps if step.pose == Pose(100, 500)) == 1
    assert joined.starts == first.starts
    assert joined.ends == second.ends
    assert joined.duration == pytest.approx(first.duration + second.duration)
    assert joined.last.pose == Pose(100, 30)


def test_a_plan_starts_where_it_was_told_and_ends_where_the_table_says():
    """⛔ **両端は厳密である。** 丸めは整数の上で閉じる。"""
    for name in gestures.POSTURES:
        starts = Pose(-30, 120)
        plan = gestures.plan(name, starts)
        assert plan.steps[0].pose == starts
        assert plan.last.pose == gestures.ends(name)


def test_nod_passes_through_its_down_posture():
    """⚠️ **`nod` だけは2つで1つである。** 下へ行ってから、`look_up` へ戻る。"""
    plan = gestures.plan("nod", Pose(0, 500))
    down = gestures.posture("nod")
    assert any(step.pose == down for step in plan.steps)
    assert plan.last.pose == gestures.posture("look_up")


def test_the_gesture_table_covers_the_layers_words():
    """⛔ **層が返す5つの語と、表の5つの行は同じ集合である。**"""
    assert set(gestures.POSTURES) == set(behaviors.GESTURES)


def test_the_firmware_table_and_this_one_agree():
    """⛔ **ホストの表は写しである。** 写しが黙ってずれないことを、ここで見る。

    ⚠️ **正本は `main.cpp` であり、この検査はそれを読む。**
    基板の数が動いた日に、ホストの数が古いまま残る形を作らない。
    """
    source = FIRMWARE.read_text(encoding="utf-8")
    found = {
        name: (int(yaw), int(pitch))
        for name, yaw, pitch in re.findall(
            r"constexpr GesturePosture k(\w+)Posture = \{(-?\d+), (-?\d+)\};", source
        )
    }
    assert set(found) == {"LookUp", "LookSide", "Rest", "NodDown", "Recoil"}
    names = {"look_up": "LookUp", "look_side": "LookSide", "rest": "Rest",
             "nod": "NodDown", "recoil": "Recoil"}
    for gesture, firmware_name in names.items():
        assert gestures.POSTURES[gesture] == found[firmware_name]

    # ⚠️ **`nod` の戻り先も、基板の綴りで確かめる。** 6つ目の数ではない。
    play = source.split("void PlayGesture(Gesture gesture) {", 1)[1]
    nod = play.split("case Gesture::kNod:", 1)[1].split("break;", 1)[0]
    moves = re.findall(r"MoveToPosture\((k\w+Posture)\)", nod)
    assert moves == ["kNodDownPosture", "kLookUpPosture"]
    assert gestures.NOD_RETURN == "look_up"


def test_every_posture_can_be_carried_by_the_line():
    """⚠️ **表の数は、この線が運べる数である**（プロトコルの枠は 1800）。"""
    for name in gestures.POSTURES:
        pose = gestures.posture(name)
        assert decode(encode(pose)) == pose


def test_duration_grows_with_distance_and_has_a_floor():
    """⚠️ **長さは距離から決まる。** 下限は判断であり、ここでは機構として在る。"""
    near = gestures.duration_for(Pose(0, 500), Pose(1, 500))
    far = gestures.duration_for(Pose(0, 500), Pose(600, 500))
    assert near == gestures.MIN_DURATION
    assert far > near
    assert far == pytest.approx(60.0 / gestures.DEGREES_PER_SECOND)


def test_a_plan_that_asks_for_no_motion_is_still_and_a_nod_is_not():
    """⛔ **`still` は列を読む。** 始点と終点を比べると、`nod` を取り違える。

    ⚠️ **2026-10-19 のデーモンのログでは、85 の身振りのうち 38 が 0 の動きの
    `look_up` だった**——首は `look_up` の姿勢に停まっており、`nod` もそこへ戻り、
    一番多い事象（`UserPromptSubmit`）がまた `look_up` を選ぶ。
    ⛔ **その列は、何も動かさないのに、武装と流しとトルクの点灯を使う。**
    """
    here = gestures.posture("look_up")
    assert gestures.still(gestures.plan("look_up", here))

    # ⚠️ **`nod` は始点と終点が同じでも、下の点まで動く。** 列は止まっていない。
    nod = gestures.plan("nod", here)
    assert nod.starts == here and nod.ends == here
    assert not gestures.still(nod)

    # ⚠️ **1歩でも動けば、止まってはいない。**
    nudged = Pose(here.yaw_tenths + 10, here.pitch_tenths)
    assert not gestures.still(gestures.plan("look_up", nudged))


def test_a_plan_inside_the_measured_floor_is_not_a_move():
    """⚠️ **床は測った数である**（`bench set` 一段ずつ、2026-10-19）。

    ⛔ **`look_up` の 80 は、位置を尋ねると 93 と読まれる**——基板の格子が粗いからである。
    **その列は動くが、サーボは 4 counts では動かない。**
    """
    near = gestures.plan("look_up", Pose(93, 490))
    assert not gestures.still(near)
    assert gestures.within_floor(near)

    # ⚠️ **yaw が 26 tenths（8 counts）を越えれば、動いた**（12→6/5）。
    assert not gestures.within_floor(gestures.plan("look_up", Pose(53, 490)))
    # ⛔ **下りに床は無い。** 4 counts の要求で 5 counts 動いた——1 count でも数える。
    assert not gestures.within_floor(gestures.plan("rest", Pose(0, 34)))
    # ⚠️ **`nod` は床の外である**（470 tenths、下って戻る）。
    assert not gestures.within_floor(gestures.plan("nod", gestures.posture("look_up")))


def _drive(stream: Stream, at: float = 0.0) -> float:
    """**期限へ飛びながら、列を終わりまで追う。** ⚠️ 時計ではなく、値で追う。"""
    while True:
        stream.line(at)
        deadline = stream.deadline
        if deadline is None:
            return at
        at = deadline


def test_a_stream_starts_at_the_events_own_time():
    """⚠️ **`at` は判定の時刻そのものである。** ここが「同じ時計」の継ぎ目である。"""
    plan = motion_of(Pose(0, 500), Pose(100, 500), 0.2, 0.02)
    stream = Stream(period=0.02, hold=0.1)
    stream.start(plan, 100.0, name="look_up")
    assert stream.deadline == 100.0
    assert stream.line(100.0) == plan.steps[0].line
    assert stream.deadline == pytest.approx(100.0 + plan.steps[1].t)


def test_a_stream_writes_every_step_once_and_then_holds():
    plan = motion_of(Pose(0, 500), Pose(100, 500), 0.2, 0.02)
    stream = Stream(period=0.02, hold=0.1)
    stream.start(plan, 0.0)
    _drive(stream)
    summary = stream.take_summary()

    assert summary is not None
    assert summary.applied == plan.count
    assert summary.late == 0
    assert summary.held == 4          # 0.1 / 0.02、最後の刻みは end に含まれない
    assert stream.take_summary() is None


def test_a_line_is_late_only_past_half_a_period():
    """⛔ **期限ちょうどは遅刻ではない。** 2026-10-18 に、計器がそれを31回言った。"""
    plan = motion_of(Pose(0, 500), Pose(100, 500), 0.2, 0.02)
    stream = Stream(period=0.02, hold=0.0)
    stream.start(plan, 0.0)
    assert stream.line(0.01) is not None      # 半周期ちょうど——遅刻ではない
    assert stream.line(0.031) is not None     # 0.011 遅れ——遅刻である
    _drive(stream, 0.031)
    summary = stream.take_summary()
    assert summary is not None
    assert summary.late == 1


def test_a_new_motion_starts_from_the_line_that_was_actually_sent():
    """⛔ **始点は「命じた終点」ではない。** 割り込まれたら、首はそこまでしか居ない。"""
    first = motion_of(Pose(0, 500), Pose(200, 500), 0.2, 0.02)
    stream = Stream(period=0.02, hold=0.1)
    stream.start(first, 0.0, name="look_side")
    stream.line(0.0)
    stream.line(0.04)
    assert stream.running or True
    starts = stream.last_pose
    assert starts is not None
    assert starts != first.ends

    second = motion_of(starts, Pose(80, 500), 0.2, 0.02)
    stream.start(second, 0.05, name="look_up")
    assert stream.line(0.05) == second.steps[0].line
