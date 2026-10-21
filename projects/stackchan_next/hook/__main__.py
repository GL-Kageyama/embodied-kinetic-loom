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

⛔ **返事を読むのは `UserPromptSubmit` の1つだけである**（設計 §12.1）——
**ユーザーが次に喋った瞬間が、いちばん静かな渡し場である。** 他の32の事象は
送って閉じるだけであり、**読めばターンがデーモンの速さを待つことになる。**
⚠️ **何も印字しない。** ただし `UserPromptSubmit` で監修の `context` が返った
ときだけ、`hookSpecificOutput.additionalContext` の1行を印字する。
⚠️ **どの失敗でも 0 で終わる。** デーモンが居ないことは、フックの失敗ではない。
⛔ **体のソケットの送信が失敗しても、メタへは送る**——**監修は体の故障に
道連れにされない。**
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys

from projects.stackchan.daemon.room import CLIENT_TIMEOUT
from projects.stackchan.hook.__main__ import read_payload

from ..client import REPLY_EVENT, line_from, reads_reply
from ..daemon.room import meta_socket_path, socket_path


def default_socket() -> str:
    """⚠️ **綴りは `room.socket_path` に1つだけ在る**——向こうのではなく、こちらの。"""
    return socket_path(os.getuid())


def default_meta_socket() -> str:
    """⚠️ **綴りは `room.meta_socket_path` に1つだけ在る**——2本目の戸口である。"""
    return meta_socket_path(os.getuid())


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
    parser.add_argument("--meta-socket", default=default_meta_socket(),
                        metavar="PATH",
                        help="the meta socket (default: %(default)s)")
    return parser


def send_line(path: str, line: str, *, read: bool) -> bytes | None:
    """**1行を送り、求められたときだけ返事を1行読む。** ⛔ **失敗は `None` である。**

    ⚠️ **待ちの上限は `CLIENT_TIMEOUT` のままである**（100ms）。メタの糸は
    数を数えて即答する（実測 0.016ms）ので、これは**遅い日を捨てるための余裕**
    であって、見込みの待ちではない（設計 §12.1）。

    ⚠️ **返事は改行までである。** メタの縁は1行を `reply` で書く——**複数行を
    読む形にすると、答えない糸の上で待ちが延びる。**
    """
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(CLIENT_TIMEOUT)
    try:
        connection.connect(path)
        connection.sendall(line.encode("utf-8"))
        # ⛔ **読まない経路で `recv` を呼ばない。** 呼べば、答えないデーモンが
        #    いるだけでターンが100ms待つ——32の事象すべてで。
        if not read:
            return None
        chunks = b""
        while b"\n" not in chunks:
            chunk = connection.recv(4096)
            if not chunk:
                break
            chunks += chunk
        return chunks.partition(b"\n")[0]
    except OSError:
        # ⚠️ **デーモンが居ない・詰まっている・ソケットが古い。** どれも捨てる。
        return None
    finally:
        connection.close()


def context_of(answer: bytes | None) -> str | None:
    """**返事から `context` を取り出す。** ⛔ **空も、無いも、同じ「言わない」である。**"""
    if not answer:
        return None
    try:
        payload = json.loads(answer)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    said = payload.get("context")
    return said if isinstance(said, str) and said else None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    line = line_from(read_payload(sys.stdin.buffer))
    if line is None:
        return 0

    # 1. 体へ。⛔ **失敗しても、メタへは送る**——監修は体の故障に道連れにされない。
    send_line(args.socket, line, read=False)

    # 2. メタへ。⛔ **33の事象すべてを送る**——**規則はターンを数えるのであり、
    #    プロンプトだけでは、ターンは1つも閉じない**（`Stop` が来ず、道具も数えられず、
    #    3語のどれも鳴らない）。⚠️ **返事を読むのはプロンプトのときだけである。**
    said = context_of(send_line(args.meta_socket, line, read=reads_reply(line)))
    if said is None:
        return 0

    # ⚠️ **印字するのは、この1行だけである。** フックの出力はターンの一部になる。
    sys.stdout.write(json.dumps(
        {"hookSpecificOutput": {"hookEventName": REPLY_EVENT,
                                "additionalContext": said}},
        ensure_ascii=False,
    ) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
