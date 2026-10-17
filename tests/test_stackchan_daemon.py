# -*- coding: utf-8 -*-
"""**デーモンの中核と縁。**

⚠️ **2つに分かれている。** `room.py` は時計もソケットも読まないので、
**台本の時刻を渡すだけで検査できる**。`__main__.py` は本物のソケットを開くので、
**プロセスを1つ起こして、行を送り、合図で止める。**

⛔ **このファイルが確かめないこと:** launchd、ログインとログアウト、
機体への送信。**デーモンはまだ何も送らない**（`sent` は `False`）。
"""
from __future__ import annotations

import json
import pathlib
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

import pytest

from projects.stackchan.behaviors import (
    ACTED,
    DISTANT,
    EXPRESSION_SECONDS,
    IDLE_SECONDS,
    SETTLED,
    SLEPT,
)
from projects.stackchan.daemon.room import (
    MAX_LINE,
    REQUEST_KEYS,
    REFUSAL_CODES,
    BadRequest,
    Room,
    parse_request,
    refusal,
    row,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
READY_SECONDS = 10.0


# ---------------------------------------------------------------------------
# 中核。⛔ ソケットも時計も無い。
# ---------------------------------------------------------------------------


def test_a_request_is_exactly_a_session_and_an_event():
    assert parse_request('{"session": "left", "event": "SessionStart"}') == (
        "left",
        "SessionStart",
    )
    assert REQUEST_KEYS == frozenset({"session", "event"})


@pytest.mark.parametrize(
    "line, code",
    [
        ("not json", "not-json"),
        ("[]", "not-an-object"),
        ('{"session": "left", "event": "Stop", "prompt": "secret"}', "unknown-key"),
        ('{"session": "left"}', "missing-key"),
        ('{"session": "", "event": "Stop"}', "bad-value"),
        ('{"session": "left", "event": 3}', "bad-value"),
        ('{"session": "left", "event": "NotAnEvent"}', "unknown-event"),
    ],
)
def test_a_malformed_line_is_refused_with_a_code(line, code):
    with pytest.raises(BadRequest) as caught:
        parse_request(line)
    assert caught.value.code == code


def test_every_refusal_code_is_in_the_closed_set():
    assert set(REFUSAL_CODES) == {
        "not-json",
        "not-an-object",
        "unknown-key",
        "missing-key",
        "bad-value",
        "unknown-event",
        "too-long",
    }


def test_the_prompt_cannot_ride_along():
    """⛔ **無視ではなく拒否である。** それが構造によるプライバシーである。"""
    with pytest.raises(BadRequest) as caught:
        parse_request('{"session": "left", "event": "Stop", "prompt": "secret"}')
    assert caught.value.code == "unknown-key"


def test_a_greeting_stamps_a_face_a_light_and_a_gesture():
    room = Room()
    decision = room.offer("main", "SessionStart", 0.0)

    assert decision.phase.value == "greeting"
    assert decision.face is not None and decision.face.value == "greeting"
    assert decision.light.value == "warm"
    assert (decision.gesture, decision.body) == ("perk", "gesture")
    assert decision.reason == ACTED
    assert decision.sent is False


def test_the_next_wake_is_the_expression_and_then_the_idle_clock():
    """⚠️ **期限は数として公開され、刻みは固定されていない。**"""
    room = Room()
    room.offer("main", "SessionStart", 0.0)
    assert room.deadline == EXPRESSION_SECONDS

    assert room.tick(EXPRESSION_SECONDS - 0.001) is None
    settled = room.tick(EXPRESSION_SECONDS)
    assert settled is not None and settled.reason == SETTLED
    assert room.deadline == IDLE_SECONDS

    slept = room.tick(IDLE_SECONDS)
    assert slept is not None and slept.reason == SLEPT
    assert room.deadline is None


def test_a_window_that_is_not_watched_changes_nothing():
    room = Room()
    room.offer("left", "SessionStart", 0.0)
    distant = room.offer("right", "Stop", 2.0)

    assert distant.reason == DISTANT
    assert distant.phase.value == "greeting"
    assert distant.gesture is None
    assert room.held == "left"


def test_the_gaze_returns_when_the_holder_is_quiet():
    room = Room()
    room.offer("left", "UserPromptSubmit", 0.0)
    assert room.held == "left"

    assert room.tick(IDLE_SECONDS) is not None  # 部屋も眠る
    assert room.held is None


def test_the_row_is_the_same_row_the_cli_prints():
    room = Room()
    decision = room.offer("main", "SessionStart", 0.0)
    payload = row(decision, 0.0, "main")

    assert payload["ok"] is True
    assert payload["session"] == "main"
    assert payload["event"] == "SessionStart"
    assert payload["sent"] is False
    assert json.loads(json.dumps(payload)) == payload


def test_a_refusal_is_not_a_decision():
    assert refusal("unknown-event") == {"ok": False, "error": "unknown-event"}


# ---------------------------------------------------------------------------
# 縁。⚠️ 本物のソケットを開き、プロセスを1つ起こす。
# ---------------------------------------------------------------------------


@pytest.fixture
def sock():
    """**短いパスに置く。** ⛔ **`tmp_path` では長すぎる**——
    macOS の `sun_path` は104バイトであり、pytest の一時ディレクトリはそこへ届く。
    ⚠️ **この制約は、設計が `/tmp` を選んだ理由そのものである。**
    """
    directory = tempfile.mkdtemp(prefix="ekl-daemon-", dir="/tmp")
    try:
        yield pathlib.Path(directory) / "room.sock"
    finally:
        shutil.rmtree(directory, ignore_errors=True)


class Daemon:
    """**1つのデーモンを、試験のあいだだけ起こす。**"""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "projects.stackchan.daemon",
             "--socket", str(path)],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._stopped = False
        self.code: int | None = None
        self.out = ""
        self.err = ""

    def __enter__(self) -> "Daemon":
        self._wait_until_ready()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def _wait_until_ready(self) -> None:
        limit = time.monotonic() + READY_SECONDS
        while time.monotonic() < limit:
            if self.proc.poll() is not None:
                out, err = self.proc.communicate()
                raise AssertionError(f"the daemon exited early: {out}{err}")
            if self.path.exists():
                try:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                        probe.settimeout(0.1)
                        probe.connect(str(self.path))
                    return
                except OSError:
                    pass
            time.sleep(0.02)
        self.stop()
        raise AssertionError(f"the daemon did not bind {self.path}")

    def send(self, payload: dict | str) -> dict:
        line = payload if isinstance(payload, str) else json.dumps(payload)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(READY_SECONDS)
            client.connect(str(self.path))
            client.sendall(line.encode("utf-8") + b"\n")
            chunks = b""
            while b"\n" not in chunks:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks += chunk
        return json.loads(chunks.partition(b"\n")[0])

    def rows(self) -> list[dict]:
        """**デーモンが出した行。** ⚠️ 起動の1行は判定ではない。"""
        rows = []
        for line in self.out.splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if "phase" in payload:
                rows.append(payload)
        return rows

    def stop(self) -> tuple[int, str, str]:
        if self._stopped:
            return self.code or 0, self.out, self.err
        self._stopped = True
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
        try:
            self.out, self.err = self.proc.communicate(timeout=READY_SECONDS)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.out, self.err = self.proc.communicate()
            raise AssertionError(f"the daemon did not stop: {self.err}")
        self.code = self.proc.returncode
        return self.code, self.out, self.err


