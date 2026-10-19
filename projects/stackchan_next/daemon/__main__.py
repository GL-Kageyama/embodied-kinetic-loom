# -*- coding: utf-8 -*-
"""**新しい層の縁。** `python3 -m projects.stackchan_next.daemon`（リポジトリの根から）。

⚠️ **既存のデーモンと並走する。** 違うのは3つだけである:

1. **ソケットの綴り**（`room.socket_path`——`ekl-stackchan-next-<uid>.sock`）。
2. **要求に3語目 `work` がありうる**。
3. **判定の後ろに `Presence` が1枚いる**（`room.NextRoom`）。

⇒ **伝送路・首・枠・時計・合図・ログの形は、すべて
`projects.stackchan.daemon.__main__` から import したものである**——`bind`・
`probe`・`emit`・`deliver`・`Neck`・`send_frame_and_read`・`frame_row`。
⛔ **この層は新しい枠を作らない。** 光の語が2つ増えても、枠は枠である。

⛔ **`serve` と `handle` だけは import しない。** 理由は1つである: あちらの
`serve` は**自分自身のモジュールの `handle` を名前で呼ぶ**ので、外から別の
`handle` を差し込む口が無い。そして `handle` は要求を2語として割る（`parse_request`）。
⇒ **この2つは、ここに在る**——**写しではなく、要求の形が違うことの結果である。**
⚠️ **それ以外の行は1行も写していない**（選択・期限・合図・受理・掃除は向こうから来る）。

⚠️ **合図と bind の順序は、向こうと同じである**——**信号の受け口をソケットより
先に作る。** 2026-10-19 に一度だけ落ちた検査の順序であり、
**「ソケットが在ることは、片付けられる準備ができたことを意味する」**を真にする。

⚠️ **停止は何も送らない。** 駐機も、最後の身振りも無い——**この機体に停止命令は無い。**
"""
from __future__ import annotations

import argparse
import datetime
import os
import select
import signal
import socket
import sys
import time
from dataclasses import replace

from projects.stackchan.behaviors import Decision
from projects.stackchan.daemon.__main__ import (
    EXIT_ALREADY_RUNNING,
    RECV,
    Neck,
    bind,
    deliver,
    emit,
    reply,
)
from projects.stackchan.daemon.room import BadRequest, refusal, row
from projects.stackchan.outbound import Outbound
from projects.stackchan.quiet import is_quiet

from ..presence import DEFAULT_PRESENCE, PRESENCES
from .room import CLIENT_TIMEOUT, MAX_LINE, NextRoom, parse_request, socket_path


def default_socket() -> str:
    """**綴りは `room.socket_path` に1つだけ在る。** ⚠️ ここは uid を渡すだけである。"""
    return socket_path(os.getuid())


def decide(room: NextRoom, session: str, event: str, work: str | None, at: float,
           hour: int | None = None) -> Decision:
    """**事象1つを、部屋に渡す。** ⚠️ **静かな時間は、この縁が読む。**

    ⛔ **中核は時計を持たない**（`room.py`）。`quiet.py` の規則が**真偽として**
    渡り、**音の欄だけを閉じる**——顔も光も首も従わない。

    ⚠️ **`hour` は試験のために在る。** 渡さなければ、壁時計のローカル時を1度読む。
    """
    if hour is None:
        hour = datetime.datetime.now().hour
    return room.offer(session, event, at, quiet=is_quiet(hour), work=work)


def handle(connection: socket.socket, room: NextRoom, outbound: Outbound, neck: Neck,
           at: float) -> None:
    """**1つの接続を読む。** ⚠️ **行が届かなければ、待ち続けずに閉じる。**

    ⚠️ **向こうの `handle` との違いは2行である**——要求が3つに割れ、判定へ
    `work` が渡る。**それ以外（長さの上限・UTF-8・断りの符号・枠より先に首・
    同じ `at`）は同じである。**
    """
    connection.settimeout(CLIENT_TIMEOUT)
    buffer = b""
    while b"\n" not in buffer:
        try:
            chunk = connection.recv(RECV)
        except OSError:
            return
        if not chunk:
            return
        buffer += chunk
        if len(buffer) > MAX_LINE:
            emit(refusal("too-long"))
            reply(connection, refusal("too-long"))
            return

    line = buffer.partition(b"\n")[0]
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError:
        emit(refusal("bad-value"))
        reply(connection, refusal("bad-value"))
        return

    try:
        session, event, work = parse_request(text)
    except BadRequest as exc:
        emit(refusal(exc.code))
        reply(connection, refusal(exc.code))
        return

    decision = decide(room, session, event, work, at)
    payload = row(decision, at, session)
    if work is not None:
        # ⚠️ **語を、ログの行に載せる。** 載せなければ、一日の内訳
        #    （`projects/stackchan.day`）は**この層が足したものを1つも数えられない**。
        # ⛔ **向こうの `row()` は変えない**——この鍵を知らない読者にとっては、
        #    知らない鍵が1つ増えるだけであり、向こうのデーモンは今もこの鍵を出さない。
        payload["work"] = work
    emit(payload)

    # ⚠️ **枠より先に決める。** 首が流すなら、枠は身振りを運ばない——2度動かさない。
    streamed = neck.take(decision, at)
    visible = replace(decision, gesture=None) if streamed else decision
    frame = outbound.frame(visible)
    if frame is not None:
        deliver(frame, at, session, neck.port)
    if streamed:
        # ⚠️ **同じ `at` から。** 顔と光の行が先、姿勢の行が後である。
        neck.pump(at)
    reply(connection, payload)


