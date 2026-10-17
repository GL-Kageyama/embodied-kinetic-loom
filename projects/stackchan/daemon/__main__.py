# -*- coding: utf-8 -*-
"""**デーモンの縁。** `python3 -m projects.stackchan.daemon`（リポジトリの根から）。

⛔ **時計・ソケット・合図は、このファイルにだけ在る。** 中核は `room.py` であり、
そこは外の世界を読まない。⇒ **判定はソケット無しで試験できる。**

⚠️ **launchd とフックに繋がっている**——2026-10-18 に設置された。設計と、外し方は
`docs/stackchan-daemon.md` に在る。

⚠️ **起動は挨拶を送らない。** 最初の運動は最初の事象から来る。
⚠️ **停止は何も送らない。** 駐機も、最後の身振りも無い——**この機体に停止命令は無い。**
⚠️ **機体への伝送路はまだ無い。** この縁は、渡すはずの枠を**ログの1行として書く**——
`{"frame": …}` がそれであり、**`sent` はどの行でも `False` である。**
⛔ **書くことは、送ることではない。**
"""
from __future__ import annotations

import argparse
import json
import os
import select
import signal
import socket
import sys
import time

from engine.backend import protocol_stackchan as wire
from projects.stackchan.outbound import Frame, Outbound

from .room import (
    CLIENT_TIMEOUT,
    MAX_LINE,
    BadRequest,
    Room,
    parse_request,
    refusal,
    row,
    socket_path,
)

#: ⚠️ **別のデーモンが生きている。** 2つ目のプロセスは、機体に一言も告げずに終わる。
EXIT_ALREADY_RUNNING = 3

#: ⚠️ **続きを読む単位である。** 数は意味を持たない。
RECV = 1024


def default_socket() -> str:
    """**綴りは `room.socket_path` に1つだけ在る。** ⚠️ ここは uid を渡すだけである。"""
    return socket_path(os.getuid())


def probe(path: str) -> bool:
    """**生きているデーモンがいるか。** ⛔ **ソケットが錠であり、pidfile は無い。**"""
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(CLIENT_TIMEOUT)
    try:
        connection.connect(path)
    except OSError:
        return False
    else:
        return True
    finally:
        connection.close()


def bind(path: str) -> socket.socket | None:
    """**探してから bind する。** 生きていれば `None`、古ければ unlink する。

    ⚠️ **connect が通ったパスは消さない。** 消せば、生きているデーモンの
    ソケットを2つ目のプロセスが奪うことになる。
    """
    if probe(path):
        return None
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        listener.bind(path)
    except OSError:
        listener.close()
        raise
    # ⚠️ **ソケットファイルは umask を引き継ぐ。** bind の後に締める。
    os.chmod(path, 0o600)
    listener.listen(8)
    return listener


def emit(payload: dict) -> None:
    """**1行を、その場で出す。** ⛔ **溜めない**——落ちたときに何も残らない。"""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def frame_row(frame: Frame, at: float, session: str | None) -> dict:
    """**機体へ渡るはずの1行を、ログの1行にする。** ⛔ **渡ってはいない。**

    ⚠️ **符号化は `engine/backend/protocol_stackchan.py` に1つだけ在る。**
    ここは値を渡すだけであり、綴りを写さない。
    """
    command = wire.Command(face=frame.face, light=frame.light, gesture=frame.gesture)
    line = wire.encode(command).decode("ascii").rstrip("\n")
    return {"frame": line, "sent": False, "at": at, "session": session}


def reply(connection: socket.socket, payload: dict) -> None:
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    try:
        connection.sendall(line.encode("utf-8"))
    except OSError:
        pass


def handle(connection: socket.socket, room: Room, outbound: Outbound, at: float) -> None:
    """**1つの接続を読む。** ⚠️ **行が届かなければ、待ち続けずに閉じる。**"""
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
        session, event = parse_request(text)
    except BadRequest as exc:
        emit(refusal(exc.code))
        reply(connection, refusal(exc.code))
        return

    decision = room.offer(session, event, at)
    payload = row(decision, at, session)
    emit(payload)
    frame = outbound.frame(decision)
    if frame is not None:
        emit(frame_row(frame, at, session))
    reply(connection, payload)


def serve(room: Room, outbound: Outbound, listener: socket.socket, wake: int) -> None:
    """**ソケットか、次の期限か、合図まで待つ。** ⛔ **固定の刻みは無い。**"""
    while True:
        timeout = None
        if room.deadline is not None:
            timeout = max(0.0, room.deadline - time.monotonic())

        readable, _, _ = select.select([listener, wake], [], [], timeout)
        if wake in readable:
            os.read(wake, 64)
            return

        now = time.monotonic()
        decision = room.tick(now)
        if decision is not None:
            emit(row(decision, now, None))
            frame = outbound.frame(decision)
            if frame is not None:
                emit(frame_row(frame, now, None))

        if listener in readable:
            connection, _ = listener.accept()
            with connection:
                handle(connection, room, outbound, now)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m projects.stackchan.daemon",
        description=(
            "One room, one neck. Listens on a socket and decides; it logs the frame "
            "it would send and sends nothing (there is no transport yet)."
        ),
    )
    parser.add_argument("--socket", default=default_socket(), metavar="PATH",
                        help="the Unix socket to bind (default: %(default)s)")
    parser.add_argument("--motion", choices=("on", "off"), default="on",
                        help="whether the neck channel chooses gestures (default: on)")
    parser.add_argument("--sound", choices=("on", "off"), default="off",
                        help="whether the speaker channel is on (default: off)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        listener = bind(args.socket)
    except OSError as exc:
        sys.stderr.write(f"cannot bind {args.socket}: {exc}\n")
        return 1
    if listener is None:
        sys.stderr.write(f"another daemon is alive on {args.socket}\n")
        return EXIT_ALREADY_RUNNING

    wake_r, wake_w = os.pipe()

    def stop(signum: int, frame: object) -> None:
        try:
            os.write(wake_w, b"\x00")
        except OSError:
            pass

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    room = Room(motion=args.motion == "on", sound=args.sound == "on")
    outbound = Outbound()
    emit({"daemon": "listening", "socket": args.socket})
    try:
        serve(room, outbound, listener, wake_r)
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
