# -*- coding: utf-8 -*-
"""門——**実際に出て行く1組を見る。**

⛔ **このファイルの中心は `test_a_refusal_still_sends_something` である。**

**「送らない」は「止まる」ではない。**
> **送信をやめると、15秒でトルクがおよそ 1/4 になる——そして、モーターは止まらない。**
> （`CLAUDE.md` の安全の節）

⇒ **ゆえに門は、弾いたときに空を返してはいけない。**
**最後に通した組を返し続ける。** **ここに書いておかないと、
「安全のために送信を止める」という、いちばん危ない実装が、自然に生える。**

⚠️ **このファイルの通貨は `(軸, 値)` である**（2026-10-15）。**`Frame` ではない**——
機体1では同じに見えるが、**1行に2軸を運ぶ機体では別物になる**（`wire.py` を見よ）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from engine.backend.gate import Gate
from engine.backend.protocol import DOF_REALITY_ENVELOPE, DofRealityWire
from engine.backend.wire import Command
from engine.trajectory.limits import ChannelLimits, Envelope

OPEN = ChannelLimits()  # ⚠️ 全部 None ＝ 制限しない
SLOW = ChannelLimits(velocity=100.0)  # 100 カウント/秒


def _gate(motors=1, limits=None, envelope=DOF_REALITY_ENVELOPE):
    """⚠️ **枠と電線は、ここで名指しで渡す。**

    ⛔ **既定で埋まっていた頃、この補助関数は「機体1の門」を作っていた**——
    **そして、どこにもそう書いていなかった**（2026-10-15）。
    """
    return Gate(
        starts_by_motor=tuple(500.0 for _ in range(motors)),
        limits_by_motor=tuple(limits or OPEN for _ in range(motors)),
        envelope=envelope,
        wire=DofRealityWire(),
    )


# --------------------------------------------------------------------------
# 通る
# --------------------------------------------------------------------------


def test_a_command_inside_the_envelope_passes():
    gate = _gate()
    v = gate.submit(1.0, (Command(0, 512.0),))
    assert v.allowed and not v.held and v.commands[0].value == 512


def test_none_in_the_envelope_means_do_not_limit():
    """⚠️ **`None` は「制限しない」である**（`limits.py` の規則）。"""
    gate = _gate(envelope=Envelope(target_min=None, target_max=None))
    assert gate.submit(1.0, (Command(0, 1024.0),)).allowed


# --------------------------------------------------------------------------
# 弾く——⛔ そして、それでも送る
# --------------------------------------------------------------------------


def test_outside_the_envelope_is_refused():
    gate = _gate()
    v = gate.submit(1.0, (Command(0, 900.0),))
    assert not v.allowed and v.held
    assert [x.kind for x in v.violations] == ["target"]
    assert v.violations[0].limit == 833.0


def test_a_refusal_still_sends_something():
    """⛔ **ここが要点である。** 弾くことは、黙ることを意味しない。"""
    gate = _gate()
    good = (Command(0, 512.0),)
    gate.submit(1.0, good)
    v = gate.submit(2.0, (Command(0, 900.0),))
    assert not v.allowed
    assert v.commands == good, "⛔ **弾いたときに空を返した。それは停止ではない**"


def test_the_first_refusal_does_not_go_silent():
    """⛔ **まだ1つも通していなくても、門は黙らない。**

    ⚠️ **この検査は、前は逆を主張していた**——「最初の拒否は空にしかなり得ない」と。
    ⛔ **それは限界だった。** **門は開始位置を知っている**（`starts_by_motor` は必須である）——
    **ゆえに「そこへ居ろ」を組める。** **空を返す理由が、1つも無い。**

    ⛔ **そして空を返せば、機体はその瞬間から誰も何も言わなくなる**——
    **15秒でトルクが 1/4 になり、モーターは止まらない**（`CLAUDE.md` の安全の節）。
    """
    gate = _gate()
    v = gate.submit(1.0, (Command(0, 900.0),))
    assert not v.allowed
    assert [c.value for c in v.commands] == [500], "⛔ **開始位置を保つべきである**"
    assert gate.hold() == v.commands


def test_a_refused_axis_creeps_toward_the_target_and_does_not_freeze():
    """⛔ **弾かれた軸は、凍るのでなく、届く速さで目標へ寄る。**

    ⚠️ **この検査は、前は逆を主張していた**——「軸が凍り、門は戻らない」と
    （`tests/test_backend.py` にあった）。**それは限界として著者へ返した**（`05 §2.2`）。

    **寄せる大きさは `limit × elapsed`**——**門がもともと通す大きさと同じである。**
    ⇒ **新しい仮定を1つも足していない。**
    """
    gate = _gate(limits=SLOW)  # 100 カウント/秒
    gate.submit(0.0, (Command(0, 500.0),))
    # ⚠️ 1秒あれば 100 カウント寄れる。600 はその外なので、まだ弾かれる。
    v = gate.submit(1.0, (Command(0, 700.0),))
    assert not v.allowed and v.held
    assert [c.value for c in v.commands] == [600], (
        "⛔ **寄せた値が機体へ行く**——`500 + 100 × 1.0` である"
    )
    # ⇒ **次は通る。** 溜まった時間を捨てないので、凍らない。
    v = gate.submit(2.0, (Command(0, 700.0),))
    assert v.allowed and v.commands[0].value == 700


def test_the_slewed_value_never_exceeds_what_the_gate_would_admit():
    """⛔ **寄せた値は、門が「段差だ」と言った大きさを超えない。**"""
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (Command(0, 500.0),))
    v = gate.submit(0.02, (Command(0, 900.0),))  # 枠の外——寄せない
    assert not v.allowed and v.commands[0].value == 500
    v = gate.submit(0.04, (Command(0, 700.0),))  # 段差——寄せる
    assert [c.value for c in v.commands] == [502], "100 カウント/秒 × 0.02 秒 = 2"


def test_an_out_of_envelope_target_is_not_slewed_toward():
    """⛔ **枠の外は、寄る先ではない。** **保つ。**

    ⚠️ **寄せれば、機体は枠へ向かって動き出す**——**門が止めようとしているのは、それである。**
    """
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (Command(0, 500.0),))
    v = gate.submit(5.0, (Command(0, 900.0),))  # 5秒ぶんの余裕があっても
    assert not v.allowed
    assert [c.value for c in v.commands] == [500], "⛔ **枠へ寄ってしまった**"



def test_a_refused_command_does_not_move_the_last_value():
    """⛔ **拒否された値が「前回値」になると、次の段差の基準が汚れる。**"""
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (Command(0, 500.0),))
    gate.submit(1.0, (Command(0, 900.0),))  # 弾かれる（枠の外）
    v = gate.submit(2.0, (Command(0, 520.0),))
    assert v.allowed, f"基準が汚れている: {v.violations}"


# --------------------------------------------------------------------------
# 段差——⛔ 門にしか見えない
# --------------------------------------------------------------------------


def test_a_step_is_refused_even_inside_the_envelope():
    """⛔ **枠の内側でも、届く速さを超えれば段差である。**
    上流ファームに補間が無いので、**段差は段差のまま入る**（§2.6）。"""
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (Command(0, 500.0),))
    v = gate.submit(0.001, (Command(0, 600.0),))  # 1 ms で 100 カウント
    assert not v.allowed
    assert [x.kind for x in v.violations] == ["step"]


def test_the_step_check_is_a_rate_not_a_magnitude():
    """⚠️ **同じ 100 カウントが、時間が在れば通る。** 大きさではなく速さの話である。"""
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (Command(0, 500.0),))
    assert gate.submit(2.0, (Command(0, 600.0),)).allowed


def test_the_elapsed_time_is_measured_not_assumed():
    """⛔ **計画の `duration` ではなく、実際の刻みである。**

    ⚠️ **計画の刻みが 0.1 秒でも、実際が 0.05 秒なら、許す量は半分である。**
    **仮定すれば 10 が通り、実測すれば 5 しか通らない。**
    """
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (Command(0, 500.0),))
    assert not gate.submit(0.05, (Command(0, 510.0),)).allowed  # 0.05 秒 × 100 = 5
    # ⚠️ **その拒否が基準を 0.05 へ動かした。ゆえにここは 0.1 秒ぶん在る**
    assert gate.submit(0.15, (Command(0, 510.0),)).allowed


def test_a_refusal_advances_the_clock_but_not_the_value():
    """⛔ **弾いた回も、保った組を送っている。** ゆえに時計は進む。

    ⇒ **次に許す量の基準は、その送信からの経過時間である**——
    **拒否が続いたぶんだけ、大きく動かしてよいことにはならない。**
    """
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (Command(0, 500.0),))
    assert not gate.submit(1.0, (Command(0, 900.0),)).allowed   # 枠の外
    # ⚠️ 1.0 秒ぶんではなく、**その拒否からの 0.1 秒ぶん**しか許さない
    v = gate.submit(1.1, (Command(0, 520.0),))
    assert not v.allowed and [x.kind for x in v.violations] == ["step"]


# --------------------------------------------------------------------------
# ⛔ 提案に無い軸を、黙らせない（2026-10-15）
# --------------------------------------------------------------------------


def test_an_axis_missing_from_the_proposal_is_still_filled_in():
    """⛔ **提案に無い軸が、出力から消えない。**

    ⚠️ **これは2台目のために見つけた、1台目の欠陥である。**
    門は `proposed` を回すだけであり、`out` に入るのは**提案された軸だけ**だった——
    **が、同じ関数の docstring は「空を返す軸は1つも無い」と主張していた。**
    `Transmitter` が毎回すべての軸を提案するので、**今日まで表に出ていなかった。**

    ⛔ **1行が2軸を運ぶ機体では、消えた軸に `encode` が何を書けばよいか分からない。**
    """
    gate = _gate(motors=3)
    v = gate.submit(1.0, (Command(1, 600.0),))
    assert v.allowed and not v.held, "⚠️ **埋めることは弾くことではない**"
    assert [c.axis for c in v.commands] == [0, 1, 2], (
        "⛔ **提案しなかった軸が、組から消えた**"
    )
    held = {c.axis: c.value for c in v.commands}
    assert held[0] == 500 and held[2] == 500, "⛔ **埋まる値は、いま機体が居る値である**"
    assert held[1] == 600


def test_filling_in_a_missing_axis_is_not_a_refusal():
    """⛔ **埋めることは「弾いた」ではない。** **ゆえに `held` は真にならない。**

    ⚠️ **`held` が言うのは「提案どおりには通さなかった」だけである**——
    **そこへ「提案に無い軸を埋めた」まで混ぜると、
    記録の上で「拒否された回」と「何もしなかった軸」が区別できなくなる。**
    """
    gate = _gate(motors=2)
    v = gate.submit(1.0, (Command(0, 512.0),))
    assert v.allowed and v.violations == () and not v.held


def test_an_axis_whose_value_the_gate_does_not_know_is_not_invented():
    """⛔ **開始位置を渡されていない軸は、埋めようが無い。**

    ⚠️ **`0.0` で埋めるのは「0 に居る」という主張である**——
    **門は、その数を使って最初の段差を測る**（`projects/pet/motion.py` の `starts_by_motor`）。
    """
    gate = _gate(motors=1)
    v = gate.submit(1.0, (Command(2, 500.0),))
    assert [x.kind for x in v.violations] == ["unknown-motor"]
    assert [c.axis for c in v.commands] == [0], (
        "⛔ **知らない軸をでっち上げた**"
    )


# --------------------------------------------------------------------------
# 壊れた組
# --------------------------------------------------------------------------


def test_two_commands_for_one_motor_are_refused():
    """⛔ **同じモーターへ2つ送ると、後が勝つ。それは計画ではない。**"""
    gate = _gate()
    v = gate.submit(1.0, (Command(0, 500.0), Command(0, 512.0)))
    assert [x.kind for x in v.violations] == ["duplicate-motor"]


def test_a_motor_the_gate_does_not_know_is_refused():
    gate = _gate(motors=1)
    v = gate.submit(1.0, (Command(2, 500.0),))
    assert [x.kind for x in v.violations] == ["unknown-motor"]


def test_a_backwards_clock_is_refused():
    """⛔ **戻る時計の上では、刻みが負になる。** 段差の検査が意味を失う。"""
    gate = _gate()
    gate.submit(2.0, (Command(0, 500.0),))
    with pytest.raises(ValueError, match="時計が戻った"):
        gate.submit(1.0, (Command(0, 500.0),))


# --------------------------------------------------------------------------
# ⛔ 門は、数を自分で持たない
# --------------------------------------------------------------------------


def test_the_gate_refuses_to_be_built_without_positions():
    with pytest.raises(ValueError, match="1つずつ"):
        Gate(starts_by_motor=(500.0, 500.0), limits_by_motor=(OPEN,),
             envelope=DOF_REALITY_ENVELOPE, wire=DofRealityWire())
    with pytest.raises(ValueError, match="モーターが1つも無い"):
        Gate(starts_by_motor=(), limits_by_motor=(),
             envelope=DOF_REALITY_ENVELOPE, wire=DofRealityWire())


def test_the_gate_cannot_be_built_without_an_envelope():
    """⛔ **枠の既定は、削除された**（2026-10-15）。

    ⚠️ **既定を持てば、門は静かに1台目の枠になる**——**そして、それは例外を1つも出さない。**
    **`Envelope` は数を1つも持たないので、`Envelope()` と書くことすらできない**
    （`limits.py` を見よ）。**ここで見ているのは、その2つ目の半分である。**
    """
    with pytest.raises(TypeError, match="envelope"):
        Gate(starts_by_motor=(500.0,), limits_by_motor=(OPEN,),
             wire=DofRealityWire())


def test_the_gate_cannot_be_built_without_a_wire():
    """⛔ **電線の既定も無い。** 門は機体を知らないので、自分で決められない。"""
    with pytest.raises(TypeError, match="wire"):
        Gate(starts_by_motor=(500.0,), limits_by_motor=(OPEN,),
             envelope=DOF_REALITY_ENVELOPE)


def test_the_gate_refuses_more_axes_than_the_wire_can_carry():
    """⛔ **電線が表せない軸へ、門は指令を出せない。**

    ⚠️ **逆向き（門のほうが少ない）は許す**——機体1の `[A xx]` は軸ごとに独立しており、
    **軸を1つだけ動かすことが、正当に表せるからである。**
    **機体2ではそれが成り立たないが、それを言うのは `encode` である**——
    **門が先回りして決めることではない。**
    """
    with pytest.raises(ValueError, match="表せない"):
        Gate(starts_by_motor=(500.0,) * 4, limits_by_motor=(OPEN,) * 4,
             envelope=DOF_REALITY_ENVELOPE, wire=DofRealityWire())


def test_a_start_position_the_wire_cannot_express_is_caught_at_construction():
    """⛔ **表せない開始位置を持つ機体は、そもそも1つも指令を受け取れない。**

    ⚠️ **最初の1組を組む瞬間ではなく、組み立てた瞬間に分かる方がよい**——
    **門は開始位置を使って段差を測るので、そこが表せないなら門は何も測れない。**
    """
    with pytest.raises(ValueError, match="収まらない"):
        Gate(starts_by_motor=(5000.0,), limits_by_motor=(OPEN,),
             envelope=Envelope(target_min=None, target_max=None),
             wire=DofRealityWire())


def test_the_gate_can_only_refuse_in_four_ways():
    """⛔ **拒否の語は、閉じた集合である。**

    ⚠️ **`unknown-command` は、ここから消えた**（2026-10-15）——
    あれは `Frame.motor()` が投げる例外を捕まえる枝であり、
    **通貨が `Command`（軸はただの `int`）になって、到達しなくなった。**
    ⛔ **到達しない枝は、docstring が「必ず何かが返る」と言っている範囲を静かに広げる**——
    **ゆえに消したことを、ここで数える。**
    """
    source = (Path(__file__).resolve().parents[1] / "engine" / "backend" / "gate.py")
    kinds = set(re.findall(r'Violation\(\s*"([a-z-]+)"', source.read_text("utf-8")))
    assert kinds == {"target", "step", "duplicate-motor", "unknown-motor"}, (
        f"⛔ **拒否の語が動いた: {sorted(kinds)}**"
    )
