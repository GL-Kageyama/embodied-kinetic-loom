# -*- coding: utf-8 -*-
"""**ログの1日を数える計器。**

⚠️ **測るのは数え方だけである。** 中核は行を受け取り、数えて返す——
**ファイルも時計も読まない**（`day/summary.py`）。⇒ **1行も書かなくても試験できる。**

⛔ **このファイルはログの意味を測らない。** 「暮らせたか」は著者の観察であり、
ここで数えているのは**本文が何をしたか**だけである——**数は証拠であり、観察ではない。**
"""
from __future__ import annotations

import json

import pytest

from projects.stackchan.day.summary import render, summarize


def line(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def frame(sent: bool = True, **words: object) -> str:
    body = {"face": None, "light": "dim", "gesture": None, "sound": None}
    body.update(words)
    return line({"frame": json.dumps(body), "sent": sent, "at": 1.0, "session": "s"})


# ---------------------------------------------------------------------------
# 空と、壊れた行。
# ---------------------------------------------------------------------------


def test_nothing_is_nothing():
    """⚠️ **空のログは、全部が0である。** 例外ではない。"""
    s = summarize([])
    assert s.lines == 0 and s.decisions == 0 and s.frames == 0 and s.readbacks == 0


def test_blank_lines_are_not_lines():
    """⛔ **空行を数えない。** 数えるのは、書かれた行だけである。"""
    assert summarize(["", "   ", "\t"]).lines == 0


def test_a_line_that_is_not_json_is_counted_not_dropped():
    """⚠️ **壊れた行は、捨てずに数える。** ログ自身が壊れていることも測定である。"""
    s = summarize(["not json at all", "{broken", "[1, 2]"])
    assert s.lines == 3
    assert s.unreadable == 3


def test_a_json_line_of_an_unknown_shape_is_counted():
    """⛔ **知らない形の JSON も、数えずに黙って捨てない。**"""
    s = summarize([line({"something": "new"})])
    assert s.lines == 1 and s.unreadable == 1


# ---------------------------------------------------------------------------
# 数えるもの。
# ---------------------------------------------------------------------------


def test_a_decision_is_counted_with_its_phase():
    s = summarize([line({"ok": True, "phase": "working", "event": "PreToolUse"})])
    assert s.decisions == 1
    assert s.phases == {"working": 1}


def test_a_frame_is_counted_and_its_words_too():
    s = summarize([frame(face="happy", light="warm", gesture="nod", sound="chime")])
    assert s.frames == 1 and s.frames_sent == 1
    assert s.faces == {"happy": 1}
    assert s.lights == {"warm": 1}
    assert s.gestures == {"nod": 1}
    assert s.sounds == {"chime": 1}


def test_an_unsent_frame_is_counted_but_its_words_are_not():
    """⛔ **送られなかった枠の語は、基板に届いていない。** 数えない。"""
    s = summarize([frame(sent=False, sound="hello", face="greeting")])
    assert s.frames == 1 and s.frames_sent == 0
    assert s.sounds == {} and s.faces == {}


def test_a_frame_whose_body_is_not_json_is_counted_apart():
    """⚠️ **枠の中身が読めないことは、別の欄である。**"""
    s = summarize([line({"frame": "{oops", "sent": True})])
    assert s.frames == 1 and s.bad_frames == 1 and s.sounds == {}


def test_null_fields_are_not_words():
    """⚠️ **`null` は語ではない。** 空の欄を数えると、鳴らなかった枠が鳴ったことになる。"""
    s = summarize([frame(sound=None, gesture=None, face=None)])
    assert s.sounds == {} and s.gestures == {} and s.faces == {}


def test_a_daemon_start_is_counted():
    s = summarize([line({"daemon": "listening", "socket": "/tmp/x.sock", "port": None})])
    assert s.starts == 1 and s.decisions == 0 and s.unreadable == 0


def test_the_plan_and_the_result_are_counted_together():
    """⚠️ **予定と結果は2行である。** 片方だけ数えると、流した量と届いた量が混ざる。"""
    s = summarize([
        line({"neck": "look_up", "from": [80, 500], "to": [80, 500], "poses": 11,
              "seconds": 0.2, "at": 1.0}),
        line({"neck": "look_up", "applied": 11, "late": 10, "held": 27, "at": 2.0}),
    ])
    assert (s.streamed, s.poses) == (1, 11)
    assert (s.applied, s.late, s.held) == (11, 10, 27)


def test_heard_and_position_are_two_different_counts():
    """⛔ **コンソールが答えたことと、サーボが位置を返したことは別である。**

    `docs/stackchan-daemon.md` の2つの失敗は、2つの欄でなければ区別できない。
    """
    s = summarize([
        line({"position": None, "heard": False}),   # コンソールが沈黙した
        line({"position": None, "heard": True}),    # 答えたが、位置は無い
        line({"position": 504, "heard": True}),     # 答えて、位置もある
    ])
    assert s.readbacks == 3
    assert s.heard == 2
    assert s.positions == 1


def test_the_boards_own_verdict_is_counted_and_kept_apart_from_the_hosts():
    """⛔ **「送った数」と「基板が適用した数」は、別の欄である。**

    ⚠️ **2026-10-19 の `recoil`**: デーモンは `applied: 18` と書き、頭は1カウントも
    動かなかった。**2つの数が同じ欄にあれば、その食い違いはログから読めない。**
    ⇒ **判定の行は、`verdict` の欄で数える。**
    """
    s = summarize([
        line({"neck": "recoil", "applied": 18, "late": 16, "held": 27, "at": 2.0}),
        line({"neck": "recoil", "verdict": {"applied": 45, "refused": 2, "clamped": 1},
              "read": "pose: 45 applied, 2 refused, 1 clamped\n", "at": 3.0}),
        line({"neck": "look_up", "verdict": None, "read": "", "at": 4.0}),
    ])
    assert (s.applied, s.late, s.held) == (18, 16, 27)
    assert (s.verdicts, s.verdict_silent) == (1, 1)
    assert (s.board_applied, s.board_refused, s.board_clamped) == (45, 2, 1)


def test_a_probe_that_carried_a_position_is_not_unreadable():
    """⛔ **成功した読み戻しが、読めない行として数えられていた。**

    ⚠️ **2026-10-19 のログで測った**: デーモンは成功した探針を `heard` の無い形
    （`{"position": [...], "at": …}`）で書いていたので、この計器は
    **58行を `unreadable` に入れ、`readbacks 46`・`positions 0` と言っていた**——
    **段7の計器そのものが、計器から見えていなかった。**
    ⇒ **古い形も、新しい形も、同じ1つの読み戻しである。**
    """
    old = line({"position": [100, 506], "at": 1.0})        # 2026-10-19 までの形
    new = line({"position": [328, 506], "heard": True, "read": "", "at": 2.0})
    s = summarize([old, new])
    assert s.unreadable == 0
    assert s.readbacks == 2
    assert s.positions == 2
    # ⚠️ **位置が読めたなら、コンソールは答えた。** 古い形は `heard` を持たない。
    assert s.heard == 2


def test_the_count_does_not_depend_on_the_order():
    """⚠️ **数え上げである。** 行の順序は数を変えない。"""
    lines = [
        frame(face="happy"),
        line({"ok": True, "phase": "present"}),
        line({"position": None, "heard": True}),
        line({"neck": "nod", "applied": 3, "late": 1, "held": 2}),
    ]
    a = summarize(lines)
    b = summarize(list(reversed(lines)))
    assert a == b


def test_rendering_names_every_count():
    """⚠️ **数えたものが、1つ残らず行になる。** 印字されない数は、読まれない数である。"""
    s = summarize([
        line({"daemon": "listening"}),
        line({"ok": True, "phase": "working"}),
        frame(sound="chime"),
        line({"neck": "nod", "applied": 3, "late": 1, "held": 2}),
        line({"position": None, "heard": True}),
    ])
    # ⚠️ **桁は問わない。** 問うのは、その名前と数が1行になって出ていることである。
    flat = " ".join(render(s).split())
    for needle in (
        "daemon starts 1", "decisions 1", "frames 1", "frames sent 1",
        "poses applied 3", "late 1", "held 2", "readbacks 1", "heard 1",
        "positions 0", "sounds chime 1", "phases working 1",
        "verdicts 0", "board refused 0",
    ):
        assert needle in flat


@pytest.mark.parametrize("empty", [None, "", 0])
def test_a_word_that_is_not_a_string_is_not_counted(empty: object):
    """⚠️ **語の欄に語でないものが来ても、数えない。** 壊れた枠は壊れた枠である。"""
    s = summarize([frame(sound=empty)])
    assert s.frames == 1 and s.sounds == {}
