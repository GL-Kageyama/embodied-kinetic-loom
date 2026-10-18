# -*- coding: utf-8 -*-
"""**デーモンの中核と縁。**

⚠️ **2つに分かれている。** `room.py` は時計もソケットも読まないので、
**台本の時刻を渡すだけで検査できる**。`__main__.py` は本物のソケットを開くので、
**プロセスを1つ起こして、行を送り、合図で止める。**

⚠️ **このファイルが確かめないこと:** launchd、ログインとログアウト、**本物の端末**。
✅ **2026-10-18 から、枠は端末へ書かれる**（`--port`）。だが試験が開くのは
**ただのファイル**であり、**LEDが光ることは、このファイルの外である。**
⛔ **`--port` を渡さなければ、`sent` は今まで通り `False`**——それが既定である。
"""
from __future__ import annotations

import json
import pathlib
import signal
import socket
import subprocess
import sys
import time

import pytest

from engine.backend import protocol_stackchan as wire
from engine.backend.protocol_stackchan_pose import decode
from projects.stackchan.behaviors import (
    ACTED,
    DISTANT,
    EXPRESSION_SECONDS,
    IDLE_SECONDS,
    MIN_BODY_INTERVAL,
    SETTLED,
    SLEPT,
)
from projects.stackchan.daemon import __main__ as edge
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
    assert (decision.gesture, decision.body) == ("look_up", "gesture")
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


