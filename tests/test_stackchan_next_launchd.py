# -*- coding: utf-8 -*-
"""**2つ目の層の、設置されるジョブの複製。**

⛔ **このファイルが読むのは `projects/stackchan_next/launchd/` の1枚だけである。**
`~/Library/LaunchAgents/` はここには無い——**緑は「設置された」を意味しない。**
設置は 2026-10-20 に手で行い、その事実は `HISTORY.md` に在る。

⚠️ **最初のジョブの複製を読む `tests/test_stackchan_launchd.py` と、形は同じで
対象は違う。** ⛔ **同じ形を2つ持つのは、2つのジョブが別の戸口だからである**——
label も、モジュール名も、ログのパスも違う。**片方の緑が、もう片方を言わない。**
"""
from __future__ import annotations

import pathlib
import plistlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
COPY = (
    ROOT / "projects" / "stackchan_next" / "launchd"
    / "embodied-kinetic-loom.stackchan-next.plist"
)
FIRST = (
    ROOT / "projects" / "stackchan" / "launchd"
    / "embodied-kinetic-loom.stackchan.plist"
)


def data() -> dict:
    with COPY.open("rb") as fh:
        return plistlib.load(fh)


def arguments() -> list[str]:
    return data()["ProgramArguments"]


def test_the_copy_parses_and_names_its_own_label():
    """⛔ **label が最初のジョブと同じなら、2つ目は起動しない**（同名は1つである）。"""
    with FIRST.open("rb") as fh:
        first = plistlib.load(fh)

    assert data()["Label"] == "embodied-kinetic-loom.stackchan-next"
    assert data()["Label"] != first["Label"]
    assert data()["RunAtLoad"] is True


def test_the_job_runs_the_second_modules_daemon():
    """⚠️ **1行の違いが、別の部屋である。**"""
    args = arguments()
    assert "projects.stackchan_next.daemon" in args
    assert "projects.stackchan.daemon" not in args


def test_the_two_jobs_do_not_write_one_log():
    """⛔ **1つのログに2つのデーモンが書けば、一日のどの数も曖昧になる。**"""
    with FIRST.open("rb") as fh:
        first = plistlib.load(fh)

    assert data()["StandardOutPath"] != first["StandardOutPath"]
    assert data()["StandardOutPath"] == "/tmp/ekl-stackchan-next.log"


def test_the_dial_is_written_out_rather_than_left_to_its_default():
    """⚠️ **空欄は中立ではない。** 既定で走っていても、この行は書かれる——

    **一日がうるさかったときに、読み手が最初に探す行だからである。**
    """
    args = arguments()
    assert "--presence" in args
    assert args[args.index("--presence") + 1] == "normal"


def test_the_hour_is_not_written_into_the_job():
    """⛔ **時刻は `quiet.py` に在る。** ジョブが時を名指せば、規則は2箇所になる。"""
    for token in arguments():
        assert "QUIET" not in token
        assert token not in ("21", "05", "5", "quiet")


def test_the_port_is_named_once():
    """⚠️ **機体2のコンソールは、ここで1度だけ名指される。**"""
    assert arguments().count("--port") == 1
    assert arguments()[arguments().index("--port") + 1] == "/dev/cu.usbmodem101"
