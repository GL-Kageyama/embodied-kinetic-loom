# -*- coding: utf-8 -*-
"""**Pi の口（`projects/stackchan_pi/`）。**

⚠️ **純粋な2つ（`candidates` / `is_loom`）は、ソケット越しに問わない。**
⛔ **ソケット越しにしか問えない規則は、規則ではなく配線である。**
⚠️ **ソケットを作るのは入口（`__main__.py`）だけである**——`relay.py` は
`socket` を輸入しない（`tests/test_pet_purity.py` が鳴る）。⇒ **接続の検査は
入口から問う。**

⚠️ **順序の7つは `tests/test_stackchan_dial_scan.py` と同じ7つである。**
⛔ **同じ順序が2か所に写っている**——片方だけ変えれば、体と橋が別の住所を歩く。
"""

import socket
import threading

import pytest

from projects.stackchan_pi import __main__ as edge
from projects.stackchan_pi import relay


# ---------------------------------------------------------------------------
# 掃き出し。⚠️ **基板の `main/dial_scan.cpp` と同じ順序である。**
# ---------------------------------------------------------------------------


def test_the_named_address_is_tried_first():
    """⛔ **名指しした住所を、最初に試す。** 掃き出しは最後の手段である。"""
    assert relay.candidates("192.168.0.103")[0] == "192.168.0.103"


def test_the_sweep_walks_outward_from_the_named_address():
    """⚠️ **`.+1`, `.-1`, `.+2`, `.-2`, …**——2つ隣へ動いたホストは3回で見つかる。

    ⚠️ 2026-10-23 の Mac は `.103` から `.106` へ動いた。この順序なら4回目である。
    """
    assert relay.candidates("192.168.0.103")[:7] == [
        "192.168.0.103",
        "192.168.0.104", "192.168.0.102",
        "192.168.0.105", "192.168.0.101",
        "192.168.0.106", "192.168.0.100",
    ]


def test_the_network_and_the_broadcast_are_not_hosts():
    """⛔ **`.0` と `.255` は住所ではない。**"""
    found = relay.candidates("192.168.0.103")
    assert "192.168.0.0" not in found
    assert "192.168.0.255" not in found


def test_every_host_of_the_slash_twenty_four_appears_once():
    """⚠️ **254 = 256 - `.0` - `.255`。** 数え上げなので、数そのものを確かめる。"""
    found = relay.candidates("192.168.0.103")
    assert len(found) == 254
    assert len(set(found)) == 254


def test_a_string_that_is_not_an_address_sweeps_nothing():
    """⛔ **名指しが住所でなければ、1つも返さない。** 勝手に歩き出さないためである。"""
    for text in ("", "loom", "192.168.0", "192.168.0.103x", "192.168.0.300",
                 "192.168.0.1.2", "192.168..1", "+192.168.0.1",
                 " 192.168.0.1", "192.168.0.+1"):
        assert relay.candidates(text) == [], "%r で歩き出した" % (text,)


def test_the_walk_survives_both_ends_of_the_subnet():
    """⚠️ **端の住所でも、範囲の外へ出ない。**"""
    found = relay.candidates("192.168.0.1")
    assert found[:3] == ["192.168.0.1", "192.168.0.2", "192.168.0.3"]
    assert "192.168.0.0" not in found
    found = relay.candidates("192.168.0.254")
    assert found[:2] == ["192.168.0.254", "192.168.0.253"]
    assert "192.168.0.255" not in found


def test_the_greeting_is_given_back_to_the_board():
    """⛔ **読んだ1行を、捨てない。** 2026-11-13 の実機が教えた穴である。

    ⚠️ **橋が名乗りを消費したら、基板はこう答えた**:
    `dial: 192.168.0.104:3333 did not greet — not this host`
    ——**基板も `loom` を待っている。** 名乗りは検査のためだけでなく、
    **この接続がどのホストのものかを告げる1行**である。
    """
    assert relay.greeting_line(b"loom") == b"loom\n"


def test_the_shut_wr_constant_is_the_one_the_socket_module_uses():
    """⛔ **`relay.SHUT_WR` は写しである。** `socket` を輸入できないので手で置いた。

    ⚠️ **写しが本物と違えば、`pump` は黙って何もしない**——`shutdown` に 1 以外を
    渡せば `OSError` になり、それは `pump` が飲む。**だからここで問う。**
    """
    assert relay.SHUT_WR == socket.SHUT_WR


def test_the_limit_cuts_the_list_and_not_the_order():
    """⚠️ **上限は末尾を切る。** 先頭が変わるなら、名指しは最初でなくなる。"""
    found = relay.candidates("192.168.0.103", limit=3)
    assert found == ["192.168.0.103", "192.168.0.104", "192.168.0.102"]


