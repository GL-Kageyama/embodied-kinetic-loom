# -*- coding: utf-8 -*-
"""**新しい層のデーモン。** ⚠️ **既存のデーモンと並走する。**

⚠️ **`tests/test_stackchan_daemon.py` と同じ2つの形である。** `room.py` は
時計もソケットも読まないので台本の時刻だけで検査できる。`__main__.py` は
本物のソケットを開くので、**プロセスを起こし、行を送り、合図で止める。**

⛔ **このファイルが確かめないこと:** 本物の端末、launchd、**光ったこと**、
そして **`work` が人に読めるか**——それは著者の目である。
✅ **確かめるのは3つである**: **別のソケットで並走すること**、**3語目の要求が
通ること**、**その語が光になること**。
⚠️ **ソケットのパスは既存と同じ理由で短くある**（`conftest` の `sock`）。
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
from projects.stackchan.daemon.room import MAX_LINE, BadRequest
from projects.stackchan_next import work as work_words
from projects.stackchan_next.daemon import __main__ as edge
from projects.stackchan_next.daemon.room import (
    OPTIONAL_KEYS,
    REQUEST_KEYS,
    REQUIRED_KEYS,
    NextRoom,
    parse_request,
    socket_path,
)
from projects.stackchan_next.presence import PRESENCES, WORK_DWELL

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
READY_SECONDS = 10.0

#: ⚠️ **新しい層のモジュール名である。** ソケットの綴りとは別である。
NEW_MODULE = "projects.stackchan_next.daemon"
OLD_MODULE = "projects.stackchan.daemon"


# ---------------------------------------------------------------------------
# 中核。⛔ ソケットも時計も無い。
# ---------------------------------------------------------------------------


def test_a_request_is_a_session_an_event_and_maybe_a_work_word():
    assert parse_request('{"session": "left", "event": "PreToolUse"}') == (
        "left",
        "PreToolUse",
        None,
    )
    assert parse_request(
        '{"session": "left", "event": "PreToolUse", "work": "write"}'
    ) == ("left", "PreToolUse", "write")
    # ⚠️ **鍵は3つまでである。** 増やすことは、フックの契約を増やすことである。
    assert REQUIRED_KEYS == frozenset({"session", "event"})
    assert OPTIONAL_KEYS == frozenset({"work"})
    assert REQUEST_KEYS == frozenset({"session", "event", "work"})


@pytest.mark.parametrize("word", work_words.WORK_WORDS)
def test_every_work_word_is_accepted_exactly_as_it_is_spelled(word):
    assert parse_request(
        f'{{"session": "s", "event": "PreToolUse", "work": "{word}"}}'
    ) == ("s", "PreToolUse", word)


@pytest.mark.parametrize("word", ["fly", "", "Write", 3, True, ["write"]])
def test_a_word_outside_the_six_is_refused_as_a_bad_value(word):
    """⛔ **知らない語を `other` に落とさない。**

    落とせば、クライアントの綴りの誤りが「その他の作業」として静かに光り、
    **誤りは一度も見えない。** ⛔ **`True` も数である**——`bool` は `int` の子である。
    """
    line = json.dumps({"session": "s", "event": "PreToolUse", "work": word})
    with pytest.raises(BadRequest) as caught:
        parse_request(line)
    assert caught.value.code == "bad-value"


def test_a_work_word_is_not_a_new_refusal_code():
    """⚠️ **符号は向こうの閉じた集合のままである。** 新しい符号を発明しない。"""
    from projects.stackchan.daemon.room import REFUSAL_CODES

    assert "bad-value" in REFUSAL_CODES
    assert len(REFUSAL_CODES) == 7


def test_the_two_daemons_listen_in_different_places():
    """⚠️ **並走できるのは、綴りが1つの prefix で違うからである。**"""
    from projects.stackchan.daemon.room import socket_path as old_path

    assert socket_path(501) != old_path(501)
    assert socket_path(501) == "/tmp/ekl-stackchan-next-501.sock"


# ---------------------------------------------------------------------------
# 光。⚠️ 純粋関数として、時計を渡して見る。
# ---------------------------------------------------------------------------


def test_a_write_event_lights_the_writing_word():
    """⚠️ **`working` は `UserPromptSubmit` から始まる。** 道具の事象は章を開かない。

    ⛔ **「作業の光」は `working` のあいだだけである**——`present` で道具が走ることは
    無い（`behaviors._evidence` が `_turn_started` を見る）。
    """
    room = NextRoom()
    room.offer("main", "UserPromptSubmit", 0.0)
    decision = room.offer("main", "PreToolUse", 1.0, work="write")
    assert decision.phase.value == "working"
    assert decision.light.value == "writing"


def test_a_run_event_lights_busy_and_a_read_event_leaves_dim():
    room = NextRoom()
    room.offer("main", "UserPromptSubmit", 0.0)
    assert room.offer("main", "PreToolUse", 1.0, work="run").light.value == "busy"
    # ⚠️ **滞留は5秒である。** その内側では、語が変わっても光は変わらない。
    assert room.offer("main", "PostToolUse", 2.0, work="read").light.value == "busy"
    assert room.offer("main", "PostToolUse", 6.5, work="read").light.value == "dim"


def test_the_dwell_stops_the_light_from_mirroring_every_tool():
    """⛔ **道具のたびに色が変われば、それは鏡であり、相棒ではない。**

    ⚠️ **章の出入りは滞留を通さない**——`working` へ入った直後の1回はすぐ見える。
    """
    room = NextRoom()
    room.offer("main", "UserPromptSubmit", 0.0)
    assert room.offer("main", "PreToolUse", 0.0, work="write").light.value == "writing"
    assert room.offer("main", "PostToolUse", 1.0, work="run").light.value == "writing"
    assert room.offer("main", "PostToolUse", WORK_DWELL, work="run").light.value == "busy"


def test_an_event_that_does_not_carry_a_word_keeps_the_last_one():
    """⛔ **`SessionStart` に `work` を載せても、語は覚えない。**

    遷移は章であり、作業ではない（`work.WORK_EVENTS`）。**覚えれば、挨拶の光が
    最後の道具の色になる。**
    """
    room = NextRoom()
    greeting = room.offer("main", "SessionStart", 0.0, work="write")
    assert greeting.phase.value == "greeting"
    assert greeting.light.value == "warm"


def test_the_quiet_dial_answers_and_says_dim():
    room = NextRoom(presence="quiet")
    room.offer("main", "UserPromptSubmit", 0.0)
    decision = room.offer("main", "PreToolUse", 1.0, work="write")
    assert decision.phase.value == "working"
    assert decision.light.value == "dim"


def test_the_edge_reads_the_hour_as_a_value():
    """⚠️ **時計を読むのは縁だけであり、読んだ結果は真偽として渡る。**

    ⛔ **静かな時間が閉じるのは音の欄だけである**——顔も光も首は従わない。
    """
    day = NextRoom(sound=True)
    day.offer("main", "SessionEnd", 0.0)
    assert edge.decide(day, "main", "PreToolUse", "write", 100.0, hour=12).sound == "pip"

    night = NextRoom(sound=True)
    night.offer("main", "SessionEnd", 0.0)
    assert edge.decide(night, "main", "PreToolUse", "write", 100.0, hour=22).sound is None


# ---------------------------------------------------------------------------
# 縁。⚠️ 本物のソケットを開き、プロセスを1つ起こす。
# ---------------------------------------------------------------------------


class Daemon:
    """**1つのデーモンを、試験のあいだだけ起こす。** ⚠️ **モジュールは引数である。**"""

    def __init__(self, path: pathlib.Path, port: pathlib.Path | None = None,
                 module: str = NEW_MODULE, extra: tuple[str, ...] = (),
                 meta: bool = True) -> None:
        self.path = path
        # ⚠️ **メタのソケットも、試験の短いパスに置く。** ⛔ **既定の
        #    `/tmp/ekl-stackchan-meta-<uid>.sock` を使わない**——設置済みの
        #    デーモンがそこを握っていれば、この試験は**本物の受口を奪い合う。**
        self.meta = path.parent / "meta.sock"
        command = [sys.executable, "-m", module, "--socket", str(path)]
        if port is not None:
            command += ["--port", str(port)]
        if module == NEW_MODULE and meta:
            command += ["--meta-socket", str(self.meta)]
        command += list(extra)
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

    def send_meta(self, payload: dict | str) -> dict:
        """**メタのソケットへ1行。** ⚠️ **体のソケットとは別の戸口である。**"""
        line = payload if isinstance(payload, str) else json.dumps(payload)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(READY_SECONDS)
            client.connect(str(self.meta))
            client.sendall(line.encode("utf-8") + b"\n")
            chunks = b""
            while b"\n" not in chunks:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks += chunk
        return json.loads(chunks.partition(b"\n")[0])

    def meta_rows(self) -> list[dict]:
        """**監修の行だけ。** ⚠️ 起動行も `meta` を持つので、値で分ける。"""
        return [row for row in self._lines()
                if row.get("meta") in ("candidate", "delivered", "dropped", "error")]

    def _lines(self) -> list[dict]:
        rows = []
        for line in self.out.splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def rows(self) -> list[dict]:
        """**判定の行。** ⚠️ 起動の1行は判定ではない。"""
        return [payload for payload in self._lines() if "phase" in payload]

    def frames(self) -> list[dict]:
        """**枠の行。** ⚠️ **`sent` が言うのは、端末へ書けたかどうかである。**"""
        return [payload for payload in self._lines() if "frame" in payload]

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
    with Daemon(sock) as daemon:
        answer = daemon.send({"session": "left", "event": "SessionStart"})
        assert answer["ok"] is True
        assert answer["phase"] == "greeting"
        assert answer["gesture"] == "look_up"
        assert answer["sent"] is False

    assert daemon.rows()[-1] == answer


def test_the_word_is_stamped_on_the_row_so_a_day_can_be_counted(sock):
    """⚠️ **ログに語が載らなければ、一日の内訳を数えられない。**

    ⛔ **語の無い事象の行には、鍵そのものが無い**——`None` を書けば、
    **「知らされていない」と「その他」が同じ行になる。**
    """
    with Daemon(sock) as daemon:
        stamped = daemon.send({"session": "main", "event": "PreToolUse", "work": "write"})
        plain = daemon.send({"session": "main", "event": "Stop"})

    assert stamped["work"] == "write"
    assert "work" not in plain, plain


def test_the_socket_is_removed_and_the_exit_is_clean(sock):
    """⛔ **ソケットが在るなら、片付けられる準備はできている。**"""
    with Daemon(sock) as daemon:
        assert sock.exists()

    assert daemon.code == 0
    assert not sock.exists()


def test_the_signal_handler_is_installed_before_the_socket_is_bound():
    """⛔ **順序そのものを読む。** 2026-10-19 に一度だけ落ちた検査の隙間である。"""
    source = (REPO_ROOT / f"{NEW_MODULE.replace('.', '/')}/__main__.py").read_text(
        encoding="utf-8")
    # ⚠️ **数えるのは体のソケットの束縛だけである**——0.19.64 にメタの束縛が
    #    1つ増えたので、`listener = bind(` で数えると `meta_listener = bind(` にも当たる
    #    （**数え方の側が、増えた側に化ける**）。⇒ **引数まで書いて名指す。**
    assert source.count("signal.signal(signal.SIGTERM") == 1
    assert source.count("listener = bind(args.socket)") == 1
    assert source.index("signal.signal(signal.SIGTERM") < source.index(
        "listener = bind(args.socket)")


def test_the_edge_copies_none_of_the_machinery():
    """⛔ **伝送路・枠・ログ・判定は、向こうから来る。**

    ⚠️ **写せば、2つの綴りが生まれる**——片方が黙って緩んだ日に、もう片方が鳴らない。
    ✅ **この層が自分で持つのは `handle` と `serve` だけである。** 理由は1つである:
    向こうの `serve` は自分自身の `handle` を名前で呼ぶので、**外から差し込む口が無い。**
    """
    source = (REPO_ROOT / f"{NEW_MODULE.replace('.', '/')}/__main__.py").read_text(
        encoding="utf-8")
    for name in ("send_frame_and_read", "frame_row", "frame_line", "parse_request",
                 "deliver", "emit"):
        assert f"def {name}(" not in source, f"{name} を写している"
    for name in ("handle", "serve"):
        assert f"def {name}(" in source, f"{name} が無い——要求の形が違うので要る"


def test_a_stale_socket_is_unlinked_and_replaced(sock):
    stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    stale.bind(str(sock))
    stale.close()
    assert sock.exists()

    with Daemon(sock) as daemon:
        assert daemon.send({"session": "main", "event": "Stop"})["ok"] is True


def test_a_second_instance_leaves_the_first_alone(sock):
    with Daemon(sock) as daemon:
        second = subprocess.run(
            [sys.executable, "-m", NEW_MODULE, "--socket", str(sock)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=READY_SECONDS,
        )
        assert second.returncode == 3
        assert "another daemon is alive" in second.stderr

        assert daemon.send({"session": "main", "event": "Stop"})["ok"] is True


def test_the_two_daemons_run_side_by_side(sock):
    """✅ **既存の設置を1行も動かさずに、こちらを走らせられる。**

    ⚠️ **2つのソケットが同じ瞬間に在り、それぞれが自分の行に答える。**
    ⛔ **これは「設置し直さなくてよい」の証拠である**——0.19.50 の切り替えは、
    **切り替えるまで何も壊さないこと**を、まずここで負っている。
    """
    other = sock.parent / "old.sock"
    with Daemon(sock) as new, Daemon(other, module=OLD_MODULE) as old:
        assert sock.exists() and other.exists()
        assert new.send({"session": "n", "event": "SessionStart"})["ok"] is True
        assert old.send({"session": "o", "event": "SessionStart"})["ok"] is True
        assert new.send({"session": "n", "event": "PreToolUse",
                         "work": "write"})["ok"] is True

    assert new.code == 0 and old.code == 0


def test_each_refusal_names_its_fault(sock):
    with Daemon(sock) as daemon:
        assert daemon.send("not json")["error"] == "not-json"
        assert daemon.send({"event": "Stop"})["error"] == "missing-key"
        assert daemon.send({"session": "main", "event": "Nope"})["error"] == "unknown-event"
        assert daemon.send(
            {"session": "main", "event": "PreToolUse", "work": "fly"}
        )["error"] == "bad-value"


def test_the_prompt_never_reaches_the_log(sock):
    """⛔ **`work` が1語増えても、プライバシーは構造のままである。**"""
    secret = "a prompt that must not be logged"
    with Daemon(sock) as daemon:
        answer = daemon.send(
            {"session": "left", "event": "PreToolUse", "prompt": secret, "work": "write"}
        )
    assert answer == {"ok": False, "error": "unknown-key"}
    assert secret not in daemon.out


def test_a_line_over_the_bound_is_refused(sock):
    with Daemon(sock) as daemon:
        assert daemon.send("x" * (MAX_LINE + 1)) == {"ok": False, "error": "too-long"}


def test_a_silent_client_does_not_block_the_room(sock):
    with Daemon(sock) as daemon:
        silent = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        silent.connect(str(sock))
        time.sleep(0.3)  # ⚠️ CLIENT_TIMEOUT より長く、口を開けたままにする
        answer = daemon.send({"session": "main", "event": "SessionStart"})
        silent.close()
        assert answer["ok"] is True
        assert answer["phase"] == "greeting"


# ---------------------------------------------------------------------------
# 外向きの枠。⚠️ 書くが、送らない。
# ---------------------------------------------------------------------------


def test_the_daemon_logs_the_frame_it_would_send(sock):
    with Daemon(sock) as daemon:
        assert daemon.send({"session": "main", "event": "SessionStart"})["sent"] is False

    frames = daemon.frames()
    assert len(frames) == 1
    assert frames[0]["sent"] is False
    assert frames[0]["session"] == "main"

    command = wire.decode(frames[0]["frame"].encode("ascii"))
    assert command == wire.Command(face="greeting", light="warm", gesture="look_up")


def test_the_work_word_becomes_a_light_in_the_logged_frame(sock):
    """✅ **3語目が、語のまま光になる。** ⛔ **枠に数は1つも入らない。**

    ⚠️ **5秒待つのは、滞留そのものが規則だからである。** 道具の事象は
    `working` を開かない——章を開くのは `UserPromptSubmit` であり、その直後は
    まだ `dim` である。⇒ **待たずに書けば、この検査は滞留を測らずに通ってしまう。**
    """
    with Daemon(sock) as daemon:
        daemon.send({"session": "main", "event": "UserPromptSubmit"})
        time.sleep(WORK_DWELL + 0.15)
        daemon.send({"session": "main", "event": "PreToolUse", "work": "write"})

    frames = daemon.frames()
    lights = [wire.decode(f["frame"].encode("ascii")).light for f in frames]
    assert lights == ["dim", "writing"], lights
    for frame in frames:
        assert set(json.loads(frame["frame"])) == {"face", "light", "gesture", "sound"}


def test_an_unchanged_event_logs_no_second_frame(sock):
    with Daemon(sock) as daemon:
        daemon.send({"session": "main", "event": "PreToolUse", "work": "read"})
        daemon.send({"session": "main", "event": "PostToolUse", "work": "read"})

    frames = daemon.frames()
    assert len(frames) == 1
    command = wire.decode(frames[0]["frame"].encode("ascii"))
    assert command.light == "breathe"
    # ⚠️ **顔は、`blocked` を抜けるときにしか連れてこられない。** ⇒ `None` である。
    assert command.face is None


def test_the_configured_port_receives_the_logged_line(sock):
    """⚠️ **端末の代わりは、ただのファイルである。** ⛔ **光ったことは分からない。**"""
    port = sock.parent / "console"
    port.touch()
    with Daemon(sock, port=port) as daemon:
        assert daemon.send({"session": "main", "event": "SessionStart"})["ok"] is True

    frames = daemon.frames()
    assert len(frames) == 1
    assert frames[0]["sent"] is True
    written = [line for line in port.read_text(encoding="ascii").splitlines()
               if line and line != "bench pos"]
    assert written == [frames[0]["frame"]]


def test_a_missing_port_is_not_a_refusal(sock):
    port = sock.parent / "absent"
    with Daemon(sock, port=port) as daemon:
        assert daemon.send({"session": "main", "event": "SessionStart"})["ok"] is True
        assert daemon.send({"session": "main", "event": "PreToolUse",
                            "work": "run"})["ok"] is True

    frames = daemon.frames()
    assert frames, "枠が1つも出ていない——この検査は何も見ていない"
    assert all(f["sent"] is False for f in frames)
    assert all(f["err"] == "ENOENT" for f in frames)


def test_the_quiet_dial_is_a_flag_and_still_answers(sock):
    """⚠️ **静かなダイヤルは、黙ることではない。** 部屋は今まで通り答える。"""
    with Daemon(sock, extra=("--presence", "quiet")) as daemon:
        answer = daemon.send({"session": "main", "event": "UserPromptSubmit"})
        assert answer["ok"] is True
        assert answer["phase"] == "working"

    assert daemon.frames(), "枠が1つも出ていない——この検査は何も見ていない"


@pytest.mark.parametrize("presence", PRESENCES)
def test_the_startup_row_names_the_dial_and_the_socket(sock, presence):
    """⚠️ **どのダイヤルで走っているかは、ログの1行目に在る。**"""
    with Daemon(sock, extra=("--presence", presence)) as daemon:
        daemon.send({"session": "main", "event": "Stop"})

    listening = [row for row in daemon._lines() if row.get("daemon") == "listening"]
    assert listening, daemon.out
    assert listening[0]["socket"] == str(sock)
    assert listening[0]["presence"] == presence
    assert listening[0]["port"] is None


# ---------------------------------------------------------------------------
# 2本目のソケットと糸（0.19.64、Phase 3.5）。⚠️ 返事はまだ誰も読まない。
# ---------------------------------------------------------------------------


def test_the_meta_socket_is_a_second_door_on_the_same_process(sock):
    """✅ **同じプロセスが、2本の戸口を持つ。** ⛔ **体のソケットに相乗りしない。**

    相乗りすれば、体が枠を書いて基板の受理を待つあいだ（中央 890ms）、
    **監修の一言がその後ろで待つ**——§19.1 の実測がそれである。
    """
    with Daemon(sock) as daemon:
        assert sock.exists()
        assert daemon.meta.exists()
        assert sock != daemon.meta

        # ⚠️ **返事の形は `context` の1つである。** 候補が無ければ `null` であり、
        #    ⛔ **鍵そのものを省かない**——読む側が *返事なし* と *形が違う* を
        #    区別できなくなる。
        assert daemon.send_meta(
            {"session": "m", "event": "UserPromptSubmit"}) == {"context": None}
        assert daemon.send_meta({"session": "m", "event": "Stop"}) == {"context": None}


def test_a_turn_review_is_logged_as_a_candidate_and_carried_by_the_next_prompt(sock):
    """⚠️ **規則が鳴ることと、声が届くことを、別の行にする**（§10.6）。

    ⛔ **1行にまとめれば、「作ったが渡らなかった」が数えられない。**
    ⚠️ **25回は呼び出しの数である**（`PreToolUse` の1行が1回）——往復で倍に数えない。
    """
    # ⚠️ **Phase 4 のフックと同じ形で送る**——同じ1行を、2つのソケットへ。
    #    ⛔ **体のソケットへ送っただけでは、メタの糸は1行も見ない。**
    with Daemon(sock) as daemon:
        # ⚠️ **ターンはプロンプトで開く。** 開かなければ、道具は数えられない
        #    （`Trace.observe`——`STEALS` が窓を決める）。
        opening = {"session": "m", "event": "UserPromptSubmit"}
        daemon.send(opening)
        daemon.send_meta(opening)
        for _ in range(25):
            event = {"session": "m", "event": "PreToolUse"}
            daemon.send(event)
            daemon.send_meta(event)
        assert daemon.meta_rows() == [], "閉じる前に候補が立っている"

        closing = {"session": "m", "event": "Stop"}
        daemon.send(closing)
        daemon.send_meta(closing)
        answer = daemon.send_meta({"session": "m", "event": "UserPromptSubmit"})

    rows = daemon.meta_rows()
    assert [row["meta"] for row in rows] == ["candidate", "delivered"], rows
    assert rows[0]["kind"] == rows[1]["kind"] == "turn-review"
    assert rows[0]["session"] == rows[1]["session"] == "m"

    # ⚠️ **返事は、このプロンプトに載る1文である。** 文にするのは `render` の1か所。
    assert answer["context"] is not None
    assert "over 25 tool calls" in answer["context"]
    assert answer["context"].startswith("[stack-chan meta]")

    # ⛔ **行に自由文は無い。** 数と、閉じた語だけである（§10.6、§14）。
    for row in rows:
        assert set(row) <= {"meta", "kind", "session", "why", "at", "error"}
        assert isinstance(row["at"], (int, float))


def test_meta_off_opens_no_socket_and_the_startup_row_says_so(sock):
    """⛔ **0 は2つの意味を持つ。** 規則が鳴らなかった日と、黙らされた日である。

    ⚠️ **分けるのは起動行の `meta` だけである**——候補の数では、どちらも0である。
    ⛔ **`off` の実装は「ソケットが無い」である。** フックはダイヤルを知らない。
    """
    with Daemon(sock, extra=("--meta", "off")) as daemon:
        assert sock.exists()
        assert not daemon.meta.exists()
        assert daemon.send({"session": "m", "event": "Stop"})["ok"] is True

    listening = [row for row in daemon._lines() if row.get("daemon") == "listening"]
    assert listening and listening[0]["meta"] == "off"


def test_the_meta_dial_is_written_on_the_startup_row(sock):
    """⚠️ **既定でも、値を書く。** 黙った日と黙らされた日を、計器が同じ0と言わないように。"""
    with Daemon(sock) as daemon:
        daemon.send({"session": "m", "event": "Stop"})

    listening = [row for row in daemon._lines() if row.get("daemon") == "listening"]
    assert listening and listening[0]["meta"] == "quiet"


def test_the_meta_socket_is_removed_with_the_body_socket(sock):
    """⛔ **戸口が2つなら、片付けも2つである。**"""
    with Daemon(sock) as daemon:
        assert daemon.meta.exists()

    assert daemon.code == 0
    assert not sock.exists() and not daemon.meta.exists()


def test_an_exception_at_the_thread_edge_is_one_row_and_the_loop_waits(sock, capsys):
    """⛔ **核心に `try` を書かない。** 例外は糸の縁で捕まえ、型名だけを1行残す。

    核心が自分で例外を飲めば、「規則が壊れている」ことが見えなくなる（§19.7）。
    ⛔ **自由文を入れない**——`error` の欄は閉じている。
    """
    import threading

    class Boom:
        def observe(self, *args: object, **kwargs: object) -> str:
            raise ValueError("boom")

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(sock))
    listener.listen(1)
    thread = threading.Thread(target=edge.meta_loop,
                              args=(listener, Boom()), daemon=True)
    thread.start()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(READY_SECONDS)
            client.connect(str(sock))
            client.sendall(b'{"session": "m", "event": "Stop"}\n')
            # ⚠️ **返事は来ない。** 例外は `reply` の前に起きる——縁が1行残して
            #    次の接続を待つことを、ここから見る。
            client.recv(1)
    finally:
        listener.close()

    rows = []
    limit = time.monotonic() + READY_SECONDS
    while time.monotonic() < limit:
        rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()
                if line.strip()]
        if rows:
            break
        time.sleep(0.02)

    assert rows == [{"meta": "error", "error": "ValueError"}], rows


# ---------------------------------------------------------------------------
# 声（2026-10-21）。⛔ **`--say` は計器であり、候補の道ではない。**
# ---------------------------------------------------------------------------


def test_say_without_listen_is_refused_before_anything_is_bound(tmp_path):
    """⛔ **声は、基板が開いた回線へしか流れない。**

    ⚠️ **Mac から基板へは、33回すべて届かなかった**（2026-10-21 の実測）。
    ⇒ **`--listen` の無い `--say` は、鳴らない約束である**——束縛する前に断る。
    """
    path = tmp_path / "body.sock"
    code = edge.main(["--socket", str(path), "--say", "これは試験である。"])
    assert code == 1
    assert not path.exists(), "断ったのに、ソケットが作られている"


def _shut(proc: subprocess.Popen) -> tuple[str, str]:
    """**必ず終わらせて、出力を返す。** ⛔ **待ちに上限が無いと、試験が止まる。**"""
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
    try:
        return proc.communicate(timeout=READY_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        return proc.communicate()


def _free_port() -> int:
    """**空いている番号を1つ。** ⚠️ 閉じた番号を渡すので、厳密には競争である。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.mark.skipif(
    __import__("shutil").which("say") is None,
    reason="say が無い機械では、声そのものを作れない")
