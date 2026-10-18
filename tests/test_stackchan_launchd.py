# -*- coding: utf-8 -*-
"""**設置されるジョブの、複製。**

⛔ **このファイルが読むのは `projects/stackchan/launchd/` の1枚だけである。**
`~/Library/LaunchAgents/` はここには無い——**緑は「設置された」を意味しない。**
設置は 2026-10-19 に手で行い、その事実は `HISTORY.md` に在る。

⚠️ **それでもこれを書いたのは、スイッチがコードの外に在るからである。**
`--sound on` はどの試験も読まない引数であり、誰かが複製から落としても
他は全部緑のままである。
"""
from __future__ import annotations

import pathlib
import plistlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
COPY = (
    ROOT / "projects" / "stackchan" / "launchd"
    / "embodied-kinetic-loom.stackchan.plist"
)


def arguments() -> list[str]:
    with COPY.open("rb") as fh:
        return plistlib.load(fh)["ProgramArguments"]


def test_the_copy_parses_and_names_its_label():
    """⚠️ **ファイルとして読めること**——複製が壊れていれば、設置も壊れる。"""
    with COPY.open("rb") as fh:
        data = plistlib.load(fh)
    assert data["Label"] == "embodied-kinetic-loom.stackchan"
    assert data["RunAtLoad"] is True


def test_the_speaker_is_switched_on():
    """✅ **2026-10-19 05:27、著者の「進めて」のあとに倒された。**

    ⛔ **既定は今も `off` である**——この行は既定ではなく、このジョブの決定である。
    """
    args = arguments()
    assert "--sound" in args
    assert args[args.index("--sound") + 1] == "on"


def test_the_hour_is_not_written_into_the_job():
    """⛔ **時刻は `quiet.py` に在る。** ジョブが時を名指せば、規則は2箇所になる。"""
    for token in arguments():
        assert "QUIET" not in token
        assert token not in ("21", "05", "5", "quiet")


def test_the_port_is_named_once():
    """⚠️ **機体2のコンソールは、ここで1度だけ名指される。**"""
    assert arguments().count("--port") == 1
