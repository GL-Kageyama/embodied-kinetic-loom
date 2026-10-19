# -*- coding: utf-8 -*-
"""リポジトリ直下の `conftest`。

⚠️ **これがやっているのは3つである。**

1. **`tests/` からリポジトリの根を `import` できるようにする。**
   pytest は `rootdir` を `sys.path` に入れないので、`tests/` の外に置いたモジュール
   （`tools/` など）は、これが無いと `import` できない。
2. **`FakeClock` を1つだけ置く。** ⚠️ **`test_cycle.py` と `test_backend.py` が
   同じ時計を要る**——**2つ書けば、片方だけが直る。**
3. **`sock` フィクスチャを1つだけ置く。** ⚠️ **`test_stackchan_daemon.py`・
   `test_stackchan_hook_client.py`・`test_stackchan_next_daemon.py` が同じ短いパスを要る**
   ——**同じ理由である。**

⚠️ **`FakeClock` は何も検査しない。** **検査は、これを使う側に在る。**
⚠️ **このファイルは `time` を import しない**（`engine/` の純粋性とは別の話である——
**ここは `engine/` の外である**）。
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class FakeClock:
    """⚠️ **眠った量を記録する時計。** それだけのために在る。

    - `overshoot` は **`sleep` が余計に眠ってしまうこと**である。**実機では常に起きる。**
    - `quantum` は**スピンの刻み**である。**これが無いと、偽の時計の上でスピンが終わらない。**
    """

    def __init__(self, quantum: float = 0.0005, overshoot: float = 0.0) -> None:
        self.t = 0.0
        self.quantum = quantum
        self.overshoot = overshoot
        self.sleeps: list[float] = []
        self.spins = 0

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        assert seconds >= 0, f"⛔ **負の sleep を要求した: {seconds}**"
        if seconds == 0.0:
            self.spins += 1
            self.t += self.quantum
            return
        self.sleeps.append(seconds)
        self.t += seconds + self.overshoot

    def advance(self, seconds: float) -> None:
        """⚠️ **ループの外から時間を進める**（「`body` が長くかかった」を作るため）。"""
        self.t += seconds


@pytest.fixture
def sock():
    """**デーモンのソケットを、短いパスに置く。**

    ⛔ **`tmp_path` では長すぎる**——macOS の `sun_path` は104バイトであり、
    pytest の一時ディレクトリはそこへ届く。**この制約は、設計が `/tmp` を選んだ
    理由そのものである**（`projects/stackchan/daemon/room.py` の `socket_path`）。
    """
    directory = tempfile.mkdtemp(prefix="ekl-daemon-", dir="/tmp")
    try:
        yield Path(directory) / "room.sock"
    finally:
        shutil.rmtree(directory, ignore_errors=True)

