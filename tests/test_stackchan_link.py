# -*- coding: utf-8 -*-
"""**基板が dial してくる先。** ⚠️ **この縁は、待ち受けと、切れていないことの2つだけを持つ。**

⛔ **向きは、こちらから選べない。** 2026-10-21 に測った: Mac から基板へは
**33回すべて `EHOSTUNREACH`、1回 0.1 ミリ秒**であり（87回の連射でも 0）、
**届いたのは基板が開いた1本だけ**だった。⇒ **デーモンは待ち受ける。**

⚠️ **このファイルが確かめないこと:** 本物の基板、本物の Wi-Fi、launchd。
ここで「基板」は**同じ機械のループバックに居る、行を読み書きするソケット**である。
⛔ **`accepted: True` が本物の基板の言葉であることは、ここでは確かめられない。**

⚠️ **いちばん危うい規則が、いちばん先に在る**: `Link` の fd は `Link` のものであり、
**首は身振りの終わりにそれを閉じてはならない。** 閉じれば、**1つの身振りが接続を畳む**
——そしてその次の枠は `nobody` になる。**このファイルは、それを2つの身振りで測る。**
"""
from __future__ import annotations

import json
import os
import select
import socket
import threading
import time

import pytest

from projects.stackchan.daemon import __main__ as edge
from projects.stackchan.daemon.room import Room
from projects.stackchan_next.daemon import __main__ as next_edge

#: **待つ上限（秒）。** ⚠️ **本物の待ち（`PORT_WAIT = 0.5`）より長く取る。**
WAIT = 2.0


class Board(threading.Thread):
    """**ループバックに座る、偽の基板。** ⚠️ **答えるのは2つの綴りだけである。**

    ⛔ **本物の `ConsoleTask` ではない。** ここで確かめるのは
    **「行が届き、答えが同じ fd に返る」**ことであり、
    **基板がその行をどう解釈するか**ではない。
    """

    def __init__(self, connection: socket.socket) -> None:
        super().__init__(daemon=True)
        self.connection = connection
        self.lines: list[str] = []
        self.poses: list[str] = []
        self.frames: list[str] = []
        self.queries = 0
        self._done = threading.Event()

    def run(self) -> None:
        buffer = b""
        self.connection.settimeout(WAIT)
        while not self._done.is_set():
            try:
                chunk = self.connection.recv(4096)
            except OSError:
                return
            if not chunk:
                return
            buffer += chunk
            while b"\n" in buffer:
                raw, _, buffer = buffer.partition(b"\n")
                line = raw.decode("utf-8", "replace")
                if line:
                    self.lines.append(line)
                    self._answer(line)

    def _answer(self, line: str) -> None:
        if line == "bench pos":
            self.queries += 1
            # ⚠️ **本物の綴りである**（`main.cpp` の `bench pos`）——試験の都合で変えない。
            self._say("bench: yaw=ok pitch=ok\n"
                      "bench: yaw raw 500, angle 10.0 deg (zero 460)\n"
                      "bench: pitch raw 700, angle 40.0 deg (zero 620)\n")
        elif line.startswith("pose "):
            self.poses.append(line)
        elif line.startswith("{"):
            self.frames.append(line)
            self._say("frame: light=warm face=happy gesture=none sound=none\n")

    def _say(self, text: str) -> None:
        try:
            self.connection.sendall(text.encode("utf-8"))
        except OSError:
            pass

    def stop(self) -> None:
        self._done.set()
        try:
            self.connection.close()
        except OSError:
            pass


class SlowBoard(Board):
    """**0.7 秒かけて答える基板。** ⛔ **有線で測った 0.5 秒の窓の外である。**

    ⚠️ **2026-10-21 の実測から来ている**: リンク越しの `bench pos` 10回で、
    位置の行は **+0.041 秒から +0.861 秒**に届いた。⇒ **0.5 秒で切る探針は、
    遅い側の答えを窓の外に落とす**——その日、デーモンは2回続けて `read: ""` を残した。
    """

    def _answer(self, line: str) -> None:
        if line == "bench pos":
            time.sleep(0.7)
        super()._answer(line)


