# -*- coding: utf-8 -*-
"""**デーモンのログを、数える。** ⛔ **何が起きたかは言わない**——数えるだけである。

⚠️ **このファイルはファイルも時計も読まない。** 行を受け取り、数えて返す
（`quiet.py` と同じ形であり、`daemon/room.py` とも同じである）。
⇒ **同じ行を渡せば、同じ数が返る。**

## なぜ、要るのか

⚠️ **ログは既に在る。** 2026-10-19 の朝の時点で `/tmp/ekl-stackchan-daemon.log` は
**3,761行、900 KB** であり、その中身は1行1つの JSON である。
⛔ **読む者が居なければ、それは記録ではない。** 行が増えるほど、読まれなくなる。

⚠️ **8段目（日々ともに暮らせるか）の「1日を書き留める」は、まだ誰も書いていない。**
⇒ **これはその日ではない。** これは**その日が来たときに引用できる数**を作る計器である——
記録の背骨は観察であり、**数はその中に証拠として引用される**（`CLAUDE.md`）。

## 数え方

⛔ **沈黙と失敗を混ぜない。** `heard: false` は**コンソールが答えなかった**ことであり、
`heard: true` で `position: null` は**コンソールは答えたが、サーボが答えなかった**ことである。
⇒ **2つは別の欄である。**

⛔ **枠が「送られた」は、基板が受け取ったことではない。** `sent` は
`os.write` が行の長さを返したことだけを言う（`docs/stackchan-daemon.md`）。
⇒ **`sent` の数と `emitted` の数を分けて数える。**

⚠️ **読めない行は捨てない。** 数える——**ログ自身が壊れていることも、測定である。**
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterable

__all__ = ["Summary", "summarize", "render"]


def _bump(counter: dict[str, int], key: object) -> None:
    """⚠️ **`None` は数えない。** 欄が空であることは、その語が起きたことではない。"""
    if isinstance(key, str) and key:
        counter[key] = counter.get(key, 0) + 1


@dataclass
class Summary:
    """**1本のログから数えられるもの、その全部。** ⚠️ **時刻は持たない**——時計は縁のものである。"""

    lines: int = 0              # 空でない行
    unreadable: int = 0         # JSON のオブジェクトでない行
    bad_frames: int = 0         # `frame` の中身が JSON でない行
    starts: int = 0             # `daemon: listening`
    decisions: int = 0          # `ok` の行
    frames: int = 0             # `frame` の行（送られたかは問わない）
    frames_sent: int = 0        # そのうち `sent: true`
    # ✅ **2026-10-19（0.19.41）から、基板の受理の言葉も数える。**
    # ⛔ **`sent` は tty のことであり、`accepted` は基板のことである。**
    frames_accepted: int = 0    # 基板が受理の行を印字した
    frames_refused: int = 0     # 基板が名指しで断った
    frames_unheard: int = 0     # 何も言わなかった（**断ったのではない**）
    streamed: int = 0           # 首の予定（`neck` と `poses`）
    poses: int = 0              # 予定された姿勢の数の合計
    applied: int = 0            # **デーモンが**書いた姿勢の合計（＝送った数である）
    late: int = 0               # そのうち遅れていたもの
    held: int = 0               # 基板が保持した姿勢の合計
    # ✅ **2026-10-19（0.19.38）から、基板自身の数も数える。**
    # ⛔ **上の `applied` は「送った数」であり、基板が「適用した」数ではない。**
    # その日、`recoil` の流しは `applied: 18` と書かれ、次の探針は頭が0カウントしか
    # 動いていないことを読んだ——**2つの数は別の問いに答える。**
    verdicts: int = 0           # 基板が自分の判定を印字した回数
    verdict_silent: int = 0     # 判定が届かなかった回数（基板は何も言わなかった）
    board_applied: int = 0      # 基板が数えた「適用した」の合計
    board_refused: int = 0      # 基板が断った行の合計
    board_clamped: int = 0      # 基板が丸めた行の合計
    readbacks: int = 0          # `heard` の行
    heard: int = 0              # コンソールが答えた
    positions: int = 0          # サーボが位置を返した
    phases: dict[str, int] = field(default_factory=dict)
    faces: dict[str, int] = field(default_factory=dict)
    lights: dict[str, int] = field(default_factory=dict)
    sounds: dict[str, int] = field(default_factory=dict)
    gestures: dict[str, int] = field(default_factory=dict)


def summarize(lines: Iterable[str]) -> Summary:
    """**行を数える。** ⚠️ **行は順序を持たない**——数え上げであるからである。"""
    s = Summary()
    for raw in lines:
        text = raw.strip()
        if not text:
            continue
        s.lines += 1
        try:
            obj = json.loads(text)
        except ValueError:
            s.unreadable += 1
            continue
        if not isinstance(obj, dict):
            s.unreadable += 1
            continue

        if obj.get("daemon") == "listening":
            s.starts += 1
            continue

        if "frame" in obj:
            s.frames += 1
            # ⚠️ **3つに分ける。** ⛔ `None`（と、この欄より前の行）は「聞こえなかった」
            #    であり、「断られた」ではない——2つを同じ数にしない。
            accepted = obj.get("accepted")
            if accepted is True:
                s.frames_accepted += 1
            elif accepted is False:
                s.frames_refused += 1
            else:
                s.frames_unheard += 1
            if obj.get("sent") is True:
                s.frames_sent += 1
                body = obj.get("frame")
                try:
                    frame = json.loads(body) if isinstance(body, str) else body
                except ValueError:
                    frame = None
                if not isinstance(frame, dict):
                    s.bad_frames += 1
                else:
                    # ⚠️ 語は、**送られた枠**のものだけを数える。
                    _bump(s.sounds, frame.get("sound"))
                    _bump(s.gestures, frame.get("gesture"))
                    _bump(s.faces, frame.get("face"))
                    _bump(s.lights, frame.get("light"))
            continue

        # ⚠️ **古い形の探針も数える。** ⛔ 2026-10-19 まで、成功した探針は
        #    `heard` を持たない形で書かれていた——**その行は数えられず、
        #    `unreadable` に入っていた**（その日のログ: `readbacks 46`、`positions 0`、
        #    `unreadable 58`）。⇒ **この検査は、前の形のログにも効く。**
        if "heard" in obj or "position" in obj:
            s.readbacks += 1
            # ⚠️ **位置が読めたなら、コンソールは答えた。** ⛔ 古い形は `heard` を
            #    持たないので、そのままだと成功が「聞こえなかった」に数えられる。
            if obj.get("heard") is True or obj.get("position") is not None:
                s.heard += 1
            if obj.get("position") is not None:
                s.positions += 1
            continue

        if "neck" in obj:
            if "verdict" in obj:
                # ⚠️ **判定の行である。** ⛔ `None` は「断らなかった」ではなく
                #    **「基板が何も言わなかった」**である——2つを同じ数にしない。
                found = obj.get("verdict")
                if isinstance(found, dict):
                    s.verdicts += 1
                    for key, target in (
                        ("applied", "board_applied"),
                        ("refused", "board_refused"),
                        ("clamped", "board_clamped"),
                    ):
                        value = found.get(key)
                        if isinstance(value, int):
                            setattr(s, target, getattr(s, target) + value)
                else:
                    s.verdict_silent += 1
                continue
            if "poses" in obj:
                s.streamed += 1
                poses = obj.get("poses")
                if isinstance(poses, int):
                    s.poses += poses
            else:
                for key, target in (
                    ("applied", "applied"), ("late", "late"), ("held", "held")
                ):
                    value = obj.get(key)
                    if isinstance(value, int):
                        setattr(s, target, getattr(s, target) + value)
            continue

        if "ok" in obj:
            s.decisions += 1
            _bump(s.phases, obj.get("phase"))
            continue

        # ⚠️ 知らない形の JSON は、数えずに捨てる——**捨てたことを言うために数える。**
        s.unreadable += 1
    return s


def render(s: Summary) -> str:
    """**数えたものを、人が読める行にする。** ⛔ **足し算はしない**——数えたものをそのまま出す。"""
    def row(name: str, value: object) -> str:
        # ⚠️ 名前の欄は 16 文字である。**数えるものが増えても、桁は動かない。**
        return f"{name:<16}{value}"

    out = [
        row("lines", s.lines),
        row("unreadable", s.unreadable),
        row("bad frames", s.bad_frames),
        row("daemon starts", s.starts),
        row("decisions", s.decisions),
        row("frames", s.frames),
        row("frames sent", s.frames_sent),
        row("  accepted", s.frames_accepted),
        row("  refused", s.frames_refused),
        row("  unheard", s.frames_unheard),
        row("neck streamed", s.streamed),
        row("poses planned", s.poses),
        row("poses applied", s.applied),
        row("  late", s.late),
        row("  held", s.held),
        row("verdicts", s.verdicts),
        row("  silent", s.verdict_silent),
        row("  board applied", s.board_applied),
        row("  board refused", s.board_refused),
        row("  board clamped", s.board_clamped),
        row("readbacks", s.readbacks),
        row("  heard", s.heard),
        row("  positions", s.positions),
    ]
    for name, counter in (
        ("phases", s.phases),
        ("faces", s.faces),
        ("lights", s.lights),
        ("sounds", s.sounds),
        ("gestures", s.gestures),
    ):
        if not counter:
            out.append(row(name, "-"))
            continue
        for word, count in sorted(counter.items()):
            out.append(row(name, f"{word} {count}"))
            name = ""
    return "\n".join(out)
