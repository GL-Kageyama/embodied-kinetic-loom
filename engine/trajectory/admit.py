# -*- coding: utf-8 -*-
"""関門——**通すか、弾くか。**

⚠️ **これは「席」ではない。** Safety が層なのか関門なのか（構想 U-01 / 04_Safetyの席）は**未決**であり、
**どちらでもこの関数は呼ばれる。** ここに在るのは判定であって、配置ではない。
⇒ **ゆえにファイル名も `safety.py` にしていない。** 席を名乗れば、決まっていないものを決めたことになる。

⛔ **そして、この関門は「計画時」の側だけである。**
[02_調査/02] §4.3 の逐語は
*"design-time assurance alone is indeed insufficient for autonomous CPS"*——
**計画時の保証だけでは足りない。** **実行時に見張る門は、まだ無い**（実機とバックエンドが要る）。

⚠️ **D-08（誰が軌道を持つか）を、これは先取りしていない。**
「計画時に弾く」は、**軌道を送る側が誰であっても要る**——**送る前に検めるには、送る前に計算するしかない。**
分岐するのは*送る*側であって、*検める*側ではない。
"""
from __future__ import annotations

from dataclasses import dataclass

from .limits import Envelope, Violation, check_targets, check_trajectory
from .plan import DEFAULT_SAMPLES, Trajectory, plan
from .profile import Trapezoid, trapezoid_for_velocity

__all__ = ["Admission", "Rejection", "admit", "trapezoid_reachability"]


@dataclass(frozen=True)
class Admission:
    """通った。**組ごとの軌道を、送る順に持つ。**"""

    trajectories: tuple[Trajectory, ...]


@dataclass(frozen=True)
class Rejection:
    """弾いた。**理由の名前と、違反の列を持つ**——「弾いた」だけでは直せない。"""

    reason: str
    violations: tuple[Violation, ...] = ()


def trapezoid_reachability(intent, starts_by_dof, limits_by_dof,
                           profile: Trapezoid) -> tuple[Rejection, ...]:
    """台形の族のうち、**この時間で速度上限を守れるものが1つでも在るか**を、組ごとに先に見る。

    ⚠️ **「速く走れるか」ではない。逆である。**
    台形の正規化した最高速度は `1/(1−r/2)` で、**族の下限は 1 である**（`r → 0`）。
    実速度の下限は `|Δ|/d` だから——

        `|Δ|/d > v_limit` なら、**族のどの r でも上限を超える。**
        ⇒ **これは「軌道が上限を超えた」ではなく「正しい軌道が存在しない」である。**

    ⚠️ **これは検査 #3（可到達性）の中身である。**
    [05_実機なしで作る] §2 が「5つのうち、これは異物である」と書いたもの——
    **#4 が「組んだ軌道が超えた」と言うのに対し、#3 は「組める軌道が無い」と言う。**
    ⛔ **机上の話ではない。** 箱の既定では、送れる目標が 190〜833 に限られる（`Envelope`）。

    ⚠️ **`profile` は使わない。** 引数に在るのは、**族を明示するためである**——
    `admit` が `isinstance(profile, Trapezoid)` で呼び分けている。
    """
    # ⛔ **ここも組を跨いで位置が動く。** `admit` の 4 と同じ理由である——
    # **2組目の移動量は、1組目の終わりからの距離である。**
    position = dict(starts_by_dof)
    out = []
    for group in intent.groups():
        for move in group:
            start = position[move.dof]
            limit = limits_by_dof[move.dof].velocity
            if limit is None:
                continue
            _, ok = trapezoid_for_velocity(move.target - start, move.duration_ms / 1000.0, limit)
            if not ok:
                out.append(Rejection(
                    f"可到達性: {move.dof} は {move.duration_ms} ms では、"
                    f"速度上限 {limit} を守る台形が族に無い"
                ))
        for move in group:
            position[move.dof] = move.target
    return tuple(out)