def _dial(link: "edge.Link", previous: str | None = None,
          kind: type[Board] = Board) -> Board:
    """**基板が dial する。** ⚠️ **接続は、待ち受ける側が `accept` するまで溜まっている。**

    ⚠️ **`previous` は、2本目を待つためである。** 1本目が居るあいだは `peer` が
    既に埋まっているので、**「変わったこと」を待たなければ、受け取る前に返る。**
    """
    port = int(link.address.rsplit(":", 1)[1])
    connection = socket.create_connection(("127.0.0.1", port), timeout=WAIT)
    board = kind(connection)
    board.start()
    deadline = time.monotonic() + WAIT
    while link.peer == previous and time.monotonic() < deadline:
        select.select([link.listener], [], [], 0.02)
        link.accept()
    assert link.peer is not None and link.peer != previous, "接続が受け取られなかった"
    return board


def _rows(captured: str) -> list[dict]:
    """**デーモンが書いた行を、辞書の列にする。**"""
    rows = []
    for line in captured.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _link() -> "edge.Link":
    return edge.Link("127.0.0.1", 0)


# ---------------------------------------------------------------------------
# 待ち受けと、切れていないこと。
# ---------------------------------------------------------------------------


def test_nobody_has_dialled_so_the_frame_says_nobody():
    """⛔ **開けないのではない。誰も dial していない。** ⚠️ **その2つを混ぜない。**"""
    link = _link()
    try:
        assert link.fd() is None
        assert link.alive() is False
        assert edge.send_frame_and_read(link, "\n{}\n") == (False, None, "nobody")
    finally:
        link.close()


def test_the_link_takes_one_board_and_names_who():
    """⚠️ **誰が来たかを残す。** ⛔ **名前の無い接続は、切れたときに言えない。**"""
    link = _link()
    board = _dial(link)
    try:
        assert link.peer.startswith("127.0.0.1:")
        assert link.fd() is not None
        assert link.alive() is True
    finally:
        board.stop()
        link.close()


def test_alive_comes_back_without_letting_a_byte_go():
    """⛔ **`MSG_PEEK` は1バイトも食べない。** 食べれば、判定も姿勢も消える。

    ⚠️ **これが `alive()` の唯一の要件である。** `recv()` で確かめる実装は、
    **確かめた瞬間に、確かめたものを捨てる。**
    """
    link = _link()
    board = _dial(link)
    try:
        board._say("frame: light=warm face=happy gesture=none sound=none\n")
        # ⚠️ **まず、届いたことを確かめる。** ⛔ **`alive()` では届いたことを測れない**
        #    ——空のソケットも「切れていない」ので `True` を返す（それが正しい）。
        ready, _, _ = select.select([link.fd()], [], [], WAIT)
        assert ready, "答えが届かなかった"
        for _ in range(3):
            assert link.alive() is True
        # ⚠️ **まだ全部そこに在る。**
        assert os.read(link.fd(), 4096) == (
            b"frame: light=warm face=happy gesture=none sound=none\n")
    finally:
        board.stop()
        link.close()


def test_a_second_board_replaces_the_first():
    """⛔ **体は1つである。** 2本目が来たら、前の1本は畳まれる。"""
    link = _link()
    first = _dial(link)
    try:
        # ⚠️ **fd の番号では測れない**——閉じた番号は、次の接続に使い回される。
        #    測るのは**誰が繋がっているか**であり、向こうから見た**閉じたこと**である。
        first_peer = link.peer
        second = _dial(link, previous=first_peer)
        try:
            assert link.peer != first_peer
            # ⚠️ **前の1本は、向こうから見て閉じている**（EOF）。
            first.connection.settimeout(WAIT)
            assert first.connection.recv(16) == b""
        finally:
            second.stop()
    finally:
        first.stop()
        link.close()


def test_dropped_is_the_same_as_never_dialled():
    link = _link()
    board = _dial(link)
    try:
        link.drop()
        assert link.fd() is None
        assert link.alive() is False
        assert edge.send_frame_and_read(link, "\n{}\n") == (False, None, "nobody")
    finally:
        board.stop()
        link.close()


