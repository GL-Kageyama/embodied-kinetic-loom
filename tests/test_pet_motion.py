# -*- coding: utf-8 -*-
"""**顔と身体が、1つの時計から出ること。**

⛔ **このファイルが主張するのは、それである。**
**「生きている感じ」でも、「安全」でもない**——[07] の逐語どおり、
**検証できるのは機構だけであり、目標は検証できない。**

⚠️ **そして、このファイルが最初に押さえるのは、顔の側の実測である。**
**5つの顔のうち2つ（`happy` と `greeting`）は、同じ絵である。**
⇒ **その2つを見分けているものが運動であるなら、
「運動が意味を運ぶ」ことは、この機体の上で初めて実演されたことになる。**

⛔ **足りないものが1つある。** **シリアル層である**——
**ゆえに、ここで動いているものは、1バイトも機体へ行っていない。**
"""
from __future__ import annotations

import io
import json

import pytest

from conftest import FakeClock
from engine.backend.axis_map import AxisMap, ChannelCalibration
from engine.backend.mock import MockBox
from engine.trajectory import ChannelLimits, Envelope, Rejection
from engine.intent import IntentError, Move
from projects.pet.expressions import FACES, State
from projects.pet.motion import (
    MOTIONS, Expression, MakeError, Rig, demo_rig, load_expression, perform,
)
from projects.pet.screen import HOME, Screen

PERIOD = 0.02  # ⚠️ **この数は既定値ではない。** `demo_rig()` が選んだ数である


def _rig(start: float = 512.0, limits: ChannelLimits | None = None) -> Rig:
    return Rig(
        axis_map=AxisMap(channels={
            "pitch": ChannelCalibration(motor=0, sign=1, offset=0.0, scale=1.0),
        }),
        starts_by_dof={"pitch": start},
        limits_by_dof={"pitch": limits if limits is not None else ChannelLimits()},
        limits_by_motor=(limits if limits is not None else ChannelLimits(),),
        period=PERIOD,
    )


def _clock() -> FakeClock:
    return FakeClock(overshoot=0.0005)  # ⚠️ **実機では、余計に眠るのが普通である**


def _run(start: float = 512.0, limits: ChannelLimits | None = None):
    out = io.StringIO()
    box = MockBox(motors=1)
    take = perform(load_expression("greeting"), _rig(start=start, limits=limits),
                   clock=_clock(), screen=Screen(out), box=box)
    return take, out, box


# ───────────────────────── 語 → 型 ─────────────────────────


def test_greeting_is_the_intent_written_in_the_file():
    """⛔ **型が読むのは `motions/greeting.json` である。****手で組んだ意図ではない。**"""
    raw = json.loads((MOTIONS / "greeting.json").read_text(encoding="utf-8"))
    assert [m["dof"] for m in raw["moves"]] == ["pitch", "pitch"]
    assert [m["target"] for m in raw["moves"]] == [552, 512]
    assert [m["group"] for m in raw["moves"]] == [0, 1]

    expression = load_expression("greeting")
    assert [m.dof for m in expression.intent.moves] == ["pitch", "pitch"]
    assert len(expression.intent.groups()) == 2, "⛔ **前傾と、戻りである**"


def test_the_words_are_outside_the_type_on_purpose():
    """⛔ **語は `Motion Intent` の中に無い。** `additionalProperties: false` だからである。

    ⚠️ **これは不便の記録ではない。** **`Intent` は既にカウントであり、
    「なぜ +40 なのか」を自分では言えない**——**ゆえに来歴は型の外に要る。**
    """
    expression = load_expression("greeting")
    assert expression.words == ("small forward tilt", "return")
    dump = json.dumps(json.loads((MOTIONS / "greeting.json").read_text("utf-8")))
    for word in expression.words:
        assert word not in dump, "⛔ **語が型の中に入っている**"


def test_an_expression_that_has_no_words_is_refused():
    with pytest.raises(MakeError):
        load_expression("nonesuch")


def test_a_move_the_type_would_refuse_never_reaches_the_rig():
    """⚠️ **型の検証は `engine/intent.py` が持つ。****ここは、それが効いていることだけを見る。**"""
    with pytest.raises(IntentError):
        from engine.intent import load as load_intent

        load_intent({"moves": [
            {"dof": "pitch", "target": 512, "duration_ms": 600, "group": 0},
            {"dof": "pitch", "target": 552, "duration_ms": 500, "group": 0},
        ]})


