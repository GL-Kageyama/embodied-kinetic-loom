# -*- coding: utf-8 -*-
"""**フックの側のクライアント。**

⚠️ **2つに分かれている。** `client.line_from` は入力と出力の関数であり、
プロセスを起こさずに検査できる。`hook/__main__.py` は本物の標準入力と
ソケットを読むので、**プロセスを1つ起こして、行を送らせる。**

⛔ **このファイルが確かめないこと:** `settings.json` への登録、launchd、
機体への送信。**クライアントはまだ何も設置されておらず、`sent` は `False` である。**
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time

import pytest

from projects.stackchan.client import INPUT_LIMIT, SOURCE_FIELDS, line_from
from projects.stackchan.daemon.room import MAX_LINE, parse_request, socket_path
from test_stackchan_daemon import REPO_ROOT, Daemon


# ---------------------------------------------------------------------------
# 中核。⛔ プロセスもソケットも無い。
# ---------------------------------------------------------------------------


def test_the_line_carries_exactly_two_fields():
    payload = {
        "session_id": "left",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "a secret",
        "cwd": "/somewhere",
        "tool_input": {"command": "cat secret"},
    }
    line = line_from(payload)

    assert json.loads(line) == {"session": "left", "event": "UserPromptSubmit"}
    assert "a secret" not in line
    assert SOURCE_FIELDS == ("session_id", "hook_event_name")


@pytest.mark.parametrize(
    "payload",
    [
        [],
        "SessionStart",
        {},
        {"session_id": "left"},
        {"hook_event_name": "Stop"},
        {"session_id": "", "hook_event_name": "Stop"},
        {"session_id": "left", "hook_event_name": ""},
        {"session_id": 3, "hook_event_name": "Stop"},
        {"session_id": "left", "hook_event_name": 4},
        {"session_id": None, "hook_event_name": "Stop"},
    ],
)
def test_a_payload_without_the_two_fields_is_dropped(payload):
    assert line_from(payload) is None


def test_an_unknown_event_is_dropped_here_too():
    """⚠️ **デーモンも同じ規則を持つ。** 二重なのは、片方が緩んでも鳴るためである。"""
    assert line_from({"session_id": "left", "hook_event_name": "NotAnEvent"}) is None


def test_the_line_is_the_daemons_contract():
    line = line_from({"session_id": "left", "hook_event_name": "Stop"})
    assert parse_request(line.strip()) == ("left", "Stop")
    assert len(line) < MAX_LINE


def test_the_socket_path_is_one_spelling():
    from projects.stackchan.daemon import __main__ as daemon_main
    from projects.stackchan.hook import __main__ as hook_main

    assert socket_path(501) == "/tmp/ekl-stackchan-501.sock"
    assert daemon_main.default_socket() == socket_path(os.getuid())
    assert hook_main.default_socket() == socket_path(os.getuid())


# ---------------------------------------------------------------------------
# 縁。⚠️ 本物の標準入力とソケット。
# ---------------------------------------------------------------------------


def run_client(path, text: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "projects.stackchan.hook", "--socket", str(path)],
        cwd=REPO_ROOT,
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_a_hook_payload_reaches_the_room(sock):
    payload = {
        "session_id": "left",
        "hook_event_name": "SessionStart",
        "prompt": "must never be logged",
    }
    with Daemon(sock) as daemon:
        result = run_client(sock, json.dumps(payload))

    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""

    rows = daemon.rows()
    assert rows[-1]["phase"] == "greeting"
    assert rows[-1]["event"] == "SessionStart"
    assert rows[-1]["sent"] is False
    assert "must never be logged" not in daemon.out


def test_the_room_keeps_the_phase_between_processes(sock):
    """⛔ **これが、この橋の存在理由である。**

    `Companion` は事象のあいだ状態を持つが、フックは1事象につき1プロセスである。
    ⇒ **2つの別プロセスが、同じ段階の続きを見る**——1つ目が `greeting` を開き、
    2つ目が `closing` へ進める。**プロセスは状態を1つも持ち越していない。**
    """
    with Daemon(sock) as daemon:
        first = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "SessionStart"}
        ))
        second = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "Stop"}
        ))

    assert first.returncode == 0 and second.returncode == 0
    assert first.stdout == "" and second.stdout == ""

    rows = daemon.rows()
    assert [r["event"] for r in rows] == ["SessionStart", "Stop"]
    assert rows[0]["phase"] == "greeting"
    assert rows[1]["phase"] == "closing"
    assert all(r["sent"] is False for r in rows)


def test_two_windows_through_two_clients_and_one_gaze(sock):
    """⚠️ **窓が2つでも、クライアントは同じものである。** 違うのは名前だけであり、
    部屋は1つのまま注目を1つに保つ。
    """
    with Daemon(sock) as daemon:
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "SessionStart"}
        ))
        run_client(sock, json.dumps(
            {"session_id": "right", "hook_event_name": "UserPromptSubmit"}
        ))
        # ⛔ 背後の窓の `Stop` は注目を奪わない。**部屋は起きたままで、何も変えない。**
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "Stop"}
        ))

    rows = daemon.rows()
    assert [r["session"] for r in rows] == ["left", "right", "left"]
    assert rows[1]["phase"] == "working"
    assert rows[2]["reason"] == "distant"
    assert rows[2]["phase"] == "working"
    assert all(r["sent"] is False for r in rows)


def test_no_daemon_is_silent_and_clean(sock):
    """⚠️ **デーモンが居ないことは、フックの失敗ではない。**"""
    assert not sock.exists()
    started = time.monotonic()
    result = run_client(sock, json.dumps(
        {"session_id": "left", "hook_event_name": "Stop"}
    ))
    elapsed = time.monotonic() - started

    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""
    assert elapsed < 5.0


def test_malformed_input_is_silent(sock):
    with Daemon(sock) as daemon:
        result = run_client(sock, "not json")
        assert result.returncode == 0
        assert result.stdout == ""

    assert daemon.rows() == []


def test_an_overlong_input_is_dropped(sock):
    with Daemon(sock) as daemon:
        result = run_client(sock, '{"session_id": "' + "x" * INPUT_LIMIT + '"}')
        assert result.returncode == 0

    assert daemon.rows() == []


def test_the_client_does_not_wait_for_a_reply(sock):
    """⛔ **読めば、ターンがデーモンの速さを待つことになる。**

    ⚠️ **受け取らないまま待つ相手を立てる。** クライアントは送って閉じるだけなので、
    返事を待たずに戻る。
    """
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(sock))
    listener.listen(1)
    try:
        started = time.monotonic()
        result = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "SessionStart"}
        ))
        elapsed = time.monotonic() - started
    finally:
        listener.close()

    assert result.returncode == 0
    assert elapsed < 1.0