# ---------------------------------------------------------------------------
# 枠も姿勢も、同じ fd の上を通る。
# ---------------------------------------------------------------------------


def test_a_frame_over_the_link_is_read_back_from_the_same_socket():
    """✅ **枠は、ソケットの上で端末と同じに振る舞う**——`sent` と `accepted` が別である。"""
    link = _link()
    board = _dial(link)
    try:
        sent, accepted, why = edge.send_frame_and_read(
            link, '\n{"face":"happy","gesture":null,'
                  '"light":"warm","sound":null}\n')
        assert (sent, accepted, why) == (True, True, None)
        assert board.frames and board.frames[0].startswith('{"face":"happy"')
    finally:
        board.stop()
        link.close()


def test_a_board_that_says_nothing_is_null_and_not_a_refusal():
    """⛔ **`accepted: null` は「断られた」ではない。** ⚠️ **2つの失敗を1つにしない。**

    ⚠️ **窓は `PORT_WAIT` で閉じる。** この検査は**その0.5秒を払う**——
    **払わなければ、沈黙が沈黙であることを測れない。**
    """
    link = _link()
    connection = socket.create_connection(
        ("127.0.0.1", int(link.address.rsplit(":", 1)[1])), timeout=WAIT)
    try:
        select.select([link.listener], [], [], WAIT)
        assert link.accept() is not None
        # ⚠️ **何も言わない基板。** 読むが、答えない。
        sent, accepted, why = edge.send_frame_and_read(link, "\n{}\n")
        assert (sent, accepted, why) == (True, None, None)
    finally:
        connection.close()
        link.close()


def _until_settled(neck: "edge.Neck", at: float) -> float:
    """**流れが終わり、判定の窓も閉じるまで、期限ごとに起こす。**"""
    t = at
    while neck.deadline is not None or neck._fd is not None:
        neck.pump(t)
        t += edge.gestures.DEFAULT_PERIOD
        assert t < at + 30.0, "流れが終わらない"
    return t


def test_the_neck_does_not_close_the_link_and_the_next_gesture_reuses_it():
    """⛔ **このファイルでいちばん危うい規則である。**

    首は身振りの終わりに fd を忘れるが、**`Link` の fd は閉じない。**
    閉じれば、**1つの身振りが接続を畳む**——そして次の枠は `nobody` になる。
    ⇒ **2つの身振りを、1本の接続の上で通す。**
    """
    link = _link()
    board = _dial(link)
    try:
        neck = edge.Neck(link)
        room = Room()

        at = 1.2
        assert neck.take(room.offer("main", "PermissionRequest", at), at) is True
        assert board.queries == 1
        _until_settled(neck, at)

        # ⛔ **fd は生きている。** 首は忘れたが、`Link` は持っている。
        assert link.fd() is not None
        assert link.alive() is True
        os.fstat(link.fd())

        # ⚠️ **2つ目の身振りは、開き直さない**——同じ接続の上で尋ねる。
        second = at + 4.0
        assert neck.take(room.offer("main", "PermissionRequest", second),
                         second) is True
        assert board.queries == 2
        _until_settled(neck, second)

        assert board.poses, "姿勢の行が1行も届いていない"
        assert link.fd() is not None
        assert link.alive() is True
    finally:
        board.stop()
        link.close()


def test_a_link_with_nobody_on_it_leaves_the_gesture_to_the_board():
    """⛔ **知らない位置を始点にしない。** ⚠️ **待ち受けているが、誰も居ない**——
    これは「開けない端末」と同じ形であり、**枠が身振りを運ぶ。**
    """
    link = _link()
    try:
        neck = edge.Neck(link)
        at = 1.2
        assert neck.take(Room().offer("main", "PermissionRequest", at), at) is False
        assert neck._fd is None
    finally:
        link.close()


