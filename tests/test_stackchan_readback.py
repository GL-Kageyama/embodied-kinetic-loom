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
    # ⚠️ **0.19.62 の行である。** ⛔ **この写しが赤くなる日が、綴りが離れた日である。**
    assert "bench: servo strikes=%d rail=%d" in source
    # ⛔ **順序も綴りの一部である。** ホストは姿勢が読めた時点で窓を閉じるので、
    #    **この行が姿勢の行より後ろにあれば、誰にも読まれない。**
    assert (source.index("bench: servo strikes=%d rail=%d")
            < source.index("bench: yaw raw %d"))
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


def test_the_verdict_is_the_boards_own_count():
    """✅ **基板が自分の数で言った判定を読む。** ⛔ ホストの `applied` とは別の数である。

    ⚠️ **この行の正本も `main.cpp` に在る**（`PoseWatchdog`）。ここは写しである。
    """
    source = MAIN_CPP.read_text(encoding="utf-8")
    assert 'pose: %d applied, %d refused, %d clamped' in source

    found = readback.verdict(
        "pose: stream lost after 500 ms — torque released\n"
        "pose: 41 applied, 2 refused, 3 clamped\n"
    )
    assert found == {"applied": 41, "refused": 2, "clamped": 3}


def test_a_window_with_two_verdicts_keeps_the_last():
    """⚠️ **新しい方が効いている。** ⛔ 古い判定を、今の流しの判定として読まない。"""
    text = ("pose: 10 applied, 0 refused, 0 clamped\n"
            "pose: 41 applied, 1 refused, 0 clamped\n")
    assert readback.verdict(text) == {"applied": 41, "refused": 1, "clamped": 0}


def test_nothing_printed_is_not_a_verdict_of_zero():
    """⛔ **「何も言わなかった」と「断らなかった」は別である。**

    ⚠️ 位置の答えは判定ではない——2つの綴りは、同じ窓に並んで届く。
    """
    assert readback.verdict("") is None
    assert readback.verdict(ANSWERS) is None
    assert readback.verdict("pose: refused (malformed)\n") is None
    assert readback.verdict("pose 12 34*41\n") is None


def test_the_frame_acceptance_is_the_boards_own_line():
    """✅ **枠を受け取ったかは、基板が印字する。** ⛔ ホストの `sent` とは別の問いである。

    ⚠️ **綴りの正本も `main.cpp` に在る**（`HandleFrame`）。ここは写しである。
    """
    source = MAIN_CPP.read_text(encoding="utf-8")
    assert 'frame: light=%s face=%s gesture=%s sound=%s' in source
    assert 'frame: refused (%s)' in source

    accepted = ("frame: light=warm face=greeting gesture=none sound=hello\r\n")
    assert readback.frame_accepted(accepted) is True
    assert readback.frame_accepted("frame: refused (unknown value)\r\n") is False


def test_a_gesture_line_is_not_the_frame_being_accepted():
    """⛔ **身振りの印字は、枠の受理ではない。** 混ぜると、断られた枠が通ったことになる。

    ⚠️ 基板は `frame: gesture %s -> raw yaw=%d pitch=%d` も印字する——
    **同じ接頭辞で始まるが、別の問いへの答えである。**
    """
    gesture = "frame: gesture look_up -> raw yaw=1 pitch=2 (measured posture)\n"
    assert readback.frame_accepted(gesture) is None


def test_nothing_printed_is_not_a_refusal():
    """⛔ **「何も言わなかった」と「名指しで断った」は別である。** `None` と `False`。"""
    assert readback.frame_accepted("") is None
    assert readback.frame_accepted(ANSWERS) is None


def test_a_window_with_two_frames_keeps_the_last():
    """⚠️ **新しい方が効いている。** 前の枠の受理を、今の枠の答えとして読まない。"""
    ok = "frame: light=warm face=greeting gesture=none sound=hello\n"
    refused = "frame: refused (malformed)\n"
    assert readback.frame_accepted(ok + refused) is False
    assert readback.frame_accepted(refused + ok) is True


# ---------------------------------------------------------------------------
# 縁。⚠️ 端末の代わりに、ただのファイルを開く。
# ---------------------------------------------------------------------------


def test_the_servo_count_is_the_boards_own_two_numbers():
    """✅ **0.19.62 から、監視犬の2つの数が問いの答えに載る。**

    ⛔ **この行が無ければ、ホストはバスが黙ったことを知れない**——監視犬の印字は
    `printf` であり、**0.19.61 にリンクが唯一の道になってから、ここへ届かない。**
    """
    text = "bench: servo strikes=1 rail=2\n" + ANSWERS
    assert readback.servo(text) == {"strikes": 1, "rail": 2}


