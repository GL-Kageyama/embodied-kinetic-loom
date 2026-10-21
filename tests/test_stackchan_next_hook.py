# -*- coding: utf-8 -*-
"""**2つ目の層のフックの縁。**

⚠️ **2つに分かれている。** `client.line_from` は入力と出力の関数であり、
`tests/test_stackchan_next_work.py` がすでに持っている。⇒ **このファイルが
起こすのは本物のプロセスである**——標準入力を読み、ソケットへ1行を送り、
何も印字せずに0で終わる。

⛔ **このファイルが確かめないこと:** 設置そのもの——`settings.json` への登録と
launchd（0.19.50 である）。⛔ **光ったことも確かめない**: 枠は `sent: False` で
ログに残るところまでである。**機体へ届いたかは、基板の行が言う。**

⚠️ **2つの層が同じ瞬間に走れることを、このファイルは既に前提にしている。**
確かめるのは**この戸口がこの部屋にだけ通じる**ことであり、その証拠として
**1つ目の部屋が3語目を知らない**ことを1つ置いた。
"""
from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import sys
import time

import pytest

from engine.backend import protocol_stackchan as wire
from projects.stackchan.daemon.room import socket_path as old_socket_path
from projects.stackchan_next.client import INPUT_LIMIT, reads_reply
from projects.stackchan_next.daemon.room import meta_socket_path, socket_path
from projects.stackchan_next.presence import WORK_DWELL
from test_stackchan_next_daemon import (
    NEW_MODULE,
    OLD_MODULE,
    REPO_ROOT,
    Daemon,
)

HOOK_MODULE = "projects.stackchan_next.hook"
EDGE = pathlib.Path(REPO_ROOT) / "projects" / "stackchan_next" / "hook" / "__main__.py"


def run_client(path, text: str, meta=None) -> subprocess.CompletedProcess:
    """⚠️ **本物のプロセスを1つ起こす。** 標準入力は文字列である。

    ⛔ **メタの行き先は、必ず試験の側で名指す**——既定の
    `/tmp/ekl-stackchan-meta-<uid>.sock` を放っておくと、**設置済みのデーモンへ
    本物の事象を送る試験**になる。既定は体のソケットの隣である。
    """
    if meta is None:
        meta = pathlib.Path(path).parent / "meta.sock"
    return subprocess.run(
        [sys.executable, "-m", HOOK_MODULE, "--socket", str(path),
         "--meta-socket", str(meta)],
        cwd=REPO_ROOT,
        input=text,
        capture_output=True,
        text=True,
        timeout=10,
    )


def refusals(daemon: Daemon) -> list[dict]:
    """**断りの行。** ⚠️ `rows()` は判定だけを拾うので、こちらは別に数える。"""
    found = []
    for line in daemon.out.splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("ok") is False:
            found.append(payload)
    return found


# ---------------------------------------------------------------------------
# 戸口。⛔ プロセスもソケットも無い。
# ---------------------------------------------------------------------------


def test_the_door_is_the_second_daemons_and_not_the_first():
    """⚠️ **綴りは1つであり、prefix が1つ違う。**"""
    from projects.stackchan_next.hook import __main__ as hook_main

    assert socket_path(501) == "/tmp/ekl-stackchan-next-501.sock"
    assert hook_main.default_socket() == socket_path(os.getuid())
    assert hook_main.default_socket() != old_socket_path(os.getuid())


def test_the_edge_borrows_the_reading_and_owns_only_the_door():
    """⛔ **写しではない。** 標準入力の読み方は向こうから借りている。

    ⚠️ **同じ規則を2つ持てば、片方が黙って緩んだ日に、もう片方が鳴らない。**
    ⇒ **この縁が自分で書くのは `main` と `build_parser` だけである。**
    """
    source = EDGE.read_text(encoding="utf-8")

    assert "from projects.stackchan.hook.__main__ import read_payload" in source
    assert "from ..client import REPLY_EVENT, line_from, reads_reply" in source
    assert "from ..daemon.room import meta_socket_path, socket_path" in source
    assert "def read_payload(" not in source
    assert "def main(" in source


# ---------------------------------------------------------------------------
# 縁。⚠️ 本物の標準入力とソケット。
# ---------------------------------------------------------------------------


