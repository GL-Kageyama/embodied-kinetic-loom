# -*- coding: utf-8 -*-
"""**フックが呼ぶ入口。** `python3 -m projects.stackchan.hook`（リポジトリの根から）。

⛔ **これは縁である。** 標準入力とソケットを読む——**判定はしない。**
組み直しは `client.line_from`（純粋）に在り、刻むのはデーモンである。

⛔ **返事を読まない。** 送って閉じるだけである——**読めば、ターンがデーモンの
速さを待つことになる。**
⚠️ **何も印字しない。** フックの出力はターンの一部になりうる。
⚠️ **どの失敗でも 0 で終わる。** デーモンが居ないことは、フックの失敗ではない。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys

from projects.stackchan.client import INPUT_LIMIT, line_from
from projects.stackchan.daemon.room import CLIENT_TIMEOUT, socket_path


def default_socket() -> str:
    """⚠️ **綴りは `room.socket_path` に1つだけ在る。**"""
    return socket_path(os.getuid())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m projects.stackchan.hook",
        description=(
            "Read one hook event from stdin and send one line to the daemon. "
            "Silent, and exits 0 whatever happens."
        ),
    )
    parser.add_argument("--socket", default=default_socket(), metavar="PATH",
                        help="the daemon's Unix socket (default: %(default)s)")
    return parser


def read_payload(stream) -> object | None:
    """**標準入力から1つの JSON を読む。** ⛔ **上限を超えたら読まずに捨てる。**"""
    try:
        raw = stream.read(INPUT_LIMIT + 1)
    except OSError:
        return None
    if len(raw) > INPUT_LIMIT:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


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