def serve(room: NextRoom, outbound: Outbound, listener: socket.socket, wake: int,
          neck: Neck) -> None:
    """**ソケットか、次の期限か、合図まで待つ。** ⛔ **固定の刻みは無い。**

    ⚠️ **期限は2つある**——部屋の期限（点滅の期限を含む）と、首の次の姿勢の
    期限である。**早い方で目を覚まし、遅い方の作業を残さない。**
    ⛔ **`room.deadline` は `Presence` のものであり、部屋と点滅の早い方である。**
    """
    while True:
        now = time.monotonic()
        neck.pump(now)

        timeout = None
        deadlines = [d for d in (room.deadline, neck.deadline) if d is not None]
        if deadlines:
            timeout = max(0.0, min(deadlines) - time.monotonic())

        readable, _, _ = select.select([listener, wake], [], [], timeout)
        if wake in readable:
            os.read(wake, 64)
            return

        now = time.monotonic()
        neck.pump(now)
        decision = room.tick(now)
        if decision is not None:
            emit(row(decision, now, None))
            frame = outbound.frame(decision)
            if frame is not None:
                deliver(frame, now, None, neck.port)

        if listener in readable:
            connection, _ = listener.accept()
            with connection:
                handle(connection, room, outbound, neck, now)
            neck.pump(time.monotonic())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m projects.stackchan_next.daemon",
        description=(
            "The same room, with the work vocabulary and one presence dial. "
            "Listens on its own socket, logs every frame and, given --port, "
            "writes the line to the board's console."
        ),
    )
    parser.add_argument("--socket", default=default_socket(), metavar="PATH",
                        help="the Unix socket to bind (default: %(default)s)")
    parser.add_argument("--port", default=None, metavar="PATH",
                        help="the board's console to write frames to; without it, "
                             "frames are only logged (default: none)")
    parser.add_argument("--motion", choices=("on", "off"), default="on",
                        help="whether the neck channel chooses gestures (default: on)")
    parser.add_argument("--sound", choices=("on", "off"), default="off",
                        help="whether the speaker channel is on (default: off); "
                             "the quiet hours 21:00-05:00 still close it")
    parser.add_argument("--presence", choices=PRESENCES, default=DEFAULT_PRESENCE,
                        help="how loud the layer added on 2026-10-20 may be "
                             "(default: %(default)s)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # ⛔ **信号の受け口を、ソケットより先に作る。** 向こうと同じ順序であり、
    #    同じ理由である（2026-10-19 の検査が1度だけ落ちた隙間）。
    wake_r, wake_w = os.pipe()

    def stop(signum: int, frame: object) -> None:
        try:
            os.write(wake_w, b"\x00")
        except OSError:
            pass

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        listener = bind(args.socket)
    except OSError as exc:
        sys.stderr.write(f"cannot bind {args.socket}: {exc}\n")
        os.close(wake_r)
        os.close(wake_w)
        return 1
    if listener is None:
        sys.stderr.write(f"another daemon is alive on {args.socket}\n")
        os.close(wake_r)
        os.close(wake_w)
        return EXIT_ALREADY_RUNNING

    room = NextRoom(presence=args.presence, motion=args.motion == "on",
                    sound=args.sound == "on")
    outbound = Outbound()
    neck = Neck(args.port)
    emit({"daemon": "listening", "socket": args.socket, "port": args.port,
          "presence": args.presence})
    try:
        serve(room, outbound, listener, wake_r, neck)
    finally:
        listener.close()
        try:
            os.unlink(args.socket)
        except FileNotFoundError:
            pass
        os.close(wake_r)
        os.close(wake_w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