# ---------------------------------------------------------------------------
# 名乗り。⛔ **なければ、3333 を持つ何者でも体を動かす。**
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("line", [b"loom", b"loom ", b"loom stackchan", b"loom\tx"])
def test_the_hosts_greeting_is_a_loom_word(line):
    """✅ **ホストは `loom` を最初の1行に書く**（`Link.accept`）。"""
    assert relay.is_loom(line) is True


@pytest.mark.parametrize("line", [b"", b"loomish", b" loom", b"LOOM", b"hello", b"loomx", b"loo"])
def test_another_word_is_not_this_host(line):
    """⛔ **接頭辞では一致させない。** `loomish` を名乗る何かは、このホストではない。"""
    assert relay.is_loom(line) is False


def test_an_empty_greeting_is_not_a_greeting():
    """⛔ **空の名乗りは名乗りではない。** 相手が黙って閉じたときと同じ扱いにする。"""
    assert relay.is_loom(b"") is False


# ---------------------------------------------------------------------------
# 1行の読み。⛔ **改行を含めて渡せば、正しい名乗りが1つも通らなくなる。**
# ---------------------------------------------------------------------------


def test_the_greeting_is_read_without_its_newline():
    """⚠️ `is_loom` は改行を受け付けない——**だから読む側が落とす。**"""
    mac, bridge = socket.socketpair()
    try:
        mac.sendall(b"loom\n")
        assert relay.read_greeting(bridge) == b"loom"
    finally:
        mac.close()
        bridge.close()


def test_a_silent_peer_ends_the_read_with_what_it_said():
    """⚠️ **相手が黙って閉じれば、読んだところで終わる。** 待ち続けない。"""
    mac, bridge = socket.socketpair()
    try:
        mac.sendall(b"loom")
        mac.close()
        assert relay.read_greeting(bridge) == b"loom"
    finally:
        bridge.close()


def test_a_peer_that_never_sends_a_newline_is_cut_at_the_limit():
    """⛔ **上限で切る。** 名乗らない相手が無限に喋れば、橋はそこで止まる。"""
    mac, bridge = socket.socketpair()
    try:
        mac.sendall(b"x" * 500)
        line = relay.read_greeting(bridge)
        assert len(line) == relay.GREETING_MAX
    finally:
        mac.close()
        bridge.close()


# ---------------------------------------------------------------------------
# 通し。⚠️ **バイトを変えない。**
# ---------------------------------------------------------------------------


def test_pump_carries_the_bytes_unchanged():
    """⛔ **橋はバイトを読み替えない。** 枠も姿勢も音声も、同じバイトで渡る。"""
    a, b = socket.socketpair()
    c, d = socket.socketpair()
    try:
        thread = threading.Thread(target=relay.pump, args=(a, c), daemon=True)
        thread.start()
        payload = b'{"face":"curious"}\n\x00\xff' * 100
        b.sendall(payload)
        b.shutdown(socket.SHUT_WR)
        got = bytearray()
        while True:
            chunk = d.recv(65536)
            if not chunk:
                break
            got += chunk
        thread.join(timeout=2.0)
        assert bytes(got) == payload
    finally:
        for sock in (a, b, c, d):
            sock.close()


def test_pump_ends_when_the_source_ends():
    """⚠️ **源が終われば、流しも終わる。** 残り続けるスレッドは、閉じた fd を持つ。"""
    a, b = socket.socketpair()
    c, d = socket.socketpair()
    try:
        done = threading.Event()

        def run():
            relay.pump(a, c)
            done.set()

        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        b.close()
        assert done.wait(timeout=2.0) is True
    finally:
        for sock in (a, c, d):
            sock.close()


# ---------------------------------------------------------------------------
# 上流を選ぶ。⛔ **名乗らない住所は、通さない。**
# ---------------------------------------------------------------------------


class FakeHost:
    """⚠️ **`loom` と言う者と、言わない者。** どちらも 3333 を持ちうる。"""

    def __init__(self, greeting):
        self.greeting = greeting
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self.seen = []
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            if self.greeting is None:
                conn.close()
                continue
            try:
                conn.sendall(self.greeting)
            except OSError:
                pass
            self.seen.append(conn)

    def close(self):
        self.sock.close()
        for conn in self.seen:
            try:
                conn.close()
            except OSError:
                pass


def test_a_host_that_says_loom_is_taken():
    """✅ **名乗った相手を返す。** ⛔ **名乗りも一緒に返す**——捨てるためではない。"""
    host = FakeHost(b"loom\n")
    try:
        found = edge.connect_upstream(["127.0.0.1"], host.port)
        assert found is not None
        sock, greeting = found
        assert greeting == b"loom"
        sock.close()
    finally:
        host.close()