def test_a_board_that_says_nothing_about_the_servos_is_not_a_zero():
    """⛔ **印字が無いことは、`strikes 0 rail 0` ではない。**

    ⚠️ **`None` は「基板がその行を言わなかった」**であり、
    **「黙っていない」でも「レールを一度も落としていない」でもない**——
    `verdict: None` と `0 refused` を混ぜないのと同じ区別である。
    """
    assert readback.servo(ANSWERS) is None
    assert readback.servo("") is None


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
    # ⚠️ **1つの問いに、1つの形である。** 成功も失敗も `heard` と `read` を持つ——
    #    2つの形があったために、読む側は成功した読み戻しを数えられなかった。
    assert rows[0]["position"] == [25, 25]
    assert rows[0]["heard"] is True
    assert rows[0]["at"] == 1.0
    assert rows[1]["neck"] == "look_up"
    assert rows[1]["from"] == [25, 25]
    assert rows[1]["to"] == [80, 500]


def test_the_row_carries_the_watchdogs_count(tmp_path, capsys):
    """✅ **0.19.62 から、探針の行が監視犬の2つの数を運ぶ。**

    ⚠️ **基板は、姿勢より先にそれを書く**（`BenchPos`）——ホストは姿勢を読んだ時点で
    窓を閉じるからである。⛔ **ここで順序を入れ替えれば、この欄は `None` になる**:
    その日、**バスが黙ったことは、また見えなくなる。**
    """
    path = _console(tmp_path, "bench: servo strikes=2 rail=1\n" + ANSWERS)
    neck = edge.Neck(str(path))

    assert neck.take(_first(neck), 1.0) is True
    neck._close()

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert rows[0]["servo"] == {"strikes": 2, "rail": 1}
    assert rows[0]["position"] == [25, 25]


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
    # ⚠️ **先頭の空行は 0.19.44 からである**——開いた直後の1バイト（切れ端を落とす）。
    # ⚠️ **0.19.62 から `servo` の欄がある。** ⛔ **`None` は「黙っていない」ではなく、
    #    「基板がその行を印字しなかった」である**——この試験台の答えは、印字しない板である。
    assert rows == [
        {"position": None, "heard": False, "servo": None,
         "read": "\nbench pos\n", "at": 0.0}
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
            "servo": None,
            "read": "bench: yaw=no answer pitch=no answer\n\nbench pos\n",
            "at": 0.0,
        }
    ]


def _run(neck: "edge.Neck", at: float) -> float:
    """**縁の輪と同じように、期限ごとに起こす。** ⚠️ 流しが終わっても、判定が残っている。"""
    t = at
    while neck.deadline is not None or neck._fd is not None:
        neck.pump(t)
        t += edge.gestures.DEFAULT_PERIOD
        assert t < at + 30.0, "流れが終わらない"
    return t


def test_the_stream_hears_the_boards_own_verdict(tmp_path, capsys):
    """✅ **0.19.38 から、流しの終わりに基板自身の数が1行になる。**

    ⛔ **それまでは、閉じた後の行を誰も読まなかった。** 2026-10-19、デーモンは
    `{"neck": "recoil", "applied": 18, ...}` と書いた——**送った数である**——
    そして頭は1カウントも動かなかった。**基板が断ったのか丸めたのかは、
    そのとき誰にも分からなかった。** ⇒ **この行が、それを分ける。**

    ⚠️ **試験台は普通のファイルである**: 判定は先に置かれ、縁がそれを読む。
    本物の tty では、基板が 0.5〜0.8 秒後に印字する（`VERDICT_WAIT` の上限）。
    """
    path = _console(
        tmp_path,
        ANSWERS + "pose: 41 applied, 1 refused, 0 clamped\n",
    )
    neck = edge.Neck(str(path))
    at = 1.0
    assert neck.take(_first(neck), at) is True
    _run(neck, at)

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    verdicts = [row for row in rows if "verdict" in row]
    assert len(verdicts) == 1, rows
    assert verdicts[0]["neck"] == "look_up"
    assert verdicts[0]["verdict"] == {"applied": 41, "refused": 1, "clamped": 0}


def test_a_silent_board_leaves_a_verdict_of_none(tmp_path, capsys):
    """⛔ **基板が何も言わなかったことを、`0 refused` と書かない。**

    ⚠️ **2つは別の失敗である**: 断らなかったのか、判定が届かなかったのか。
    ⇒ **`verdict: None` と、届いた文字（`read`）を残す。**
    """
    path = _console(tmp_path, ANSWERS)
    neck = edge.Neck(str(path))
    at = 1.0
    assert neck.take(_first(neck), at) is True
    _run(neck, at)

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    verdicts = [row for row in rows if "verdict" in row]
    assert len(verdicts) == 1, rows
    assert verdicts[0]["verdict"] is None
    assert "read" in verdicts[0]


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