# ---------------------------------------------------------------------------
# 住所の読み方と、2つの行き先を同時に名指さないこと。
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ("192.168.0.103:3333", ("192.168.0.103", 3333)),
        ("0.0.0.0:3333", ("0.0.0.0", 3333)),
        ("127.0.0.1:0", ("127.0.0.1", 0)),
    ],
)
def test_the_address_is_read_as_two_values(text, expected):
    assert next_edge.parse_listen(text) == expected


@pytest.mark.parametrize("text", ["", "3333", "host:", ":3333", "host:port"])
def test_an_address_that_is_not_two_values_is_refused(text):
    with pytest.raises(ValueError):
        next_edge.parse_listen(text)


def test_two_ways_to_the_same_body_are_refused_before_anything_is_bound(tmp_path):
    """⛔ **片方は必ず読まれない。** ⇒ **ソケットを束縛する前に断る。**

    ⚠️ **断りが先である理由**: 束縛した後で断れば、**片付ける道が増える**——
    そして増えた道のうち、通らないものが残る。
    """
    socket_path = tmp_path / "next.sock"
    assert next_edge.main([
        "--socket", str(socket_path),
        "--port", "/dev/null",
        "--listen", "127.0.0.1:0",
    ]) == 1
    assert not socket_path.exists(), "断ったのに、ソケットが作られている"


def test_a_link_waits_longer_than_a_wire(capsys):
    """⛔ **上限は、問いについてこない。**

    ⚠️ **これは 2026-10-21 の実測の再現である**: リンク越しの `bench pos` は
    **0.041〜0.861 秒**かかった。有線で測った `PORT_WAIT = 0.5` の窓では、
    **遅い側の答えが窓の外に落ちる**——その日、デーモンは2回続けて `read: ""` を残した。
    ⇒ **0.7 秒かけて答える基板を置き、位置が読めることを確かめる。**
    """
    link = _link()
    board = _dial(link, kind=SlowBoard)
    try:
        neck = edge.Neck(link)
        at = 1.2
        assert neck.take(Room().offer("main", "PermissionRequest", at), at) is True
        # ⚠️ **窓は、開いたときに決まる**——道なら 0.5 / 1.5、リンクなら 1.5 / 3.0。
        assert neck._probe_wait == edge.LINK_WAIT
        assert neck._verdict_wait == edge.LINK_VERDICT_WAIT

        heard = [r for r in _rows(capsys.readouterr().out) if "position" in r]
        assert heard, "探針の行が無い"
        assert heard[0]["heard"] is True, f"答えが窓の外に落ちた: {heard[0]}"
        # ⚠️ **数そのものは、このファイルの主題ではない**（`readback` が読む）。
        #    ここで測るのは**読めたこと**——窓の中で答えたことである。
        assert heard[0]["position"] is not None, heard[0]
    finally:
        board.stop()
        link.close()


def test_a_wire_keeps_the_wait_it_was_measured_with(tmp_path):
    """⚠️ **有線の 0.5 秒は、そのままである。** ⛔ **測った値の側を動かさない。**"""
    port = tmp_path / "console"
    port.touch()
    assert edge.Neck(str(port))._probe_wait == edge.PORT_WAIT
    assert edge.Neck(None)._probe_wait == edge.PORT_WAIT
    assert edge.Neck(str(port))._verdict_wait == edge.VERDICT_WAIT
    assert edge.Neck(None)._verdict_wait == edge.VERDICT_WAIT


# ---------------------------------------------------------------------------
# 回線へ、行ではないものを書く（声、2026-10-21）。
# ---------------------------------------------------------------------------


class Ears(Board):
    """**バイトを、そのまま溜める基板。** ⛔ **行に割らない。**

    ⚠️ 音声の塊は行ではない——`audio <n>` のあとの n バイトの中の 0x0A は改行でなく、
    **行に割る読み方では、塊が1行ずつに砕ける**（`audio_line.h`）。
    """

    def __init__(self, connection: socket.socket) -> None:
        super().__init__(connection)
        self.data = bytearray()

    def run(self) -> None:
        self.connection.settimeout(WAIT)
        while not self._done.is_set():
            try:
                chunk = self.connection.recv(4096)
            except OSError:
                return
            if not chunk:
                return
            self.data += chunk

    def take(self, count: int) -> bytes:
        """**`count` バイトが届くまで待ち、渡す。** ⚠️ 届かなければ空である。"""
        deadline = time.monotonic() + WAIT
        while len(self.data) < count and time.monotonic() < deadline:
            time.sleep(0.01)
        got = bytes(self.data[:count])
        del self.data[:count]
        return got