def test_a_write_event_reaches_the_room_with_its_word(sock):
    """⚠️ **`working` は `UserPromptSubmit` から始まる。** 道具の事象は章を開かない。

    ⇒ 2つの別プロセスで開き、そのあいだに部屋が状態を持つ——**この橋の存在理由である。**
    """
    with Daemon(sock) as daemon:
        opened = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "UserPromptSubmit"}
        ))
        wrote = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "PreToolUse",
             "tool_name": "Edit", "tool_input": {"file_path": "/secret"}}
        ))

    assert opened.returncode == 0 and wrote.returncode == 0
    assert opened.stdout == "" and wrote.stdout == ""

    rows = daemon.rows()
    assert [r["event"] for r in rows] == ["UserPromptSubmit", "PreToolUse"]
    # ⚠️ **鍵そのものが無い。** `null` にすれば「その他」と「知らされていない」が
    #    同じ行になり、一日の内訳がその2つを数えられない。
    assert "work" not in rows[0]
    assert rows[1]["work"] == "write"
    assert rows[1]["phase"] == "working"
    assert rows[1]["light"] == "writing"
    assert "/secret" not in daemon.out


def test_the_word_becomes_a_light_on_the_logged_frame(sock):
    """✅ **語は、行ではなく枠に載る。** ⛔ **送ってはいない**——`sent` である。"""
    with Daemon(sock) as daemon:
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "UserPromptSubmit"}
        ))
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "PreToolUse",
             "tool_name": "Bash"}
        ))

    frames = daemon.frames()
    assert frames, "the room logged no frame"

    # ⚠️ **ログの `frame` は符号化された1行である**（`frame_row`）。復号して読む——
    #    読む側と書く側が同じ符号器を通ることが、ここでも1回確かめられる。
    command = wire.decode(frames[-1]["frame"].encode("ascii"))
    assert command.light == "busy"
    assert set(json.loads(frames[-1]["frame"])) == {
        "face", "light", "gesture", "sound"
    }
    assert frames[-1]["sent"] is False


def test_the_dwell_holds_the_light_across_two_tools(sock):
    """⚠️ **待つことそのものが規則である。** 5秒の滞留は、実時計では待たないと見えない。

    ⚠️ **最初の1語はすぐ見える**——`working` へ入った時刻を「滞留の1つ前」として
    数えるからである（`presence.py`）。⇒ **滞留を測るには、光が一度変わっていなければ
    ならない。** だから `run` で `busy` にしてから、`read` を続けて2回送る:

    - 1回目（5秒の内側）→ `busy` のまま；
    - 2回目（5.15秒の外側）→ `dim`。
    """
    with Daemon(sock) as daemon:
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "UserPromptSubmit"}
        ))
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "PreToolUse",
             "tool_name": "Bash"}
        ))
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "PreToolUse",
             "tool_name": "Read"}
        ))
        time.sleep(WORK_DWELL + 0.15)
        run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "PreToolUse",
             "tool_name": "Read"}
        ))

    lights = [r["light"] for r in daemon.rows() if r["event"] == "PreToolUse"]
    assert lights == ["busy", "busy", "dim"]


def test_the_first_room_does_not_know_the_third_word(sock):
    """⛔ **戸口は契約である。** この縁を1つ目の部屋へ向ければ、道具の行は断られる。

    ⚠️ **黙って落ちるのではなく、`unknown-key` で断られる**——それが、設置の
    1行が間違った日に読める形である。
    """
    with Daemon(sock, module=OLD_MODULE) as daemon:
        opened = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "UserPromptSubmit"}
        ))
        wrote = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "PreToolUse",
             "tool_name": "Edit"}
        ))

    assert opened.returncode == 0 and wrote.returncode == 0
    assert [r["event"] for r in daemon.rows()] == ["UserPromptSubmit"]
    assert refusals(daemon) == [{"ok": False, "error": "unknown-key"}]


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
    """⛔ **読めば、ターンがデーモンの速さを待つことになる。**"""
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


# ---------------------------------------------------------------------------
# 配送（Phase 4）—— ⛔ **返事を読むのはプロンプトのときだけである**
# ---------------------------------------------------------------------------

PROMPT = {"session_id": "left", "hook_event_name": "UserPromptSubmit"}


