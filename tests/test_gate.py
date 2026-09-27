# -*- coding: utf-8 -*-
"""門——**実際に出て行く1フレームを見る。**

⛔ **このファイルの中心は `test_a_refusal_still_sends_something` である。**

**「送らない」は「止まる」ではない。**
> **送信をやめると、15秒でトルクがおよそ 1/4 になる——そして、モーターは止まらない。**
> （`CLAUDE.md` の安全の節）

⇒ **ゆえに門は、弾いたときに空を返してはいけない。**
**最後に通した組を返し続ける。** **ここに書いておかないと、
「安全のために送信を止める」という、いちばん危ない実装が、自然に生える。**
"""
from __future__ import annotations

import pytest

from engine.backend.gate import Gate
from engine.backend.protocol import encode_target
from engine.trajectory.limits import ChannelLimits, Envelope

OPEN = ChannelLimits()  # ⚠️ 全部 None ＝ 制限しない
SLOW = ChannelLimits(velocity=100.0)  # 100 カウント/秒


def _gate(motors=1, limits=None, envelope=None):
    kw = {}
    if envelope is not None:
        kw["envelope"] = envelope
    return Gate(
        starts_by_motor=tuple(500.0 for _ in range(motors)),
        limits_by_motor=tuple(limits or OPEN for _ in range(motors)),
        **kw,
    )


# --------------------------------------------------------------------------
# 通る
# --------------------------------------------------------------------------


def test_a_frame_inside_the_envelope_passes():
    gate = _gate()
    v = gate.submit(1.0, (encode_target(0, 512),))
    assert v.allowed and not v.held and v.frames[0].value == 512


def test_none_in_the_envelope_means_do_not_limit():
    """⚠️ **`None` は「制限しない」である**（`limits.py` の規則）。"""
    gate = _gate(envelope=Envelope(target_min=None, target_max=None))
    assert gate.submit(1.0, (encode_target(0, 1024),)).allowed


# --------------------------------------------------------------------------
# 弾く——⛔ そして、それでも送る
# --------------------------------------------------------------------------


def test_outside_the_envelope_is_refused():
    gate = _gate()
    v = gate.submit(1.0, (encode_target(0, 900),))
    assert not v.allowed and v.held
    assert [x.kind for x in v.violations] == ["target"]
    assert v.violations[0].limit == 833.0


def test_a_refusal_still_sends_something():
    """⛔ **ここが要点である。** 弾くことは、黙ることを意味しない。"""
    gate = _gate()
    good = (encode_target(0, 512),)
    gate.submit(1.0, good)
    v = gate.submit(2.0, (encode_target(0, 900),))
    assert not v.allowed
    assert v.frames == good, "⛔ **弾いたときに空を返した。それは停止ではない**"


def test_the_first_refusal_can_only_be_empty():
    """⚠️ **まだ1つも通していなければ、保つものが無い。** これは限界であって、設計ではない。"""
    gate = _gate()
    v = gate.submit(1.0, (encode_target(0, 900),))
    assert not v.allowed and v.frames == () and gate.hold() == ()


def test_a_refused_frame_does_not_move_the_last_value():
    """⛔ **拒否された値が「前回値」になると、次の段差の基準が汚れる。**"""
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (encode_target(0, 500),))
    gate.submit(1.0, (encode_target(0, 900),))  # 弾かれる（枠の外）
    v = gate.submit(2.0, (encode_target(0, 520),))
    assert v.allowed, f"基準が汚れている: {v.violations}"


# --------------------------------------------------------------------------
# 段差——⛔ 門にしか見えない
# --------------------------------------------------------------------------


def test_a_step_is_refused_even_inside_the_envelope():
    """⛔ **枠の内側でも、届く速さを超えれば段差である。**
    上流ファームに補間が無いので、**段差は段差のまま入る**（§2.6）。"""
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (encode_target(0, 500),))
    v = gate.submit(0.001, (encode_target(0, 600),))  # 1 ms で 100 カウント
    assert not v.allowed
    assert [x.kind for x in v.violations] == ["step"]


def test_the_step_check_is_a_rate_not_a_magnitude():
    """⚠️ **同じ 100 カウントが、時間が在れば通る。** 大きさではなく速さの話である。"""
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (encode_target(0, 500),))
    assert gate.submit(2.0, (encode_target(0, 600),)).allowed


def test_the_elapsed_time_is_measured_not_assumed():
    """⛔ **計画の `duration` ではなく、実際の刻みである。**

    ⚠️ **計画の刻みが 0.1 秒でも、実際が 0.05 秒なら、許す量は半分である。**
    **仮定すれば 10 が通り、実測すれば 5 しか通らない。**
    """
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (encode_target(0, 500),))
    assert not gate.submit(0.05, (encode_target(0, 510),)).allowed  # 0.05 秒 × 100 = 5
    # ⚠️ **その拒否が基準を 0.05 へ動かした。ゆえにここは 0.1 秒ぶん在る**
    assert gate.submit(0.15, (encode_target(0, 510),)).allowed


def test_a_refusal_advances_the_clock_but_not_the_value():
    """⛔ **弾いた回も、保った組を送っている。** ゆえに時計は進む。

    ⇒ **次に許す量の基準は、その送信からの経過時間である**——
    **拒否が続いたぶんだけ、大きく動かしてよいことにはならない。**
    """
    gate = _gate(limits=SLOW)
    gate.submit(0.0, (encode_target(0, 500),))
    assert not gate.submit(1.0, (encode_target(0, 900),)).allowed   # 枠の外
    # ⚠️ 1.0 秒ぶんではなく、**その拒否からの 0.1 秒ぶん**しか許さない
    v = gate.submit(1.1, (encode_target(0, 520),))
    assert not v.allowed and [x.kind for x in v.violations] == ["step"]


# --------------------------------------------------------------------------
# 壊れた組
# --------------------------------------------------------------------------


def test_two_frames_for_one_motor_are_refused():
    """⛔ **同じモーターへ2つ送ると、後が勝つ。それは計画ではない。**"""
    gate = _gate()
    v = gate.submit(1.0, (encode_target(0, 500), encode_target(0, 512)))
    assert [x.kind for x in v.violations] == ["duplicate-motor"]


def test_a_motor_the_gate_does_not_know_is_refused():
    gate = _gate(motors=1)
    v = gate.submit(1.0, (encode_target(2, 500),))
    assert [x.kind for x in v.violations] == ["unknown-motor"]


def test_a_backwards_clock_is_refused():
    """⛔ **戻る時計の上では、刻みが負になる。** 段差の検査が意味を失う。"""
    gate = _gate()
    gate.submit(2.0, (encode_target(0, 500),))
    with pytest.raises(ValueError, match="時計が戻った"):
        gate.submit(1.0, (encode_target(0, 500),))


def test_the_gate_refuses_to_be_built_without_positions():
    with pytest.raises(ValueError, match="1つずつ"):
        Gate(starts_by_motor=(500.0, 500.0), limits_by_motor=(OPEN,))
    with pytest.raises(ValueError, match="モーターが1つも無い"):
        Gate(starts_by_motor=(), limits_by_motor=())
