# -*- coding: utf-8 -*-
"""**Pi で走る口。** `python3 -m projects.stackchan_pi --upstream <Mac>`

⛔ **ソケットを作るのは、この入口だけである。** `projects/` の決定論を守る検査が
`socket` を禁じている（`tools/purity.py`）——**規則は `relay.py` に、配線はここに。**

⚠️ **これは道具であり、判断ではない。** ここが持つ数は住所と待ち時間だけで、
**顔も光も身振りも1つも知らない。**
"""

from __future__ import annotations

import argparse
import signal
import socket
import sys
import threading
from typing import Iterable, Optional, Tuple

from .relay import (
    CONNECT_SECONDS,
    GREETING_SECONDS,
    candidates,
    greeting_line,
    is_loom,
    pump,
    read_greeting,
)


def own_addresses(probe: str, port: int) -> set:
    """**この機械の住所。** ⛔ **掃き出しの候補から外すために要る。**

    ⚠️ **橋は、自分が待ち受けている /24 を掃く。** 除かなければ、掃き出しは
    **自分自身の 3333 を掴み**、そのセッションがまた上流を探す——**入れ子になる。**
    ⛔ **基板の `dial_scan` には要らない。** 基板は 3333 を待ち受けていない。

    ⚠️ **UDP の `connect` はパケットを1つも送らない。** 経路を選ばせて、
    その経路の自分の住所を読むだけである——**上流が居なくても答える。**
    """
    found = {"127.0.0.1"}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((probe, port))
            found.add(sock.getsockname()[0])
        finally:
            sock.close()
    except OSError:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(info[4][0])
    except OSError:
        pass
    return found


def connect_upstream(addresses: Iterable[str], port: int,
                     *, connect_seconds: float = CONNECT_SECONDS,
                     greeting_seconds: float = GREETING_SECONDS
                     ) -> Optional[Tuple[socket.socket, bytes]]:
    """**名乗った最初の住所と、その名乗りを返す。** 名乗らなければ `None`。

    ⛔ **名乗りを確かめない接続は、この関数の外でも作らない。** 3333 を持つ
    何者でも体を動かしてよいなら、掃き出しは要らない——要るのは、
    **名乗りという1つの条件**である。

    ⛔ **名乗りを返すのは、捨てないためである。** 基板も `loom` を待っている——
    **確かめて捨てれば、基板は「名乗らなかった」と判断する**（2026-11-13 の実測）。
    """
    for address in addresses:
        sock = socket.socket()
        sock.settimeout(connect_seconds)
        try:
            sock.connect((address, port))
            sock.settimeout(greeting_seconds)
            line = read_greeting(sock)
            if not is_loom(line):
                sock.close()
                continue
            sock.settimeout(None)
            return sock, line
        except OSError:
            try:
                sock.close()
            except OSError:
                pass
    return None


def bridge_once(board: socket.socket, upstream: socket.socket) -> None:
    """**1本のセッション。** どちらかが終われば、両方を閉じる。"""
    back = threading.Thread(target=pump, args=(upstream, board), daemon=True)
    back.start()
    pump(board, upstream)
    back.join(timeout=2.0)
    for sock in (board, upstream):
        try:
            sock.close()
        except OSError:
            pass


def session(board: socket.socket, addresses: Iterable[str], upstream_port: int,
            *, on_event=None) -> str:
    """**1本の下流を、1本の上流に繋ぐ。** 返り値は `"dropped"` か `"closed"`。

    ⛔ **上流が無ければ、下流を閉じる。** 閉じなければ、体は眠れない——
    `sleep_rule.h` は在席の信号をリンクそのものに置いている。
    """
    found = connect_upstream(addresses, upstream_port)
    if found is None:
        try:
            board.close()
        except OSError:
            pass
        if on_event is not None:
            on_event("upstream-missing", None)
        return "dropped"
    upstream, greeting = found
    if on_event is not None:
        try:
            on_event("upstream", upstream.getpeername())
        except OSError:
            on_event("upstream", None)
    # ⛔ **名乗りを基板へ渡す。** 橋が読んだ1行は、検査のためだけでなく、
    # **この接続がどのホストのものかを基板に告げる1行**でもある。
    # 2026-11-13、これを捨てて基板は `did not greet — not this host` と答えた。
    try:
        board.sendall(greeting_line(greeting))
    except OSError:
        for sock in (board, upstream):
            try:
                sock.close()
            except OSError:
                pass
        return "closed"
    bridge_once(board, upstream)
    return "closed"


def serve(listen: str, port: int, known_upstream: str, upstream_port: int,
          *, sweep: bool = True, on_event=None, stop=None) -> None:
    """**待ち受け続ける。** 1本ずつ。

    ⚠️ **1本ずつでよい。** デーモンの `Link.accept` は1本しか持たず、2本目は
    1本目を追い出す——**橋が2本持てば、橋だけが2本持つことになる。**
    """
    if sweep:
        exclude = own_addresses(known_upstream, upstream_port)
        if listen not in ("0.0.0.0", ""):
            exclude.add(listen)
        addresses = candidates(known_upstream, exclude=exclude)
    else:
        addresses = [known_upstream]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((listen, port))
    server.listen(1)
    if stop is not None:
        # ⚠️ `accept` で固まったまま止まれない橋は、止められない橋である。
        server.settimeout(0.5)
    try:
        while True:
            try:
                board, peer = server.accept()
            except socket.timeout:
                if stop is not None and stop.is_set():
                    return
                continue
            if on_event is not None:
                on_event("downstream", peer)
            session(board, addresses, upstream_port, on_event=on_event)
            if on_event is not None:
                on_event("closed", peer)
    finally:
        try:
            server.close()
        except OSError:
            pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="projects.stackchan_pi",
        description="Mac（上流）と基板（下流）のあいだを、バイトのまま通す。")
    parser.add_argument("--listen", default="0.0.0.0",
                        help="下流を待つ住所（既定 0.0.0.0）")
    parser.add_argument("--port", type=int, default=3333,
                        help="下流のポート（既定 3333）")
    parser.add_argument("--upstream", default="10.10.10.38",
                        help="上流の名指しの住所。最初に試す（既定 10.10.10.38）")
    parser.add_argument("--upstream-port", type=int, default=3333,
                        help="上流のポート（既定 3333）")
    parser.add_argument("--no-sweep", action="store_true",
                        help="名指しの住所だけを試す（掃き出さない）")
    args = parser.parse_args(argv)

    stop = threading.Event()

    def on_signal(_signum, _frame):
        stop.set()

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    def on_event(kind, value):
        print("bridge: %s %s" % (kind, value), flush=True)

    print("bridge: listening on %s:%d, upstream %s:%d%s"
          % (args.listen, args.port, args.upstream, args.upstream_port,
             "" if not args.no_sweep else " (no sweep)"), flush=True)
    serve(args.listen, args.port, args.upstream, args.upstream_port,
          sweep=not args.no_sweep, on_event=on_event, stop=stop)
    print("bridge: stopped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