# ───────────────────── 運動が意味を運ぶ ─────────────────────


def test_happy_and_greeting_are_the_same_face_so_the_motion_is_the_difference():
    """⛔ **これが、この演技を最初に選んだ理由である。**

    `happy` と `greeting` の顔は1バイトも違わない（実測）。**⇒ 見分けているのは運動だけである。**
    ⚠️ **そして下の後半が、その運動が「何もしない」でないことを押さえる**——
    **顔が同じで運動も同じなら、それは1つの状態である。**
    """
    assert FACES[State.HAPPY] == FACES[State.GREETING]

    expression = load_expression("greeting")
    targets = {m.target for m in expression.intent.moves}
    assert targets == {512, 552}, "⛔ **動かなければ、2つは分かれない**"


def test_the_face_and_the_body_come_from_the_same_tick():
    """⛔ **[06] §11-8 の逐語——「顔と身体は必ず同時に一つの時計から出す」。**

    ⚠️ **`drawn_at` がその主張の形である。** **顔を描いた時刻が、運動を送った
    最初の刻みの時刻と一致する**——ゆえに**2つの時計ではない。**
    ⛔ **ループの外で描いていたら、この検査は書けなかった。**
    """
    take, out, box = _run()

    assert take.ran
    assert take.drawn_at is not None and take.ticks
    assert take.drawn_at == take.ticks[0].started, (
        "⛔ **顔が、運動を送った刻みの外で描かれている**"
    )
    assert out.getvalue().count(HOME) == 1, "⚠️ **この版の演技は、途中で表情を変えない**"
    assert FACES[State.GREETING][1] in out.getvalue()
    assert box.received, "⛔ **身体が出ていない**"


def test_the_pet_arrives_back_where_it_started():
    """⚠️ **「戻り」は、往復の後半である。** **着かなければ、それは前傾ではない。**"""
    take, _, box = _run()
    assert take.arrived == (512.0,)
    assert take.sent[-1].value == 512


def test_the_pet_reaches_the_written_target():
    """⛔ **意図に書かれた数が、実際に送られている。**"""
    take, _, _ = _run()
    assert max(f.value for f in take.sent) == 552
    assert min(f.value for f in take.sent) == 512


def test_nothing_jumps_at_the_boundary_between_the_two_groups():
    """⛔ **2組の境目で、送る値が飛ばない。** 前傾して、戻る——それがこの演技である。

    ⚠️ **この検査が書かれた理由**（実測 2026-09-28）。**演技が終わった後の刻みで、
    最後の組の*最初の*標本が送られていた**——**最後の目標（512）ではなく、552 である。**
    ⇒ **機体は、512 へ向かって走っている途中で、いきなり 552 を commanded される。**

    ⛔ **そして、この誤りは `admit` の欠陥に隠れていた。** 当時は2組目が
    「512 からの平らな線」だったので、**その最初の標本も 512 だった**——
    **⇒ 到着の検査は、2つの誤りが打ち消し合って緑だった。**
    """
    take, _, _ = _run()
    values = [f.value for f in take.sent]
    # ⚠️ **最後の 552 である。** `index` は最初のものを返す——
    # **山の頂上は何刻みか続くので、最初から見ると頂上の中腹に立つことになる。**
    peak = len(values) - 1 - values[::-1].index(max(values))

    assert max(values) == 552 and values[-1] == 512
    assert 552 not in values[peak + 1:], (
        "⛔ **山を越えた後、もう一度 552 が来ている**——"
        "**終わった組が、その最初の標本へ戻されている**"
    )
    # ⛔ **そして、送った値は降りきっている。** **「戻り」は、往復の後半である。**
    assert values[-1] == take.arrived[0] == 512.0


def test_the_whole_performance_runs_without_a_refusal():
    """⚠️ **この演技は、門に1度も止められない。** **止められるなら、意図のほうが悪い。**

    ⛔ **但しこれは「安全」ではない。** **上限を渡していないので、段差の検査は鳴っていない**——
    下の `test_the_demo_rig_supplies_no_limits` を見よ。
    """
    take, _, _ = _run()
    assert take.refusals == 0
    assert take.skipped == 0


