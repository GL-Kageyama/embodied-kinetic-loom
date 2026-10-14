# -*- coding: utf-8 -*-
"""送信——**軌道を、実際の時刻で引く。**

⛔ **このファイルの中心は `test_a_late_tick_selects_the_sample_nearest_the_wall_clock` である。**

`Trajectory.at(t)` は**補間しない**（`plan.py` を見よ）。⚠️ **だが、周期ループの `now` は
標本点に落ちない**——遅れるからである。

⇒ **標本を1つずつ進めると、軌道がゆっくりになる。** 5秒の動作が、遅れたぶんだけ長くかかる。
**これは機体の上では「別の動作」である。**

⇒ **ゆえにここは `now` にいちばん近い標本を選ぶ。** 遅れた刻みは**標本を飛ばす**——
**そして、その段差は門が捕まえる**（`gate.py`）。**遅れは消せない。だが「遅れたときに
何が機体へ行くか」は選べる。**
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.backend.axis_map import AxisMap, ChannelCalibration
from engine.backend.gate import Gate
from engine.backend.protocol import DOF_REALITY_ENVELOPE, DofRealityWire, encode_target
from engine.backend.transmit import Transmitter
from engine.trajectory.limits import ChannelLimits
from engine.trajectory.plan import plan

DURATION = 1.0
COUNT = 11  # ⚠️ 刻みは 0.1 秒である


def _calibration():
    return ChannelCalibration(motor=0, sign=1, offset=0.0, scale=1.0)


def _rig(start=500.0, end=600.0, limits=None, duration=DURATION, count=COUNT):
    traj = plan(starts=(start,), ends=(end,), duration=duration,
                labels=("pitch",), count=count)
    amap = AxisMap(channels={"pitch": _calibration()})
    wire = DofRealityWire()
    gate = Gate(
        starts_by_motor=(amap.to_counts("pitch", start),),
        limits_by_motor=(limits or ChannelLimits(),),
        envelope=DOF_REALITY_ENVELOPE,
        wire=wire,
    )
    return Transmitter(trajectory=traj, axis_map=amap, gate=gate, wire=wire)


# --------------------------------------------------------------------------
# ⛔ 遅れは、軌道をゆっくりにしない
# --------------------------------------------------------------------------


def test_at_time_zero_the_first_sample_is_sent():
    tx = _rig()
    fs = tx.frames_at(0.0, 0.0)
    assert fs.sample_t == 0.0 and fs.stale_by == pytest.approx(0.0)
    assert fs.verdict.commands[0].value == 500


def test_an_on_time_tick_has_no_staleness():
    """⚠️ **`stale_by` は「送った値が、どの時刻の値か」の代償である。** 0 が理想。"""
    tx = _rig()
    fs = tx.frames_at(0.0, 0.5)
    assert fs.sample_t == pytest.approx(0.5)
    assert fs.at == pytest.approx(0.5)
    assert fs.stale_by == pytest.approx(0.0)


def test_a_late_tick_selects_the_sample_nearest_the_wall_clock():
    """⛔ **ここが中心である。**

    0.3 秒で送ったあと、次が 0.9 秒になる。**標本を1つずつ進めるなら、次は 0.4 秒の値である**——
    **軌道が6倍ゆっくりになる。** ここは **0.9 秒の値を選ぶ。**
    ⚠️ **その代償が `stale_by` である。この場合は 0 である**——
    **壁時計に追いついているので、値は古くない。古くなるのは、標本の間を飛ばした側である。**
    """
    tx = _rig()
    tx.frames_at(0.0, 0.3)
    fs = tx.frames_at(0.0, 0.9)
    assert fs.sample_t == pytest.approx(0.9), "⛔ **標本を1つずつ進めている＝軌道が遅くなる**"
    assert fs.stale_by == pytest.approx(0.0)
    # ⚠️ 5つ以上を飛ばしている（0.4 0.5 0.6 0.7 0.8）
    assert fs.sample_t - 0.3 > 5 * 0.1


def test_a_tick_between_samples_takes_the_nearest_one():
    """⚠️ **周期と標本の刻みは、一致している必要が無い。**"""
    tx = _rig()
    fs = tx.frames_at(0.0, 0.31)
    assert fs.sample_t == pytest.approx(0.3)
    assert fs.stale_by == pytest.approx(0.01), "⚠️ **ここで初めて古さが出る**"


def test_past_the_end_the_last_sample_is_held():
    """⚠️ **軌道の外へは出ない。** 端は最後の標本である。"""
    tx = _rig()
    fs = tx.frames_at(0.0, 5.0)
    assert fs.sample_t == pytest.approx(DURATION)
    assert fs.verdict.commands[0].value == 600
    assert fs.stale_by == pytest.approx(4.0), "⛔ **4秒古い値を送っていると、言えること**"


def test_a_time_before_the_trajectory_starts_is_refused():
    tx = _rig()
    with pytest.raises(ValueError, match="軌道が始まる前"):
        tx.frames_at(1.0, 0.5)


# --------------------------------------------------------------------------
# ⛔ 丸めは、門の手前で起きる
# --------------------------------------------------------------------------


def test_the_gate_sees_the_rounded_value_not_the_raw_one():
    """⛔ **丸めは送る値を変える。ゆえに門は、丸めた後を見る。**

    **そうでないと、門は「出て行かない値」を検査していることになる。**
    ⚠️ ここでは 0.1 秒の標本が **500.856**（min-jerk の形）で、**送るのは 501** である。
    **門の違反が報告する段差が 1.0 なら、門は 501 を見ている。**
    """
    tx = _rig(limits=ChannelLimits(velocity=1.0))  # ⛔ 1 カウント/秒
    tx.frames_at(0.0, 0.0)
    fs = tx.frames_at(0.0, 0.1)
    assert fs.sample_t == pytest.approx(0.1)
    assert not fs.verdict.allowed
    violation = fs.verdict.violations[0]
    assert violation.kind == "step"
    assert violation.value == 1.0, f"丸める前の値を見ている: {violation.value}"


def test_a_refusal_still_carries_commands_to_send():
    """⛔ **「送らない」は「止まる」ではない**（`gate.py` を見よ）。

    **門が弾いたとき、送信側が空を送ってはいけない。**
    """
    tx = _rig(limits=ChannelLimits(velocity=1.0))
    tx.frames_at(0.0, 0.0)
    fs = tx.frames_at(0.0, 0.1)
    assert not fs.verdict.allowed and fs.verdict.held
    assert fs.verdict.commands[0].value == 500, "⛔ **弾いたときに空を返した**"


# --------------------------------------------------------------------------
# 決定論
# --------------------------------------------------------------------------


def test_the_same_call_gives_the_same_bytes():
    """⚠️ **ここが「決定論的」の意味である**（`CLAUDE.md` の固定方針）。"""
    a, b = _rig(), _rig()
    fa, fb = a.frames_at(0.0, 0.7), b.frames_at(0.0, 0.7)
    assert fa.payload == fb.payload, "⚠️ **同じ入力から、同じバイト列が出る**"
    assert fa.sample_t == fb.sample_t


def test_done_is_not_the_machine_stopping():
    """⛔ **「軌道が終わった」は「機体が止まった」ではない。**

    **この機体は、自分が何をしたかを報告してこない**（`CLAUDE.md` の固定方針）。
    """
    tx = _rig()
    assert not tx.done(0.0, 0.99)
    assert tx.done(0.0, 1.0)
    assert tx.done(0.0, 2.0)


# --------------------------------------------------------------------------
# ⛔ バイト列は、門の後ろで組まれる（2026-10-15）
# --------------------------------------------------------------------------


def test_the_payload_is_the_bytes_the_wire_would_write():
    """⛔ **弾かれた刻みでも、バイト列は空にならない。**

    ⚠️ **組む元が「提案」ではなく「門を通った組」である**——
    **ゆえにここには、保った値のバイト列が出る。**
    """
    tx = _rig(limits=ChannelLimits(velocity=1.0))  # ⛔ 1 カウント/秒
    tx.frames_at(0.0, 0.0)
    fs = tx.frames_at(0.0, 0.1)
    assert not fs.verdict.allowed
    assert fs.payload == encode_target(0, 500).raw, (
        "⛔ **弾いた刻みで空を送った。それは停止ではない**"
    )


def _identifiers(path: Path) -> set[str]:
    """⚠️ **散文ではなく、識別子を集める。**

    ⛔ **原文を探すと、この検査は自分の説明文に鳴る**——`transmit.py` の docstring は
    **「かつて `encode_target` を呼んでいた」と書いており、それは正しい文である。**
    ⇒ **AST で名前だけを見る。** `tools/purity.py` が grep ではなく AST を使うのと同じ理由である。
    """
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text("utf-8"))):
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                out.add(alias.name.split(".")[-1])
                if alias.asname:
                    out.add(alias.asname)
    return out


def test_the_payload_does_not_name_the_machine():
    """⚠️ **この層は、機体の名前を1つも書かない。** バイト列は電線が作る。

    ⛔ **ここで見ているのは、その分離が実際に効いていることである**——
    **`Transmitter` は `Wire` の3つのメソッドしか呼ばない。**
    """
    path = Path(__file__).resolve().parents[1] / "engine" / "backend" / "transmit.py"
    forbidden = {
        "encode_target", "decode_frames", "MOTOR_LETTERS", "MAX_TARGET", "Frame",
        "ProtocolError", "FeedbackDiv4",            # 機体1の語
        "DofRealityWire", "DOF_REALITY_ENVELOPE",   # 機体1の名前
    }
    named = _identifiers(path) & forbidden
    assert not named, f"⛔ **送信層が機体1の語を書いている: {sorted(named)}**"


class _OtherWire:
    """⚠️ **2台目の代役である。** ⛔ **実装ではない**——

    この段では機体はまだ1台であり、**2台目の数え方は未測定である**（計画を見よ）。
    **ここで見たいのは、食い違いが組めないことだけである。**
    """

    def axis_count(self) -> int:
        return 1

    def quantize(self, value: float) -> float:
        return float(value)

    def encode(self, commands) -> bytes:
        return b""


def test_a_transmitter_refuses_a_wire_the_gate_does_not_have():
    """⛔ **2台ぶんの誤りが、1台の上で静かに混ざる形を、組めなくする。**

    ⚠️ **門に機体1の電線を挿し、ここに別の電線を挿すと、
    門が機体1の数え方で丸めた値を、別の機体の言葉で書くことになる。**
    ⇒ **「気をつける」ではなく、`__post_init__` で照合する。**
    """
    tx = _rig()
    with pytest.raises(ValueError, match="電線が違う"):
        Transmitter(trajectory=tx.trajectory, axis_map=tx.axis_map,
                    gate=tx.gate, wire=_OtherWire())