class Daemon:
    """**1つのデーモンを、試験のあいだだけ起こす。**"""

    def __init__(self, path: pathlib.Path, port: pathlib.Path | None = None) -> None:
        self.path = path
        command = [sys.executable, "-m", "projects.stackchan.daemon",
                   "--socket", str(path)]
        if port is not None:
            command += ["--port", str(port)]
        self.proc = subprocess.Popen(
            command,
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

    def frames(self) -> list[dict]:
        """**枠の行。** ⚠️ **`sent` が言うのは、端末へ書けたかどうかである。**"""
        frames = []
        for line in self.out.splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if "frame" in payload:
                frames.append(payload)
        return frames

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
        assert answer["gesture"] == "look_up"
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


# ---------------------------------------------------------------------------
# 外向きの枠。⚠️ 書くが、送らない。
# ---------------------------------------------------------------------------


def test_the_daemon_logs_the_frame_it_would_send(sock):
    """✅ **挨拶は、判定の行のほかに、枠の行を1つ残す。**

    ⛔ **端末を渡していないので、渡っていない。** `sent` は `False` である。
    ✅ **渡すのは `test_the_configured_port_receives_the_logged_line` の仕事である。**
    """
    path = sock
    with Daemon(path) as daemon:
        answer = daemon.send({"session": "main", "event": "SessionStart"})
        assert answer["sent"] is False

    frames = daemon.frames()
    assert len(frames) == 1
    assert frames[0]["sent"] is False
    assert frames[0]["session"] == "main"

    command = wire.decode(frames[0]["frame"].encode("ascii"))
    assert command == wire.Command(face="greeting", light="warm", gesture="look_up")


def test_an_unchanged_event_logs_no_second_frame(sock):
    """⚠️ **同じ状態の事象は、枠を増やさない。** ⛔ これは流れではない。"""
    path = sock
    with Daemon(path) as daemon:
        daemon.send({"session": "main", "event": "PreToolUse"})
        daemon.send({"session": "main", "event": "PostToolUse"})

    frames = daemon.frames()
    assert len(frames) == 1
    command = wire.decode(frames[0]["frame"].encode("ascii"))
    assert command.light == "breathe"
    assert command.face is None


# ---------------------------------------------------------------------------
# 伝送路。⚠️ 端末の代わりに、ただのファイルを開く。
# ---------------------------------------------------------------------------


def test_the_configured_port_receives_the_logged_line(sock):
    """✅ **`--port` を渡すと、枠はその端末へ、ログと同じ綴りで書かれる。**

    ⚠️ **端末の代わりは、ただのファイルである。** ⛔ **光ったことは、ここでは分からない。**
    """
    port = sock.parent / "console"
    port.touch()
    with Daemon(sock, port=port) as daemon:
        answer = daemon.send({"session": "main", "event": "SessionStart"})
        assert answer["ok"] is True

    frames = daemon.frames()
    assert len(frames) == 1
    assert frames[0]["sent"] is True
    assert port.read_text(encoding="ascii") == frames[0]["frame"] + "\n"


def test_a_missing_port_is_not_a_refusal(sock):
    """⛔ **端末が無いことは、事象の拒否ではない。** 部屋は答える。"""
    port = sock.parent / "absent"
    with Daemon(sock, port=port) as daemon:
        first = daemon.send({"session": "main", "event": "SessionStart"})
        second = daemon.send({"session": "main", "event": "PreToolUse"})
        assert first["ok"] is True
        assert second["ok"] is True

    frames = daemon.frames()
    assert frames, "枠が1つも出ていない——この検査は何も見ていない"
    assert all(f["sent"] is False for f in frames)
    assert not port.exists()


def test_without_a_port_nothing_is_written(sock):
    """⚠️ **既定では、端末を開かない。** `sent` は今まで通り `False`。"""
    with Daemon(sock) as daemon:
        daemon.send({"session": "main", "event": "SessionStart"})

    frames = daemon.frames()
    assert [f["sent"] for f in frames] == [False]
    assert not (sock.parent / "console").exists()


def test_a_line_that_cannot_be_written_is_not_sent(tmp_path):
    """⛔ **書けなかった行を、`sent` が `True` と言ってはならない。**

    ⚠️ **開けない場所**（無いパス、ディレクトリ）と、**開ける場所**（ファイル）を並べる。
    """
    assert edge.send_line(str(tmp_path / "absent"), "x\n") is False
    assert edge.send_line(str(tmp_path), "x\n") is False

    target = tmp_path / "console"
    target.write_text("", encoding="ascii")
    assert edge.send_line(str(target), "x\n") is True
    assert target.read_text(encoding="ascii") == "x\n"


# ---------------------------------------------------------------------------
# 継ぎ目。2026-10-19 —— 1つの事象が、枠と姿勢の行に分かれる。
# ---------------------------------------------------------------------------


def test_the_second_gesture_is_streamed_and_the_frame_carries_none(sock):
    """✅ **1つの事象が、顔と光を枠で、首を姿勢の行で動かす。**

    ⛔ **枠が身振りも運べば、基板は2度動く**——`PlayGesture` はメインループを数秒塞ぎ、
    その間の姿勢の行は遅れて適用される。⇒ **流すとき、枠の `gesture` は `None` である。**
    ⚠️ **最初の1回だけは基板が演じる**（このホストは首の位置を読まない）——
    だからこの検査は、**2つ目の事象**で見る。
    """
    port = sock.parent / "console"
    port.touch()
    with Daemon(sock, port=port) as daemon:
        first = daemon.send({"session": "main", "event": "SessionStart"})
        # ⚠️ **体の下限を越える。** 近すぎる身振りは、並べずに捨てられる。
        time.sleep(MIN_BODY_INTERVAL + 0.05)
        second = daemon.send({"session": "main", "event": "PermissionRequest"})
        assert first["gesture"] == "look_up"
        assert second["gesture"] == "look_side"
        time.sleep(0.3)

    lines = port.read_text(encoding="ascii").splitlines()
    frames = [json.loads(line) for line in lines if line.startswith("{")]
    poses = [line for line in lines if line.startswith("pose ")]

    assert len(frames) == 2
    assert frames[0]["gesture"] == "look_up"     # 最初の1回は、基板が演じる
    assert frames[1]["gesture"] is None          # 2回目からは、首が姿勢の行で動く
    assert len(poses) >= 5, "姿勢の行が流れていない——この検査は何も見ていない"
    for line in poses:
        decode(line.encode("ascii") + b"\n")

    rows = [json.loads(line) for line in daemon.out.splitlines() if line.strip()]
    necks = [row for row in rows if "neck" in row]
    assert necks, "首の行が1つも出ていない"
    assert necks[0]["neck"] == "look_side"
    assert necks[0]["poses"] >= 5
    assert necks[0]["from"] == [80, 500]         # look_up の姿勢から
    assert necks[0]["to"] == [350, 500]          # look_side の姿勢へ


def test_the_first_gesture_is_not_streamed(sock):
    """⚠️ **最初の1回は、基板に任せる。** このホストは首の位置を読まない。

    ⛔ **知らない位置を始点にすれば、1行目は「その位置への移動」になる。**
    """
    port = sock.parent / "console"
    port.touch()
    with Daemon(sock, port=port) as daemon:
        daemon.send({"session": "main", "event": "SessionStart"})

    lines = port.read_text(encoding="ascii").splitlines()
    assert [line for line in lines if line.startswith("pose ")] == []
    assert json.loads(lines[0])["gesture"] == "look_up"

    rows = [json.loads(line) for line in daemon.out.splitlines() if line.strip()]
    assert [row for row in rows if "neck" in row] == []


# ---------------------------------------------------------------------------
# 端末。⛔ **2026-10-19 に、行ごとの開閉がデーモンを止めた。** その縁を固定する。
# ---------------------------------------------------------------------------


def _park(neck: "edge.Neck", at: float = 0.0) -> None:
    """**最初の身振りは基板に演じさせる。** その後、首は表の終わりを起点に持つ。"""
    room = Room()
    assert neck.take(room.offer("main", "SessionStart", at), at) is False


def test_one_stream_opens_the_port_once(tmp_path, monkeypatch, capsys):
    """✅ **開くのは、身振りに1回。** ⛔ **行ごとに開くと、基板が読まなくなった瞬間に止まる。**

    ⚠️ **これは数える検査である**: `os.open` を数え、列の数と比べる。
    **測ったこと**（2026-10-19）: 20 ms ごとの開閉は5行目あたりで `open` が返らず、
    デーモンごと止まった。開くのは1回でなければならない。
    """
    port = tmp_path / "console"
    port.touch()
    neck = edge.Neck(str(port))
    _park(neck)

    at = 1.2
    decision = Room().offer("main", "PermissionRequest", at)

    opens: list[str] = []
    real_open = edge.os.open

    def counting_open(path, flags, *args, **kwargs):
        opens.append(str(path))
        return real_open(path, flags, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(edge.os, "open", counting_open)
        assert neck.take(decision, at) is True

    # ⚠️ **流れを終わらせる。** 呼ぶ側（select ループ）と同じく、期限ごとに起こす。
    t = at
    while neck.deadline is not None or neck._fd is not None:
        neck.pump(t)
        t += edge.gestures.DEFAULT_PERIOD
        assert t < at + 30.0, "流れが終わらない"

    assert opens == [str(port)], f"開いた回数が違う: {opens}"
    assert neck._fd is None, "身振りが終わっても、ポートを持ち続けている"

    written = [line for line in port.read_text(encoding="ascii").splitlines()
               if line.startswith("pose ")]
    assert len(written) >= 5
    for line in written:
        decode(line.encode("ascii") + b"\n")


def test_a_port_that_takes_nothing_stops_the_stream(tmp_path, capsys):
    """⛔ **読まない端末を、行の列で埋めない。** 待ちには上限があり、越えたら流れは止まる。

    ⚠️ **パイプを満たして、書けない fd を作る。** 本物の基板が止まったときの形であり、
    `PORT_WAIT` の後に `sent: false` の行が1つ出て、ポートが閉じる。
    """
    import os

    port = tmp_path / "console"
    port.touch()
    neck = edge.Neck(str(port))
    _park(neck)

    at = 1.2
    assert neck.take(Room().offer("main", "PermissionRequest", at), at) is True

    read_end, write_end = os.pipe()
    os.close(neck._fd)
    os.set_blocking(write_end, False)
    try:
        while True:
            os.write(write_end, b"x" * 4096)
    except BlockingIOError:
        pass
    neck._fd = write_end

    started = time.monotonic()
    neck.pump(at + 0.02)
    elapsed = time.monotonic() - started

    assert elapsed < edge.PORT_WAIT + 1.0, "待ちに上限が無い"
    assert neck._fd is None, "書けなかった後もポートを持っている"

    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert any(row.get("sent") is False for row in rows), "止まったことが残っていない"
    os.close(read_end)


def test_a_port_that_cannot_be_opened_leaves_the_gesture_to_the_board(tmp_path):
    """⚠️ **開けない端末に、行だけを数えて「送った」と言わない。**

    開けなければ流さない——**枠が身振りを運び、基板が演じる。** `take` は `False` を返す。
    """
    neck = edge.Neck(str(tmp_path / "missing"))
    room = Room()
    assert neck.take(room.offer("main", "SessionStart", 0.0), 0.0) is False
    assert neck.take(room.offer("main", "PermissionRequest", 1.2), 1.2) is False
    assert neck._fd is None
