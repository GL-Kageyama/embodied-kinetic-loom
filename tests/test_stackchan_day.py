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


def frame(sent: bool = True, accepted: object = None, **words: object) -> str:
    body = {"face": None, "light": "dim", "gesture": None, "sound": None}
    body.update(words)
    return line({"frame": json.dumps(body), "sent": sent, "accepted": accepted,
                 "at": 1.0, "session": "s"})


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


def test_the_boards_word_on_a_frame_is_counted_three_ways():
    """⛔ **受理・拒否・聞こえなかった、は3つの数である。**

    ⚠️ **`None` は「断られた」ではない**——基板が何も言わなかったことである。
    0.19.41 より前の行は `accepted` を持たないので、**同じ `unheard` に数える**。
    """
    old = line({"frame": json.dumps({"light": "warm"}), "sent": True, "at": 1.0})
    s = summarize([frame(accepted=True), frame(accepted=False), frame(accepted=None), old])
    assert s.frames == 4
    assert s.frames_accepted == 1
    assert s.frames_refused == 1
    assert s.frames_unheard == 2


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


def test_the_watchdogs_count_is_counted_and_a_row_without_it_is_not_a_zero():
    """✅ **0.19.62 から、基板の監視犬の2つの数を数える。**

    ⛔ **欄の無い行を 0 と数えない**——それは *知らされていない* ことであり、
    **「黙っていない」でも「レールを落としていない」でもない**
    （`verdict: None` と `0 refused` の区別と同じである）。

    ⚠️ **`servo_silent` は予告の欄である。** `strikes` が 1 か 2 なら、バスは
    **黙りかけている**——3 でレールが落ちるので、**`rail` より早く届く。**
    """
    s = summarize([
        line({"position": [328, 506], "heard": True,
              "servo": {"strikes": 0, "rail": 0}}),
        line({"position": [328, 506], "heard": True,
              "servo": {"strikes": 2, "rail": 0}}),
        line({"position": None, "heard": True}),   # 欄が無い——知らされていない
    ])
    assert s.readbacks == 3
    assert s.servo_reports == 2       # ⛔ 3 ではない
    assert s.servo_silent == 1        # `strikes` > 0 の行だけ
    assert s.rail_cycles == 0         # 増えていない


def test_a_rail_count_that_goes_backwards_is_a_reboot():
    """⚠️ **`rail` は、基板の起動からの回数である。** ⇒ **増えた分が、起きた回数である。**

    ⛔ **戻るのは、基板が再起動したときだけである**——そのとき**その前の回数は
    観測できない**。数えず、基準を引き直す。
    ⇒ **`rail_cycles` が小さいことは、黙りが少なかったことではない。**
    """
    s = summarize([
        line({"position": None, "heard": True, "servo": {"strikes": 0, "rail": 1}}),
        line({"position": None, "heard": True, "servo": {"strikes": 0, "rail": 3}}),
        line({"position": None, "heard": True, "servo": {"strikes": 0, "rail": 1}}),
        line({"position": None, "heard": True, "servo": {"strikes": 0, "rail": 2}}),
    ])
    assert s.rail_cycles == 2 + 1     # 1→3 と、再起動後の 1→2
    assert s.rail_resets == 1


def test_one_count_depends_on_the_order_and_it_is_named():
    """⛔ **数え上げではない欄が、1つだけある。** 隠さずに、ここに書く。

    ⚠️ **逆向きに渡せば `rail_cycles` は別の数になる**——それ以外の欄は変わらない。
    ⇒ **`summarize` は行を順に渡されることを前提にする**（この欄のために）。
    """
    lines = [
        line({"position": None, "heard": True, "servo": {"strikes": 0, "rail": 1}}),
        line({"position": None, "heard": True, "servo": {"strikes": 0, "rail": 4}}),
    ]
    forward = summarize(lines)
    backward = summarize(list(reversed(lines)))
    assert forward.rail_cycles == 3
    assert backward.rail_cycles == 0 and backward.rail_resets == 1
    # ⚠️ **ほかの欄は、順序を問わない。**
    assert (forward.readbacks, forward.heard, forward.positions) == (
        backward.readbacks, backward.heard, backward.positions)


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