def test_nothing_opens_a_port():
    """⛔ **送り先は Mock である。** **箱のふりをした Python である。**

    ⚠️ **この検査が言えるのは「ここからシリアルへ行く道が無い」ことだけである**——
    **`engine/backend/` は1行もポートを開かない**（`CLAUDE.md` の安全の節）。
    """
    take, _, box = _run()
    assert box.received and all(len(f.raw) == 5 for f in take.sent)


# ───────────────── 型が表現できない前提 ─────────────────


def test_a_start_position_the_intent_was_not_written_for_moves_the_pet_away():
    """⛔ **この検査は、欠陥ではなく、型の限界を記録する。**

    `Motion Intent` の `target` は**絶対カウント**である（型の定義）。
    ⇒ **意図は「どこから」を知らない。** ゆえに、**512 から始まる前提で書かれた意図を
    400 から走らせると、機体は 512 へ行って終わる**——**自分のいた場所へは戻らない。**

    ⛔ **そして門は、これを1つも止めない。** **1フレーム1フレームは、どれも合法である**
    ——**軌道は「400 から 552 へ」を正しく組む。** **間違っているのは意味のほうである。**
    ⚠️ **決定論的な核心は、意図の数が意味を持つかを知らない。**
    """
    take, _, _ = _run(start=400.0)

    assert take.ran, "⚠️ **計画時には通ってしまう**"
    assert take.refusals == 0, "⛔ **門にも、止める理由が無い**"
    assert take.arrived == (512.0,), (
        "⛔ **機体は、いた場所（400）ではなく、意図が書いた場所（512）へ行く**"
    )


def test_a_target_outside_the_envelope_sends_nothing_at_all():
    """⛔ **枠の外は、着く先ではない。****そして枠は、この演技で唯一の実測である。**"""
    intent = load_expression("greeting").intent
    far = Expression(state=State.GREETING, words=intent and ("far",),
                     intent=type(intent)(moves=(
                         Move(dof="pitch", target=900, duration_ms=600, group=0),
                     )))

    box = MockBox(motors=1)
    take = perform(far, _rig(), clock=_clock(), screen=Screen(io.StringIO()), box=box)

    assert isinstance(take.refusal, Rejection)
    assert take.sets == (), "⛔ **1フレームも組まない**"
    assert box.received == [] and box.commands == []
    assert "枠" in take.refusal.reason


def test_a_motor_with_no_known_position_is_not_filled_in_with_zero():
    """⛔ **知らない開始位置を 0.0 で埋めない。**

    **門は、その数を使って最初の1フレームの段差を測る**——
    **0 と書けば、門は「0 に居る」と信じる。**
    """
    rig = Rig(
        axis_map=AxisMap(channels={
            "pitch": ChannelCalibration(motor=0, sign=1, offset=0.0, scale=1.0),
            "roll": ChannelCalibration(motor=2, sign=1, offset=0.0, scale=1.0),
        }),
        starts_by_dof={"pitch": 512.0, "roll": 512.0},
        limits_by_dof={},
        limits_by_motor=(ChannelLimits(), ChannelLimits(), ChannelLimits()),
        period=PERIOD,
    )
    assert rig.motors() == 3

    with pytest.raises(MakeError):
        rig.starts_by_motor()  # ⚠️ モーター1 の位置が、どこにも無い


# ────────────────────── デモの数の記録 ──────────────────────


def test_the_demo_rig_supplies_no_limits():
    """⛔ **デモは上限を1つも渡していない。****ゆえに段差の検査は鳴っていない。**

    ⚠️ **この検査が在る理由**: **`demo_rig()` の docstring が「鳴っていない」と書いている。**
    **数を後から埋めたら、この検査が落ちる**——**説明と実装が食い違わないためである。**
    """
    rig = demo_rig()
    assert rig.limits_by_dof["pitch"] == ChannelLimits()
    assert rig.limits_by_motor == (ChannelLimits(),)
    assert rig.limits_by_dof["pitch"].velocity is None


def test_the_demo_rig_is_the_only_place_those_numbers_live():
    """⚠️ **`demo_rig()` の数は、1つも測っていない。****そして、それは docstring に書いてある。**"""
    rig = demo_rig()
    assert rig.starts_by_dof == {"pitch": 512.0}
    assert rig.period == PERIOD
    assert rig.envelope == Envelope(), "⚠️ **枠だけは既定＝実測である**"
