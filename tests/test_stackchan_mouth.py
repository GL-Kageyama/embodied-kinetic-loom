# -*- coding: utf-8 -*-
"""**口** —— 本体が書いた1文を、体のスピーカーで言わせる縁（設計 §22.10）。

⚠️ **この試験が確かめるのは、3つの段である。**

1. **要求の形**（`parse_voice`）——鍵は1つ、文は1行、長さは選んだ数。
2. **縁の道具**（`projects/stackchan_next/mouth`）——どの道も1語を印字し、
   **`queued` と `night` だけが 0 で終わる。**
3. **断りの順**（`voice_handle`）——**板が居ないことは事実であり、規則ではない。**

⛔ **この試験が確かめないこと:** 声が聞こえたこと、その声が良いこと。
それは**著者の耳**である（§22.6）。ここで測るのは**言葉と符号の道だけ**である。
"""
from __future__ import annotations

import json
import pathlib
import socket
import threading

import pytest

from projects.stackchan.daemon.room import REFUSAL_CODES, BadRequest
from projects.stackchan_next.daemon import __main__ as edge
from projects.stackchan_next.daemon.room import (
    VOICE_KEYS,
    VOICE_MAX_CHARS,
    mouth_socket_path,
    parse_voice,
)
from projects.stackchan_next.mouth import __main__ as mouth

#: ⚠️ **口の道具が待つ上限である。** 糸を止め忘れれば、試験がここで止まる。
WAIT = 5.0


# ---------------------------------------------------------------------------
# 要求の形。⛔ ソケットも時計も無い。
# ---------------------------------------------------------------------------


def test_the_mouth_is_the_third_spelling():
    """⛔ **3本の戸口は、3つの綴りである。** 相乗りすれば§8.2 が偽になる。"""
    from projects.stackchan.daemon.room import socket_path as body_path
    from projects.stackchan_next.daemon.room import socket_path as next_path
    from projects.stackchan_next.daemon.room import meta_socket_path

    spellings = {body_path(501), next_path(501), meta_socket_path(501),
                 mouth_socket_path(501)}
    assert len(spellings) == 4
    assert mouth_socket_path(501) == "/tmp/ekl-stackchan-mouth-501.sock"


def test_the_request_has_one_key_and_the_sentence_is_the_whole_of_it():
    """⚠️ **窓も事象も載せない。** 口は体の1文であり、事象ではない。"""
    assert VOICE_KEYS == frozenset({"text"})
    assert parse_voice('{"text": "長かった。25回、書いてた。"}') == \
        "長かった。25回、書いてた。"


@pytest.mark.parametrize("line, code", [
    ("これはJSONではない", "not-json"),
    ("[1, 2]", "not-an-object"),
    ('{"text": "はい", "event": "Stop"}', "unknown-key"),
    # ⚠️ **`{"event": …}` は `unknown-key` である**——知らない鍵のほうが先に立つ。
    ("{}", "missing-key"),
    ('{"text": 3}', "bad-value"),
    ('{"text": "   "}', "bad-value"),
    ('{"text": "一行目\\n二行目"}', "bad-value"),
    ('{"text": "' + "あ" * (VOICE_MAX_CHARS + 1) + '"}', "too-long"),
])
def test_a_line_the_mouth_cannot_read_is_refused_with_a_known_code(line, code):
    """⛔ **新しい符号を発明しない。** 体中の閉じた集合から選ぶ。"""
    assert code in REFUSAL_CODES
    with pytest.raises(BadRequest) as refused:
        parse_voice(line)
    assert refused.value.code == code


def test_the_length_is_a_choice_and_it_does_not_cut():
    """⛔ **切り詰めない**——**切った文は、別の文である。** 長すぎる文は断る。"""
    exactly = "あ" * VOICE_MAX_CHARS
    assert parse_voice(json.dumps({"text": exactly})) == exactly


# ---------------------------------------------------------------------------
# 縁の道具。⚠️ **どの道も1語を印字する。**
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reply, word", [
    (b'{"voice": "queued"}\n', "queued"),
    (b'{"voice": "night"}\n', "night"),
    (b'{"voice": "busy"}\n', "busy"),
    (b'{"voice": "no-board"}\n', "no-board"),
    (b'{"voice": "refused", "error": "too-long"}\n', "refused:too-long"),
    (b'{"voice": "refused"}\n', "refused"),
    (b"", "unreadable"),
    (b"not json\n", "unreadable"),
    (b"[1]\n", "unreadable"),
    (b'{"voice": 7}\n', "unreadable"),
])
def test_the_reply_becomes_one_word(reply, word):
    """⛔ **返事が無いことと、形が違うことは、別である**——だが
    **どちらも「鳴ったとは言えない」**ので、道具は2つを1語に落とす。"""
    assert mouth.state_of(reply) == word


def _serve_once(path: pathlib.Path, reply: dict | str) -> tuple[dict, threading.Thread]:
    """**1回だけ答える偽のデーモン。** ⚠️ 本物の口は、この試験では起こさない。"""
    seen: dict = {}
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    listener.listen(1)

    def run() -> None:
        with listener:
            connection, _ = listener.accept()
            with connection:
                buffer = b""
                while b"\n" not in buffer:
                    chunk = connection.recv(4096)
                    if not chunk:
                        return
                    buffer += chunk
                seen.update(json.loads(buffer.partition(b"\n")[0]))
                line = reply if isinstance(reply, str) else json.dumps(reply)
                connection.sendall(line.encode("utf-8") + b"\n")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return seen, thread