def test_a_decision_carries_its_work_word():
    """✅ **2026-10-20（0.19.52）。** 第2層は `work` を判定の行に載せる。

    ⚠️ **載せた理由は、一日の内訳を数えるためである**（`daemon/__main__.py` の
    `handle`）。⇒ **計器がそれを数えなければ、載せた理由がまだ無い。**
    """
    s = summarize([
        line({"ok": True, "phase": "working", "work": "write"}),
        line({"ok": True, "phase": "working", "work": "write"}),
        line({"ok": True, "phase": "working", "work": "run"}),
    ])
    assert s.works == {"write": 2, "run": 1}
    assert s.decisions == 3


def test_a_decision_without_a_word_is_not_other():
    """⛔ **「知らされていない」を `other` に数えない。** 31の事象は語を運ばない。"""
    s = summarize([
        line({"ok": True, "phase": "working"}),                 # 語を運ばない事象
        line({"ok": True, "phase": "working", "work": "other"}), # 表に無い道具
    ])
    assert s.works == {"other": 1}, "運ばなかった行が other として数えられた"
    assert s.decisions == 2


def test_an_empty_work_field_is_not_a_word():
    """⚠️ **`null` と空文字は語ではない。** 数えれば、不在が語になる。"""
    s = summarize([
        line({"ok": True, "phase": "working", "work": None}),
        line({"ok": True, "phase": "working", "work": ""}),
        line({"ok": True, "phase": "working", "work": 7}),
    ])
    assert s.works == {}
    assert s.decisions == 3


def test_rendering_names_the_work_words():
    """⚠️ **印字されない数は、読まれない数である。**"""
    s = summarize([line({"ok": True, "phase": "working", "work": "search"})])
    assert "works search 1" in " ".join(render(s).split())


def test_rendering_marks_an_absent_work_column():
    """⚠️ **1語も無ければ `-` である。** 空欄は、0と見分けられない。"""
    flat = " ".join(render(summarize([line({"ok": True, "phase": "working"})])).split())
    assert "works -" in flat


def test_the_count_does_not_depend_on_the_order():
    """⚠️ **数え上げである。** 行の順序は数を変えない。

    ⛔ **例外は1つである**: `rail_cycles` は「基板の起動からの回数」の**増えた分**なので、
    順序を持たない——**それは `test_one_count_depends_on_the_order_and_it_is_named` が
    名指しで持っている。** この試験には監視犬の行が1つも無い。
    """
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
        "servo reports 0", "seen silent 0", "rail cycles 0", "rail resets 0",
    ):
        assert needle in flat


@pytest.mark.parametrize("empty", [None, "", 0])
def test_a_word_that_is_not_a_string_is_not_counted(empty: object):
    """⚠️ **語の欄に語でないものが来ても、数えない。** 壊れた枠は壊れた枠である。"""
    s = summarize([frame(sound=empty)])
    assert s.frames == 1 and s.sounds == {}


# ---------------------------------------------------------------------------
# 監修の5つの欄（0.19.64、設計 §10.6）——⛔ 知らない計器は正しい行を「壊れた行」にする。
# ---------------------------------------------------------------------------


def test_the_meta_rows_are_counted_and_not_called_unreadable():
    """⛔ **正しい行が `unreadable` に入れば、計器は「ログが壊れている」と言い始める。**

    2026-10-21 に実測した: メタの5行を食わせると `unreadable` が5になり、
    5つの欄を足すと0に戻った（設計 §19.10）。
    """
    lines = [
        line({"meta": "candidate", "kind": "turn-review", "session": "s", "at": 1.0}),
        line({"meta": "candidate", "kind": "failure-loop", "session": "s", "at": 2.0}),
        line({"meta": "delivered", "kind": "turn-review", "session": "s", "at": 3.0}),
        line({"meta": "dropped", "kind": "failure-loop", "why": "budget", "at": 4.0}),
        line({"meta": "error", "error": "ValueError"}),
    ]
    s = summarize(lines)

    assert s.unreadable == 0, "正しい行が壊れた行に数えられている"
    assert s.meta_candidates == 2
    assert s.meta_delivered == 1
    assert s.meta_dropped == 1
    # ⛔ **残した行が数えられないなら、残した意味が無い**（§10.6）。
    assert s.meta_errors == 1


@pytest.mark.parametrize("why", ["budget", "cooldown", "expired", "superseded"])
def test_a_dropped_row_is_one_count_whatever_the_reason(why):
    """⚠️ **`why` の4つを、4つの数にしない。** 名前の欄は16文字である。

    内訳は `jq` で数える——**計器は毎日読むもの、内訳は調べるときに読むもの**（§10.6）。
    """
    s = summarize([line({"meta": "dropped", "kind": "turn-review",
                         "why": why, "at": 1.0})])
    assert s.meta_dropped == 1
    assert s.unreadable == 0