def test_a_host_that_says_another_word_is_left_alone():
    """⛔ **`hello` と言う 3333 は、このホストではない。** 閉じて次へ行く。"""
    host = FakeHost(b"hello\n")
    try:
        assert edge.connect_upstream(["127.0.0.1"], host.port) is None
    finally:
        host.close()


def test_a_host_that_says_nothing_is_left_alone():
    """⛔ **黙る相手も通さない。** 名乗りが条件である。"""
    host = FakeHost(None)
    try:
        assert edge.connect_upstream(["127.0.0.1"], host.port) is None
    finally:
        host.close()


def test_the_sweep_takes_the_second_address_when_the_first_is_silent():
    """✅ **名指しが黙っていれば、次を試す。** 掃き出しの目的はこれだけである。"""
    host = FakeHost(b"loom\n")
    try:
        # ⚠️ `.1` はこの機械では誰も待っていない——閉じたポートは即座に断る。
        found = edge.connect_upstream(["127.0.0.0", "127.0.0.1"], host.port)
        assert found is not None
        found[0].close()
    finally:
        host.close()


# ---------------------------------------------------------------------------
# セッション。⛔ **上流が無ければ、下流を閉じる**（裁定3）。
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 自分自身を掴まない。⛔ **橋は自分が待ち受けている /24 を掃く。**
# ---------------------------------------------------------------------------


def test_the_sweep_never_includes_the_bridge_itself():
    """⛔ **自分を掴めば、入れ子になる。**

    掃き出しが自分の 3333 に繋がれば、そのセッションもまた上流を探す——
    **掴むたびに1本増える。** ⇒ **自分自身の住所は候補から外す。**
    """
    found = relay.candidates("10.10.10.38", exclude={"10.10.10.2"})
    assert "10.10.10.2" not in found
    assert found[0] == "10.10.10.38"
    assert len(found) == 253


def test_a_named_address_that_is_the_bridge_itself_is_dropped_and_the_rest_walked():
    """⛔ **名指しが自分なら、名前だけ落とす。** 掃き出しは「名指しが違う」ための手段である。

    ⇒ **自分を掴まないことと、歩かないことは別である。**
    """
    found = relay.candidates("10.10.10.2", exclude={"10.10.10.2"})
    assert "10.10.10.2" not in found
    assert found[0] == "10.10.10.3"
    assert len(found) == 253


def test_the_exclusion_does_not_change_the_order_of_the_rest():
    """⚠️ **除いた分だけ詰める。** 順序が動けば、2つ隣のホストは3回で見つからない。"""
    found = relay.candidates("192.168.0.103", exclude={"192.168.0.104"})
    assert found[:6] == [
        "192.168.0.103",
        "192.168.0.102", "192.168.0.105",
        "192.168.0.101", "192.168.0.106",
        "192.168.0.100",
    ]


def test_the_bridge_knows_at_least_one_of_its_own_addresses():
    """✅ **自分の住所を名乗る。** ⚠️ 除く側が空なら、この防ぎは何もしない。"""
    found = edge.own_addresses("127.0.0.1", 3333)
    assert "127.0.0.1" in found


def test_a_session_without_an_upstream_closes_the_board():
    """⛔ **閉じなければ、体は眠れない。**

    `sleep_rule.h` は在席の信号をリンクそのものに置いている——**繋いだまま
    黙る橋は「誰かが居る」と言い続ける。**
    """
    board, other = socket.socketpair()
    try:
        result = edge.session(board, ["127.0.0.0"], 1)
        assert result == "dropped"
        # ⚠️ 反対側から見て、閉じたことが分かる。
        other.settimeout(2.0)
        assert other.recv(1) == b""
    finally:
        other.close()


def test_a_session_carries_the_frame_and_the_answer_back():
    """✅ **1本のセッションで、枠が下り、受理が上る。** 段1の実測と同じ形である。"""
    mac = socket.socket()
    mac.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    mac.bind(("127.0.0.1", 0))
    mac.listen(1)
    port = mac.getsockname()[1]

    board, other = socket.socketpair()

    def host():
        conn, _ = mac.accept()
        conn.sendall(b"loom\n")
        line = conn.recv(4096)
        conn.sendall(line + b"<-")
        conn.close()

    thread = threading.Thread(target=host, daemon=True)
    thread.start()

    done = []

    def run_session():
        done.append(edge.session(board, ["127.0.0.1"], port))

    worker = threading.Thread(target=run_session, daemon=True)
    worker.start()

    try:
        other.settimeout(2.0)
        # ⛔ **最初に届くのは名乗りである。** 基板もこれを待っている（2026-11-13）。
        assert other.recv(4096) == b"loom\n"
        other.sendall(b'{"face":"curious"}\n')
        assert other.recv(4096) == b'{"face":"curious"}\n<-'
    finally:
        other.close()
        worker.join(timeout=3.0)
        mac.close()

    assert done == ["closed"]
