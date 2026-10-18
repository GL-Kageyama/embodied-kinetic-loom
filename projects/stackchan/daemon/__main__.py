# -*- coding: utf-8 -*-
"""**デーモンの縁。** `python3 -m projects.stackchan.daemon`（リポジトリの根から）。

⛔ **時計・ソケット・合図は、このファイルにだけ在る。** 中核は `room.py` であり、
そこは外の世界を読まない。⇒ **判定はソケット無しで試験できる。**

⚠️ **launchd とフックに繋がっている**——2026-10-18 に設置された。設計と、外し方は
`docs/stackchan-daemon.md` に在る。

⚠️ **起動は挨拶を送らない。** 最初の運動は最初の事象から来る。
⚠️ **停止は何も送らない。** 駐機も、最後の身振りも無い——**この機体に停止命令は無い。**
✅ **伝送路は 2026-10-18 に、この縁へ着いた**——`--port` を渡すと、枠は
**その端末へ1行として書かれる**。⚠️ **枠が運ぶのは語だけである**（`face`・`light`・`gesture`）。
⛔ **`sent` が `True` になるのは、`os.write` が行の長さを返したときだけである。**
⚠️ **開いて書き、閉じる**——**1枠ごとに。** コンソールは1本のポートであり、
握ったままのデーモンは `bench` と `idf.py flash` の間に座り込む。
⚠️ **`--port` が無いとき、`sent` は今まで通り `False` である。**

✅ **そして 0.19.14 から、首は同じ輪で動く**——遷移が身振りを選んだとき、
デーモンは `neck/` の純粋な予定表を1つ持ち、**同じ `at` から姿勢の行を流す**。
⚠️ **枠と姿勢の行で、同じ身振りを2度動かさない**: 流すとき、枠の `gesture` は `None` である
（基板の `PlayGesture` はメインループを数秒塞ぎ、その間の姿勢は遅れて適用される）。
⛔ **最初の1回だけは基板に演じさせる**——このホストは首の位置を読まないからである。**
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
from dataclasses import replace

from engine.backend import protocol_stackchan as wire
from projects.stackchan.behaviors import Decision
from projects.stackchan.neck import gestures
from projects.stackchan.neck.stream import Stream
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


def frame_line(frame: Frame) -> str:
    """**枠の、ただ1つの綴り。** ⚠️ **符号化は `protocol_stackchan.py` に1つだけ在る。**

    ⚠️ **ログに残る行と、端末へ書く行は、この1回の符号化から来る。**
    2回書けば、2つは同じに見えて、同じであることを誰も確かめていない。
    """
    command = wire.Command(face=frame.face, light=frame.light, gesture=frame.gesture,
                           sound=frame.sound)
    return wire.encode(command).decode("ascii")


def frame_row(line: str, at: float, session: str | None, sent: bool) -> dict:
    """**枠の1行を、ログの1行にする。** ⛔ **書いたことは、渡ったことではない。**

    ⚠️ `sent` は **`os.write` が行の長さを返したときだけ** `True` である。
    """
    return {"frame": line.rstrip("\n"), "sent": sent, "at": at, "session": session}


def send_line(path: str, line: str | bytes) -> bool:
    """**1行を端末へ書く。** ✅ 書けたときだけ `True`。

    ⚠️ **開いて、書き、閉じる。** 1行ごとに。⚠️ 遷移の枠も、20 ms の姿勢の行も
    ここを通る——**握らないことで `bench` と `idf.py flash` を妨げない。**
    ⚠️ **枠はここで ASCII へ符号化するが、姿勢の行はすでにバイト列である**
    （`protocol_stackchan_pose.encode` の1つの綴りを、ここで作り直さない）。

    ⛔ **短く書けたら、失敗である。** 端末が受け取っていない行を、
    `sent` が `True` と言ってはならない。

    ⚠️ **リングバッファと、閉じたときの回線の扱いは、ここでは測っていない**——
    この機体で1度だけ、実際に書いて確かめた（記録は `HISTORY.md` の 0.19.8）。
    """
    try:
        fd = os.open(path, os.O_WRONLY | os.O_NOCTTY | os.O_NONBLOCK | os.O_APPEND)
    except OSError:
        return False
    try:
        payload = line.encode("ascii") if isinstance(line, str) else line
        return os.write(fd, payload) == len(payload)
    except OSError:
        return False
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


class Neck:
    """**首の縁。** ⚠️ **純粋な予定表（`Stream`）と、最後に命じた姿勢だけを持つ。**

    ⛔ **最初の1回は、基板に演じさせる。** このホストは首の位置を読まない——
    知らない位置を始点にすれば、1行目は「その位置への移動」になる。
    だから最初の身振りは枠の `gesture` に任せ、**その終わりの姿勢**を覚える。
    ⚠️ **それは推測である**: 基板が演じ切ったことを、このホストは知らない
    （この機体は何も報告しない）。**命令は届くものとして扱う。**
    """

    def __init__(self, port: str | None, *, period: float = gestures.DEFAULT_PERIOD,
                 hold: float = gestures.DEFAULT_HOLD) -> None:
        self.port = port
        self._period = period
        self._stream = Stream(period=period, hold=hold)
        self._parked = None

    @property
    def deadline(self) -> float | None:
        return self._stream.deadline if self.port is not None else None

    def take(self, decision: Decision, at: float) -> bool:
        """**身振りを引き受ける。** ⚠️ **流し始めたときだけ `True`。**

        ⛔ **枠と姿勢の行で、同じ身振りを2度動かさない。** `True` を返したら、
        呼ぶ側は枠の `gesture` を `None` にして送る——基板の `PlayGesture` は
        メインループを数秒塞ぎ、その間の姿勢は遅れて適用される。
        """
        if self.port is None or decision.gesture is None:
            return False

        starts = self._stream.last_pose
        if starts is None:
            starts = self._parked
        if starts is None:
            # ⚠️ **最初の1回だけ、基板に演じさせる。** 位置を知らないからである。
            self._parked = gestures.ends(decision.gesture)
            return False

        if self._stream.running:
            # ⚠️ **割り込まれた動きも、送った数として残す。**
            self._stream.stop(at)
            summary = self._stream.take_summary()
            if summary is not None:
                emit({"neck": summary.name, "applied": summary.applied,
                      "late": summary.late, "held": summary.held,
                      "at": summary.at, "interrupted": True})

        plan = gestures.plan(decision.gesture, starts, period=self._period)
        self._stream.start(plan, at, name=decision.gesture)
        emit({
            "neck": decision.gesture,
            "from": [starts.yaw_tenths, starts.pitch_tenths],
            "to": [plan.ends.yaw_tenths, plan.ends.pitch_tenths],
            "poses": plan.count,
            "seconds": round(plan.duration, 3),
            "at": at,
        })
        return True

    def pump(self, at: float) -> None:
        """**期限の来た行を、すべて書く。** ⚠️ 終わったら、要約を1行だけ残す。"""
        if self.port is None:
            return
        while True:
            line = self._stream.line(at)
            if line is None:
                break
            if not send_line(self.port, line):
                # ⛔ **書けなかった列を、書いた列として続けない。**
                emit({"neck": self._stream.name, "sent": False, "at": at})
                self._stream.stop(at)
                break
        summary = self._stream.take_summary()
        if summary is not None:
            emit({"neck": summary.name, "applied": summary.applied,
                  "late": summary.late, "held": summary.held, "at": summary.at})


def reply(connection: socket.socket, payload: dict) -> None:
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    try:
        connection.sendall(line.encode("utf-8"))
    except OSError:
        pass


def deliver(frame: Frame, at: float, session: str | None, port: str | None) -> None:
    """**枠を、ログの1行にし——端末があれば、そこへも書く。**

    ⚠️ **ログの行は、送った後でも先でも同じ1行である。** 違うのは `sent` だけ。
    ⛔ **端末が無いことは失敗ではない**——`--port` を渡さなければ、今まで通り書かない。
    """
    line = frame_line(frame)
    sent = send_line(port, line) if port is not None else False
    emit(frame_row(line, at, session, sent))


def handle(connection: socket.socket, room: Room, outbound: Outbound, neck: Neck,
           at: float) -> None:
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


def serve(room: Room, outbound: Outbound, listener: socket.socket, wake: int,
          neck: Neck) -> None:
    """**ソケットか、次の期限か、合図まで待つ。** ⛔ **固定の刻みは無い。**

    ⚠️ **期限は2つある**——部屋の期限と、首の次の姿勢の期限である。
    **早い方で目を覚まし、遅い方の作業を残さない。**
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
        prog="python3 -m projects.stackchan.daemon",
        description=(
            "One room, one neck. Listens on a socket and decides; it logs every frame "
            "and, given --port, writes the line to the board's console."
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
    neck = Neck(args.port)
    emit({"daemon": "listening", "socket": args.socket, "port": args.port})
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