def drive_to_candidate(daemon: Daemon, session: str = "left") -> None:
    """**25回の呼び出しと `Stop` で、候補を1つ作る。** ⚠️ **声はまだ出ていない。**

    ⚠️ **体のソケットではなく、メタのソケットへ直接送る**——ここで測りたいのは
    *フックが返事を読むか*であり、*体が事象を運ぶか*ではない。
    """
    for _ in range(25):
        daemon.send_meta({"session": session, "event": "PreToolUse",
                          "work": "run"})
    daemon.send_meta({"session": session, "event": "Stop"})


def test_the_meta_socket_is_spelled_once():
    """⚠️ **2か所に書けば、片方だけが直る日が来る。**"""
    from projects.stackchan_next.daemon import __main__ as daemon_edge
    from projects.stackchan_next.hook import __main__ as hook_main

    assert meta_socket_path(501) == "/tmp/ekl-stackchan-meta-501.sock"
    assert hook_main.default_meta_socket() == meta_socket_path(os.getuid())
    assert daemon_edge.default_meta_socket() == meta_socket_path(os.getuid())
    assert hook_main.default_meta_socket() != hook_main.default_socket()


@pytest.mark.parametrize("event", ["UserPromptSubmit", "Stop", "PreToolUse"])
def test_only_a_prompt_reads_the_reply(event):
    """⛔ **32の事象が返事を読めば、ターンがデーモンの速さを待つ。**"""
    line = json.dumps({"session": "s", "event": event}) + "\n"
    assert reads_reply(line) is (event == "UserPromptSubmit")


def test_a_prompt_carries_the_sentence_as_additional_context(sock):
    """✅ **次のプロンプトが、前のターンの1文を運ぶ**（設計 §12.1）。"""
    with Daemon(sock) as daemon:
        opened = run_client(sock, json.dumps(PROMPT))
        drive_to_candidate(daemon)
        said = run_client(sock, json.dumps(PROMPT))

    # ⚠️ **行はデーモンが止まってから読む**（`out` は `communicate` の返りである）。
    delivered = [r for r in daemon.meta_rows() if r["meta"] == "delivered"]

    # ⚠️ **最初のプロンプトは何も言わない**——待っている候補が無いからである。
    assert opened.returncode == 0 and opened.stdout == ""
    assert said.returncode == 0
    payload = json.loads(said.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert payload["hookSpecificOutput"]["additionalContext"].startswith(
        "[stack-chan meta]")
    # ⚠️ **印字したことと、部屋が渡したことは同じ1件である。**
    assert len(delivered) == 1


def test_a_stop_does_not_read_the_reply(sock):
    """⛔ **`Stop` の `additionalContext` は、ユーザーの答えを置き換える。**

    ⇒ **既定では読まない。** その候補は、次のプロンプトまで残る。
    """
    with Daemon(sock) as daemon:
        run_client(sock, json.dumps(PROMPT))
        drive_to_candidate(daemon)
        stopped = run_client(sock, json.dumps(
            {"session_id": "left", "hook_event_name": "Stop"}
        ))
        said = run_client(sock, json.dumps(PROMPT))

    assert stopped.returncode == 0 and stopped.stdout == ""
    # ⚠️ **読みもしない返事は捨てられていない**——次のプロンプトが運んでいる。
    assert json.loads(said.stdout)["hookSpecificOutput"]["additionalContext"]


def test_a_dead_body_does_not_take_the_meta_down(sock):
    """⛔ **監修は、体の故障に道連れにされない**（設計 §12.1）。"""
    nowhere = sock.parent / "no-body.sock"
    assert not nowhere.exists()

    with Daemon(sock) as daemon:
        run_client(sock, json.dumps(PROMPT))
        drive_to_candidate(daemon)
        said = run_client(nowhere, json.dumps(PROMPT), meta=daemon.meta)

    assert said.returncode == 0
    assert json.loads(said.stdout)["hookSpecificOutput"]["additionalContext"]


def test_a_missing_meta_socket_is_silent(sock):
    """⚠️ **メタのデーモンが居ないことは、フックの失敗ではない。**"""
    absent = sock.parent / "absent-meta.sock"
    assert not sock.exists() and not absent.exists()

    result = run_client(sock, json.dumps(PROMPT), meta=absent)

    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""