def test_a_silenced_day_is_not_a_silent_day():
    """⛔ **候補0は2つの意味を持つ。** 分けるのは起動行の `meta` だけである。

    黙った日（`quiet`）と、黙らされた日（`off`）は、**候補の数では同じ0**である。
    """
    silent = summarize([line({"daemon": "listening", "socket": "s", "meta": "quiet"})])
    silenced = summarize([line({"daemon": "listening", "socket": "s", "meta": "off"})])

    assert silent.meta_off_starts == 0
    assert silenced.meta_off_starts == 1
    assert silent.starts == silenced.starts == 1
    assert silent.meta_candidates == silenced.meta_candidates == 0


def test_a_startup_row_without_the_dial_is_not_silenced():
    """⚠️ **この欄より前の起動行には `meta` が無い。** それを `off` と読まない。"""
    s = summarize([line({"daemon": "listening", "socket": "s"})])
    assert s.starts == 1 and s.meta_off_starts == 0 and s.unreadable == 0


def test_an_unknown_meta_value_is_still_unreadable():
    """⚠️ **知らない形は、数えずに捨てない。** 捨てたことを言うために数える。"""
    s = summarize([line({"meta": "whisper", "at": 1.0})])
    assert s.unreadable == 1
    assert s.meta_candidates == 0


def test_the_five_names_fit_the_sixteen_character_column():
    """⚠️ **名前の欄は16文字である。** 数えるものが増えても、桁は動かない。"""
    s = summarize([])
    rows = [row for row in render(s).splitlines() if row.startswith("meta ")]
    assert len(rows) == 5, rows
    for row in rows:
        assert len(row[:row.index(str(0))].rstrip()) <= 16, row
    assert [row[:16].rstrip() for row in rows] == [
        "meta candidates", "meta delivered", "meta dropped", "meta errors",
        "meta off starts"]


# ---------------------------------------------------------------------------
# 口の6つの欄（0.19.70、設計 §22.10）——⛔ 同じ理由で、同じ日に足した。
# ---------------------------------------------------------------------------


def test_the_voice_rows_are_counted_and_not_called_unreadable():
    """⛔ **計数を足さずに新しい行を出せば、その日から全部が `unreadable` になる。**

    0.19.64 にメタの5行で踏んだのと同じ穴である（設計 §19.10）。⇒ **口の行にも、
    同じ日に6つの欄を置いた。**
    """
    lines = [
        line({"voice": "spoke", "blocks": 23, "bytes": 92882}),
        line({"voice": "cut", "blocks": 4, "bytes": 16000}),
        line({"voice": "cannot render", "error": "OSError"}),
        line({"voice": "busy"}),
        line({"voice": "refused", "error": "too-long"}),
        line({"voice": "no-board"}),
        line({"voice": "night"}),
        line({"voice": "error", "error": "ConnectionResetError"}),
    ]
    s = summarize(lines)

    assert s.unreadable == 0, "正しい行が壊れた行に数えられている"
    assert s.voice_spoke == 1
    # ⚠️ **`cut` と `cannot render` は1つの数である**——「言いかけて止まった」。
    assert s.voice_cut == 2
    # ⚠️ **`busy` と `refused` も1つである**——「断った」。
    assert s.voice_refused == 2
    assert s.voice_no_board == 1
    assert s.voice_night == 1
    assert s.voice_errors == 1


def test_an_unknown_voice_value_is_still_unreadable():
    """⚠️ **知らない形は、数えずに捨てない。** メタの枝と同じ切り方である。"""
    s = summarize([line({"voice": "whispered", "at": 1.0})])
    assert s.unreadable == 1
    assert s.voice_spoke == 0


def test_the_six_voice_names_fit_the_sixteen_character_column():
    """⚠️ **名前の欄は16文字である。** `voice no board` が最も長く、14文字である。"""
    s = summarize([])
    rows = [row for row in render(s).splitlines() if row.startswith("voice ")]
    assert [row[:16].rstrip() for row in rows] == [
        "voice spoke", "voice cut", "voice refused", "voice no board",
        "voice night", "voice errors"]
    for row in rows:
        assert len(row[:row.index(str(0))].rstrip()) <= 16, row
