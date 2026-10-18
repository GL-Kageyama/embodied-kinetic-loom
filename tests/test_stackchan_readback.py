# -*- coding: utf-8 -*-
"""**基板に首の位置を尋ねる。** ⚠️ **推測を、測定に置き換えるための綴りである。**

⛔ **このファイルは本物の端末を開かない。** 端末の代わりは、ただのファイルである——
`bench pos` と答えるのは、この試験が先に書いた2行だけである。
⇒ **基板が何秒で答えるかは、ここでは分からない**（`MEASURE_RETRY` は判断である）。

⚠️ **`main.cpp` の `printf` の綴りを読む。** 尋ねる語も、答える行の形も、
正本は基板の側に在る——ここは写しであり、**食い違った日に赤くなるのが写しの値打ちである。**
"""
from __future__ import annotations

import json
import os
import pathlib
import time

from engine.backend.protocol_stackchan_pose import Pose
from projects.stackchan.daemon import __main__ as edge
from projects.stackchan.daemon.room import Room
from projects.stackchan.neck import readback

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_CPP = REPO_ROOT / "projects" / "stackchan-firmware" / "main" / "main.cpp"

#: ⚠️ **基板が答える形そのものである。** `bench: yaw raw 512, angle 2.5 deg (zero 504)`
ANSWERS = (
    "bench: yaw=ok pitch=ok\n"
    "bench: yaw raw 512, angle 2.5 deg (zero 504)\n"
    "bench: pitch raw 788, angle 2.5 deg (zero 780)\n"
)


# ---------------------------------------------------------------------------
# 綴り。⛔ 正本は基板の側である。
# ---------------------------------------------------------------------------


def test_the_query_and_the_answer_are_the_boards_own_words():
    """⚠️ **尋ねる語も、答える形も、`main.cpp` に在る。** ここは写しである。"""
    source = MAIN_CPP.read_text(encoding="utf-8")
    assert "bench pos" in source
    assert "bench: yaw raw %d, angle %d.%d deg (zero %d)" in source
    assert "bench: pitch raw %d, angle %d.%d deg (zero %d)" in source
    assert readback.QUERY == b"bench pos\n"


def test_the_two_lines_become_one_pose():
    """✅ **2軸そろって、1つの姿勢。** ⚠️ 1カウントは 5/16 度である。"""
    assert readback.parse(ANSWERS) == Pose(yaw_tenths=25, pitch_tenths=25)


def test_a_small_negative_angle_keeps_the_sign_the_print_lost():
    """⛔ **度の欄は読まない。** 1度に満たない負の角は、`0.6` と印字される。

    ⚠️ **C の切り捨てと Python の `//` は、負で違う。** その差が1カウントである。
    """
    delta = (502 - 504) * 50
    assert delta // 16 == -7                  # Python は負の無限大へ
    assert readback.tenths(502, 504) == -6    # C は 0 へ

    # ⚠️ **基板がこの姿勢を印字すると、符号が消える。** raw と zero だけが残る。
    printed = ("bench: yaw raw 502, angle 0.6 deg (zero 504)\n"
               "bench: pitch raw 502, angle 0.6 deg (zero 504)\n")
    assert readback.parse(printed) == Pose(yaw_tenths=-6, pitch_tenths=-6)


def test_one_axis_is_not_a_pose():
    """⛔ **欠けた軸を 0 で埋めない。** 0 は `rest` の yaw と同じ綴りである。"""
    assert readback.parse("bench: yaw raw 512, angle 2.5 deg (zero 504)\n") is None
    assert readback.parse("bench: yaw=no answer pitch=no answer\n") is None
    assert readback.parse("") is None
    assert readback.parse("pose 12 34*41\n") is None


def test_an_answer_without_a_position_is_still_an_answer():
    """⛔ **コンソールの沈黙と、サーボの沈黙は別である。**"""
    quiet = "bench: yaw=no answer pitch=no answer\n"
    assert readback.answered(quiet) is True
    assert readback.parse(quiet) is None
    assert readback.answered("alive\n") is False
    assert readback.answered("") is False


# ---------------------------------------------------------------------------
# 縁。⚠️ 端末の代わりに、ただのファイルを開く。
# ---------------------------------------------------------------------------