def admit(intent, starts_by_dof, limits_by_dof, envelope: Envelope | None = None,
          profile="min-jerk", count: int = DEFAULT_SAMPLES):
    """意図を検めて、通すか弾くか。

    ⚠️ **`starts_by_dof` と `limits_by_dof` は、呼ぶ側が揃える。**
    現在位置は機体のフィードバックから来て、上限は配線から来る——
    **どちらも自由度とモーターの対応を知っている側にしか無い**（`plan.py` を見よ）。
    **このリポジトリは、その対応を決めない。**

    順に、4つを見る:

        1. 知らない自由度が無いか（開始位置と上限が、すべての move に在るか）
        2. 行き先が枠の内側か                        ← `check_targets`
        3. 台形なら、その時間で届くか                ← `trapezoid_reachability`
        4. 軌道を組んで、軸ごとと合成の上限を超えないか ← `check_trajectory`

    ⛔ **4 は 2 を含まない。** 目標が枠の内側でも、途中で超えることはある。
    """
    if envelope is None:
        envelope = Envelope()

    # 1. 知らない自由度
    for move in intent.moves:
        if move.dof not in starts_by_dof:
            return Rejection(f"自由度 {move.dof!r} の現在位置が渡されていない")
        if move.dof not in limits_by_dof:
            return Rejection(f"自由度 {move.dof!r} の上限が渡されていない")

    # 2. 枠
    violations = list(check_targets(tuple(m.target for m in intent.moves), envelope))
    if violations:
        return Rejection("目標が枠の外である", tuple(violations))

    # 3. 可到達性（台形のときだけ）
    if isinstance(profile, Trapezoid):
        for rejection in trapezoid_reachability(intent, starts_by_dof, limits_by_dof, profile):
            return rejection

    # 4. 制限
    #
    # ⛔ **組を跨いで、位置は動く。** `starts_by_dof` は**最初の1組の開始位置**であって、
    # すべての組の開始位置ではない——**2組目は、1組目が終わった場所から始まる。**
    #
    # ⚠️ **この版の最初は、どの組も `starts_by_dof` から始めていた。**
    # 同じ自由度が2つの組に現れると（例: 前傾して、戻る）、**2組目の軌道が
    # 「初期位置 → 2組目の目標」になり**、機体は1組目の終わりに居るのに
    # **その場所から始まる軌道が組まれる。**
    # ⇒ **組の境目で、機体は軌道の最初の標本へ飛ぶ。** **それは段差である**——
    # **上流ファームにソフトスタートは無く、`CLAUDE.md` は「段差を送るな」と書いている。**
    # ⛔ **そして、この誤りは制限の検査では捕まらない。** 戻る軌道は、
    # **どの上限の内側にも収まっている**——**合法な形をした、意味の違う軌道である。**
    # ⚠️ **既存の唯一の2組の検査（`tests/test_admit.py`）は、組ごとに別の自由度を使っていた**——
    # **ゆえに緑のまま、この誤りを1度も踏まなかった**（実測 2026-09-28）。
    position = dict(starts_by_dof)
    trajectories = []
    for group in intent.groups():
        starts = tuple(position[m.dof] for m in group)
        ends = tuple(m.target for m in group)
        labels = tuple(m.dof for m in group)
        limits = tuple(limits_by_dof[m.dof] for m in group)
        trajectory = plan(starts, ends, group[0].duration_ms / 1000.0,
                          profile=profile, labels=labels, count=count)
        found = list(check_trajectory(trajectory, limits, envelope))
        if found:
            return Rejection("軌道が上限を超える", tuple(found))
        trajectories.append(trajectory)
        # ⛔ **1組終わるたびに、位置を更新する。** **標本の最後ではなく、目標を書く**——
        # `plan` の端の値は目標そのものである（端の条件）。
        for move in group:
            position[move.dof] = move.target

    return Admission(trajectories)