def test_the_socket_answers_and_logs_the_same_row(sock):
    path = sock
    with Daemon(path) as daemon:
        answer = daemon.send({"session": "left", "event": "SessionStart"})
        assert answer["ok"] is True
        assert answer["phase"] == "greeting"
        assert answer["gesture"] == "perk"
        assert answer["sent"] is False

    # ⚠️ **ログは停止のときに回収される。** 行は返事と同じである。
    assert daemon.rows()[-1] == answer


def test_the_socket_is_removed_and_the_exit_is_clean(sock):
    path = sock
    with Daemon(path) as daemon:
        assert path.exists()

    assert daemon.code == 0
    assert not path.exists()


def test_a_stale_socket_is_unlinked_and_replaced(sock):
    path = sock
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(str(path))
    stale.close()
    assert path.exists()

    with Daemon(path) as daemon:
        answer = daemon.send({"session": "main", "event": "Stop"})
        assert answer["ok"] is True


def test_a_second_instance_leaves_the_first_alone(sock):
    path = sock
    with Daemon(path) as daemon:
        second = subprocess.run(
            [sys.executable, "-m", "projects.stackchan.daemon",
             "--socket", str(path)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=READY_SECONDS,
        )
        assert second.returncode == 3
        assert "another daemon is alive" in second.stderr

        answer = daemon.send({"session": "main", "event": "Stop"})
        assert answer["ok"] is True


def test_each_refusal_names_its_fault(sock):
    path = sock
    with Daemon(path) as daemon:
        assert daemon.send("not json")["error"] == "not-json"
        assert daemon.send({"event": "Stop"})["error"] == "missing-key"
        assert daemon.send({"session": "main", "event": "Nope"})["error"] == "unknown-event"


def test_the_prompt_never_reaches_the_log(sock):
    path = sock
    secret = "a prompt that must not be logged"
    with Daemon(path) as daemon:
        answer = daemon.send(
            {"session": "left", "event": "Stop", "prompt": secret}
        )
    assert answer == {"ok": False, "error": "unknown-key"}
    assert secret not in daemon.out


def test_a_silent_client_does_not_block_the_room(sock):
    path = sock
    with Daemon(path) as daemon:
        silent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        silent.connect(str(path))
        time.sleep(0.3)  # ⚠️ CLIENT_TIMEOUT より長く、口を開けたままにする
        answer = daemon.send({"session": "main", "event": "SessionStart"})
        silent.close()
        assert answer["ok"] is True
        assert answer["phase"] == "greeting"


def test_a_line_over_the_bound_is_refused(sock):
    path = sock
    with Daemon(path) as daemon:
        answer = daemon.send("x" * (MAX_LINE + 1))
        assert answer == {"ok": False, "error": "too-long"}