def test_the_board_hears_the_sentence_when_it_dials_in(sock):
    """**基板が dial すると、頭つきの塊が来る。** ⛔ **これが B の配管の端から端である。**

    ⚠️ **本物の `say` と `afconvert` が走る**（1〜2 秒）。これは計器の試験であり、
    声の良し悪しは**著者の耳**である（§22.6）。ここで測るのは
    **「文が、頭とバイトの列として回線に出た」ことだけ**である。
    """
    # ⚠️ **`tmp_path` は `sun_path` に長すぎる**（`conftest` の `sock`）。
    path = sock
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", NEW_MODULE, "--socket", str(path),
         "--listen", f"127.0.0.1:{port}", "--meta", "off",
         "--say", "これは、試験である。"],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    board: socket.socket | None = None
    try:
        limit = time.monotonic() + READY_SECONDS
        while True:
            # ⛔ **失敗したソケットを、もう一度 `connect` しない。** macOS では
            #    2回目が `EINVAL` で返り、**「まだ居ない」が「永久に繋がらない」に化ける**
            #    ——2026-10-21、この試験がその形で10秒を使って落ちた。
            attempt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                attempt.connect(("127.0.0.1", port))
                board = attempt
                break
            except OSError:
                attempt.close()
                # ⛔ **上限の無い `communicate()` を書かない。** 書けば、
                #    **デーモンが生きているあいだ、試験が永久に止まる**
                #    （2026-10-21 にこの試験が2分止まり、その形で止まった）。
                if time.monotonic() > limit or proc.poll() is not None:
                    out, err = _shut(proc)
                    raise AssertionError(f"dial できなかった: {out}{err}")
                time.sleep(0.02)
        assert board is not None
        board.settimeout(READY_SECONDS * 4)
        heard = b""
        while b"\n" not in heard:
            chunk = board.recv(4096)
            if not chunk:
                raise AssertionError("回線が閉じた")
            heard += chunk
        header, _, body = heard.partition(b"\n")
        # ⚠️ **頭は基板の綴りである**（`audio <n>`）。
        assert header.startswith(b"audio "), header
        assert int(header.split()[1]) % 2 == 0
        # ⚠️ **頭が言う数だけ、標本が来る。** 1バイトも足りない。
        want = int(header.split()[1])
        while len(body) < want:
            chunk = board.recv(4096)
            if not chunk:
                raise AssertionError("塊が途中で終わった")
            body += chunk
        assert len(body) >= want
    finally:
        if board is not None:
            board.close()
        _shut(proc)
