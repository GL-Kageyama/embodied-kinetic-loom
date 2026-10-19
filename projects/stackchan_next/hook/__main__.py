# -*- coding: utf-8 -*-
"""**フックが呼ぶ入口（新しい層）。** `python3 -m projects.stackchan_next.hook`
（リポジトリの根から）。

⛔ **これは縁である。** 標準入力とソケットを読む——**判定はしない。**
組み直しは `projects.stackchan_next.client.line_from`（純粋）に在り、刻むのは
デーモンである。

⚠️ **既存の縁の写しではない。** 読む・送る・黙って0で終わる、という3つは
そのままである。違いは**どの行を組み立てるか**と**どの戸口へ送るか**の2点であり、
それは2つの import に現れている。⇒ **`read_payload` は向こうから借りる**
——**同じ規則を2つ持てば、片方が黙って緩んだ日に、もう片方が鳴らない。**

⛔ **返事を読まない。** 送って閉じるだけである——**読めば、ターンがデーモンの
速さを待つことになる。**
⚠️ **何も印字しない。** フックの出力はターンの一部になりうる。
⚠️ **どの失敗でも 0 で終わる。** デーモンが居ないことは、フックの失敗ではない。
"""
from __future__ import annotations

import argparse
import os
import socket
import sys

from projects.stackchan.daemon.room import CLIENT_TIMEOUT
from projects.stackchan.hook.__main__ import read_payload

from ..client import line_from
from ..daemon.room import socket_path


def default_socket() -> str:
    """⚠️ **綴りは `room.socket_path` に1つだけ在る**——向こうのではなく、こちらの。"""
    return socket_path(os.getuid())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m projects.stackchan_next.hook",
        description=(
            "Read one hook event from stdin and send one line to the second "
            "daemon. Silent, and exits 0 whatever happens."
        ),
    )
    parser.add_argument("--socket", default=default_socket(), metavar="PATH",
                        help="the daemon's Unix socket (default: %(default)s)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    line = line_from(read_payload(sys.stdin.buffer))
    if line is None:
        return 0

    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(CLIENT_TIMEOUT)
    try:
        connection.connect(args.socket)
        connection.sendall(line.encode("utf-8"))
    except OSError:
        # ⚠️ **デーモンが居ない・詰まっている・ソケットが古い。** どれも捨てる。
        return 0
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