def test_a_block_goes_down_the_link_byte_for_byte():
    """⛔ **行ではなく、バイトである。** ⚠️ **1バイトも変えない、1バイトも足さない。**

    ⚠️ **`0x0a` を塊の中に入れてある**——頭のあとの標本の1バイトが改行でありうる
    ことを、この試験は固定する。**行として書けば、そこで切れる。**
    """
    from projects.stackchan.voice import pcm

    link = _link()
    board = _dial(link, kind=Ears)
    try:
        payload = pcm.head(8) + b"\x0a\x00\x0d\xff\x0a\x0a\x0d\x00"
        assert link.send(payload) is True
        assert board.take(len(payload)) == payload
        assert link.broken is False
    finally:
        board.stop()
        link.close()


def test_send_with_nobody_on_the_link_is_false_and_not_broken():
    """⛔ **誰も居ないことは、壊れたことではない。** ⚠️ **2つを混ぜない。**"""
    link = _link()
    try:
        assert link.send(b"audio 2\n\x00\x00") is False
        assert link.broken is False
    finally:
        link.close()


def test_a_board_that_let_go_makes_the_next_send_broken():
    """⛔ **塊の途中で書けなくなったら、その回線は捨てる。**

    ⚠️ **ここでは閉じない**——`broken` を立てるだけである。閉じるのは `serve` の糸で
    あり、**2つの糸が同じ fd を閉じれば、番号が再利用されて別のファイルへ書く。**
    """
    link = _link()
    board = _dial(link)
    try:
        board.stop()  # 向こうから切れる
        for _ in range(20):
            if not link.send(b"audio 2\n\x00\x00"):
                break
            time.sleep(0.02)
        assert link.send(b"audio 2\n\x00\x00") is False
        assert link.broken is True
    finally:
        link.close()


def test_the_neck_and_the_voice_write_through_one_lock():
    """⛔ **書き手は2人である。** 錠が別なら、**塊の真ん中に姿勢の1行が入る。**

    ⚠️ **同じ物であることを、`is` で測る**——「どちらも錠を持っている」では、
    **2つの錠を持っていても通る。**
    """
    link = _link()
    board = _dial(link)
    try:
        neck = edge.Neck(link)
        assert neck._open() is True
        try:
            assert neck._lock is link.writing
        finally:
            neck._close()
        # ⚠️ **離した後は持たない。** 次の身振りが、繋がっていない回線の錠を取らない。
        assert neck._lock is None
    finally:
        board.stop()
        link.close()


def test_two_writers_do_not_mix_their_bytes():
    """⚠️ **1回の `send` は、割り込まれない。** それだけを約束する。

    ⛔ **約束しないこと**: 2つの糸のあいだの順序。**塊と塊のあいだは自由である**——
    塊はそれぞれ頭を持つので、順序が入れ替われば音が入れ替わるだけで、
    **頭と標本の境目は動かない。**
    """
    link = _link()
    board = _dial(link, kind=Ears)
    try:
        first = b"A" * 256
        second = b"B" * 256
        count = 4

        def write(payload: bytes) -> None:
            for _ in range(count):
                assert link.send(payload) is True

        threads = [threading.Thread(target=write, args=(first,)),
                   threading.Thread(target=write, args=(second,))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=WAIT)

        got = board.take(len(first) * count * 2)
        assert len(got) == len(first) * count * 2
        # ⚠️ **256バイトの窓は、どれも1人のものである。**
        windows = {got[i:i + 256] for i in range(0, len(got), 256)}
        assert windows == {first, second}, "2人のバイトが混ざった"
    finally:
        board.stop()
        link.close()