@pytest.mark.parametrize("reply, code", [
    ({"voice": "queued"}, 0),
    ({"voice": "night"}, 0),
    ({"voice": "busy"}, 1),
    ({"voice": "no-board"}, 1),
    ({"voice": "refused", "error": "bad-value"}, 1),
])
def test_only_queued_and_night_are_success(sock, capsys, reply, code):
    """⚠️ **`night` は故障ではない**——**規則が働いた日である**（§17.4 (c)）。"""
    _, thread = _serve_once(sock, reply)
    assert mouth.main(["これは、試験である。", "--socket", str(sock)]) == code
    thread.join(WAIT)
    words = capsys.readouterr().out.split()
    assert len(words) == 1, words
    assert words[0].startswith(reply["voice"])


def test_the_words_given_on_the_command_line_are_one_sentence(sock, capsys):
    """⚠️ **囲み忘れた文が、黙って1語目だけにならないように。**"""
    seen, thread = _serve_once(sock, {"voice": "queued"})
    mouth.main(["これは", "試験で", "ある。", "--socket", str(sock)])
    thread.join(WAIT)
    assert seen == {"text": "これは 試験で ある。"}


def test_a_missing_daemon_says_so_and_is_not_a_silent_success(sock, capsys):
    """⛔ **フックとは逆である。** フックは欠けても体の故障ではないが、
    **この道具は「鳴らなかったこと」を言うために呼ばれている。**"""
    assert not sock.exists()
    assert mouth.main(["はい", "--socket", str(sock)]) == 1
    assert capsys.readouterr().out.strip() == "no-daemon"


# ---------------------------------------------------------------------------
# 断りの順。⚠️ **板が居ないことは事実であり、規則ではない。**
# ---------------------------------------------------------------------------


class _Link:
    """**板の回線。** ⚠️ ここで要るのは `peer` の在否だけである。"""

    def __init__(self, peer: object | None) -> None:
        self.peer = peer


class _Speaker:
    """**声の糸の代役。** ⚠️ 断るかどうかだけを決める。"""

    def __init__(self, answer: bool = True) -> None:
        self.answer = answer
        self.said: list[str] = []

    def say(self, text: str) -> bool:
        self.said.append(text)
        return self.answer


def _ask(line: bytes, speaker: _Speaker, link: _Link | None, hour: int) -> dict:
    """**1接続を、音も時計も無しで通す。** ⚠️ ソケットは対で作る。"""
    left, right = socket.socketpair()
    try:
        right.sendall(line)
        edge.voice_handle(left, speaker, link, hour)
        buffer = b""
        while b"\n" not in buffer:
            chunk = right.recv(4096)
            if not chunk:
                break
            buffer += chunk
        return json.loads(buffer.partition(b"\n")[0])
    finally:
        left.close()
        right.close()


def test_the_night_is_a_face_and_not_a_voice():
    """⚠️ **§17.4 (c) の裁定は「昼に限り」である。** 夜は表情だけ（§22.5）。

    ⛔ **規則は `quiet.py` に1つだけ在る。** 音の欄を閉じるのと同じ関数である。
    """
    speaker = _Speaker()
    for hour in (21, 23, 0, 5):
        assert _ask(b'{"text": "\xe8\xa9\xb1"}\n', speaker,
                    _Link(object()), hour) == {"voice": "night"}
    assert speaker.said == [], "夜に合成している"


def test_a_board_that_is_not_there_is_seen_before_the_hour():
    """⛔ **順が規則である。** 無い回線へ3秒の合成をしない。

    ⚠️ **夜でも「板が居ない」は同じ事実である**——ゆえに時より先に見る。
    """
    speaker = _Speaker()
    assert _ask(b'{"text": "\xe8\xa9\xb1"}\n', speaker, None, 22) == {
        "voice": "no-board"}
    assert _ask(b'{"text": "\xe8\xa9\xb1"}\n', speaker, _Link(None), 2) == {
        "voice": "no-board"}
    assert speaker.said == []


def test_a_busy_speaker_refuses_and_the_sentence_is_not_queued_behind():
    """⚠️ **古い候補を、新しい瞬間に言わない**（§12）。⇒ **深さ1、話していれば断る。**"""
    speaker = _Speaker(answer=False)
    assert _ask(b'{"text": "\xe8\xa9\xb1"}\n', speaker, _Link(object()), 12) == {
        "voice": "busy"}
    assert speaker.said == ["話"]


def test_a_queued_sentence_is_handed_over_once():
    """⚠️ **受け取ったことと、鳴り終えたことは、2行である。**"""
    speaker = _Speaker()
    assert _ask(b'{"text": "\xe8\xa9\xb1"}\n', speaker, _Link(object()), 12) == {
        "voice": "queued"}
    assert speaker.said == ["話"]


def test_a_queued_sentence_leaves_no_row_of_its_own(capsys):
    """⛔ **`queued` は返事であって、行ではない。**

    ⚠️ **行にすれば `voice` の値が1つ増え、計器がそれを `unreadable` と数える**——
    受け取ったことは、**鳴り終えた `spoke` の行が既に含んでいる。**
    """
    speaker = _Speaker()
    _ask(b'{"text": "\xe8\xa9\xb1"}\n', speaker, _Link(object()), 12)
    assert capsys.readouterr().out == ""


def test_a_refusal_is_the_body_s_own_code():
    """⚠️ **体と同じ符号である。** 口だけの語彙を作らない。"""
    speaker = _Speaker()
    assert _ask(b'{"text": "a", "event": "Stop"}\n', speaker,
                _Link(object()), 12) == {"voice": "refused",
                                         "error": "unknown-key"}
    assert speaker.said == []