def _console(tmp_path: pathlib.Path, text: str = "") -> pathlib.Path:
    path = tmp_path / "console"
    path.write_text(text, encoding="ascii")
    return path


def _first(neck: "edge.Neck") -> "Decision":
    return Room().offer("main", "SessionStart", 1.0)


def test_the_daemon_asks_the_console_and_streams_from_the_answer(tmp_path, capsys):
    """✅ **尋ねた姿勢が、そのまま始点になる。** ⛔ 最初の遷移も流れる。

    ⚠️ **問い合わせは1行、姿勢の行と同じポートに書かれる。**
    """
    path = _console(tmp_path, ANSWERS)
    neck = edge.Neck(str(path))

    assert neck.take(_first(neck), 1.0) is True
    neck._close()

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows[0] == {"position": [25, 25], "at": 1.0}
    assert rows[1]["neck"] == "look_up"
    assert rows[1]["from"] == [25, 25]
    assert rows[1]["to"] == [80, 500]


def test_an_unanswered_query_is_written_and_not_believed(tmp_path, capsys):
    """⛔ **答えの無い端末を、位置として信じない。** 尋ねたことは残る。

    ⚠️ **始点が無いので、最初の身振りは基板が演じる**——`take` は `False`。
    """
    path = _console(tmp_path)
    neck = edge.Neck(str(path))

    assert neck.take(_first(neck), 0.0) is False
    assert "bench pos" in path.read_text(encoding="ascii")
    assert neck._fd is None, "演じさせた後も、ポートを握っている"

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows == [
        {"position": None, "heard": False, "read": "bench pos\n", "at": 0.0}
    ]


def test_the_console_can_answer_without_a_position(tmp_path, capsys):
    """⛔ **答えたが読めない**——その行は、黙った行と違う。

    ⚠️ **2026-10-19 の機体がこの形だった**: `bench scan` は 0 台、`bench pos` は
    `no answer`。**コンソールは生きており、サーボのバスが黙っていた。**
    """
    path = _console(tmp_path, "bench: yaw=no answer pitch=no answer\n")
    neck = edge.Neck(str(path))

    assert neck.take(_first(neck), 0.0) is False
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows == [
        {
            "position": None,
            "heard": True,
            "read": "bench: yaw=no answer pitch=no answer\nbench pos\n",
            "at": 0.0,
        }
    ]


def test_the_probe_is_bounded_by_port_wait(tmp_path):
    """⛔ **答えない端末を、いつまでも待たない。** 上限は `PORT_WAIT` である。"""
    fifo = tmp_path / "console"
    os.mkfifo(fifo)
    neck = edge.Neck(str(fifo))

    started = time.monotonic()
    assert neck.take(_first(neck), 0.0) is False
    elapsed = time.monotonic() - started
    assert elapsed < edge.PORT_WAIT + 1.5, "待ちに上限が無い"


def test_every_gesture_asks_once_and_uses_what_it_hears(tmp_path, capsys):
    """✅ **尋ねるのは身振りの瞬間だけである。** ⛔ 背景では尋ねない。

    ⚠️ **2つ目の身振りも、同じ瞬間に尋ねる**——前の答えを覚えて使い回さない。
    （この試験台は普通のファイルなので、2度目も同じ2行を読む。**それは試験台の
    性質である**: 本物の tty では、読んだ答えは消える。）
    """
    path = _console(tmp_path, ANSWERS)
    neck = edge.Neck(str(path))

    at = 1.0
    assert neck.take(_first(neck), at) is True
    t = at
    while neck.deadline is not None or neck._fd is not None:
        neck.pump(t)
        t += edge.gestures.DEFAULT_PERIOD
        assert t < at + 30.0, "流れが終わらない"

    second = Room().offer("main", "PermissionRequest", t)
    assert neck.take(second, t) is True
    neck._close()

    text = path.read_text(encoding="ascii")
    assert text.count("bench pos") == 2

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    necks = [row for row in rows if "from" in row]
    assert [row["neck"] for row in necks] == ["look_up", "look_side"]
    assert all(row["from"] == [25, 25] for row in necks)
