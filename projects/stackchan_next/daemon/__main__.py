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

## 2本目のソケットと糸（0.19.64、Phase 3.5）

⛔ **監修は、体のソケットに相乗りしない。** 体の `handle()` は枠を書いて基板の
受理を待つので、その返事は中央 890ms である——**いちばん声をかけたい瞬間に落ちる**
（設計 §19.1）。⇒ **同じプロセスの中に、メタ専用のソケットを1本と、糸を1本足す。**

- 綴りは `room.meta_socket_path(uid)`（`/tmp/ekl-stackchan-meta-<uid>.sock`）。
- `--meta off` なら**開かない**。⚠️ **フックはダイヤルを知らない**——ソケットが
  無ければ `connect` が失敗し、何も印字せず0で終わる。**それが `off` の実装である**（§6）。
- 要求の形は**体と同じ**（`parse_request`——窓・事象・作業語）。⇒ **契約を増やさない。**
- 糸は数の規則を回して即答する。⛔ **体の糸を待たない**——`select` の輪に混ぜず、
  `accept` する別の糸に置く（§19.7 の試作が測った形である）。
- 例外は**糸の縁**で捕まえ、`{"meta": "error", "error": "<型名>"}` を1行残して
  次の接続を待つ。⛔ **核心（`MetaRoom`）に `try` を書かない**——核心が自分で
  例外を飲めば、「規則が壊れている」ことが見えなくなる（§19.7）。
- **Phase 3.5 では、フックはまだこのソケットへ送らない。** 返事の1行はあるが、
  **読む者が居ない**——配送は Phase 4 である（§15）。
"""
from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import select
import signal
import socket
import sys
import threading
import time
from dataclasses import replace

from projects.stackchan.behaviors import Decision
from projects.stackchan.daemon.__main__ import (
    EXIT_ALREADY_RUNNING,
    RECV,
    Link,
    Neck,
    bind,
    deliver,
    emit,
    reply,
)
from projects.stackchan.daemon.room import BadRequest, refusal, row
from projects.stackchan.outbound import Outbound
from projects.stackchan.quiet import is_quiet
#: ⚠️ **合成は縁のものである**（`subprocess` を輸入してよいのは `__main__.py` だけ）。
#: ⛔ **鎖をここに書き写さない**——`samples` が唯一の鎖である（`voice/__main__.py`）。
from projects.stackchan.voice.__main__ import samples
from projects.stackchan.voice.speaker import Speaker

from projects.stackchan_meta import MetaRoom

from ..presence import DEFAULT_PRESENCE, PRESENCES
from .room import (
    CLIENT_TIMEOUT,
    MAX_LINE,
    NextRoom,
    meta_socket_path,
    mouth_socket_path,
    parse_request,
    parse_voice,
    socket_path,
)


#: ⛔ **閉じた3語である。** ダイヤルはユーザーが回すものであり、機械が決めるものではない（§6）。
#: ⚠️ **`off` は「黙る」ではなく「ソケットを開かない」である**——フックはダイヤルを
#: 知らないので、無いソケットへの `connect` が失敗することが `off` の実装である。
META_DIALS = ("off", "quiet", "eager")


def default_socket() -> str:
    """**綴りは `room.socket_path` に1つだけ在る。** ⚠️ ここは uid を渡すだけである。"""
    return socket_path(os.getuid())


def default_meta_socket() -> str:
    """**綴りは `room.meta_socket_path` に1つだけ在る。** ⚠️ uid を渡すだけである。"""
    return meta_socket_path(os.getuid())


def default_mouth_socket() -> str:
    """**綴りは `room.mouth_socket_path` に1つだけ在る。** ⚠️ uid を渡すだけである。"""
    return mouth_socket_path(os.getuid())


def mouth_command() -> str:
    """**本体へ渡す、口の命令である。** ⚠️ **口が開いているときだけ、前置きに載る。**

    ⛔ **道は走っている場所のものである。** 規則の層（`render.py`）は絶対の道を
    持たない——**層が機械の住所を知れば、層はこの機械に縛られる**（§11.3）。
    ⇒ **住所を組み立てるのは縁であり、縁は既に外の世界を読んでいる。**

    ⚠️ **`parents[3]` は、このファイルから数えたリポジトリの根である**
    （`daemon` / `stackchan_next` / `projects` / 根）。
    """
    root = pathlib.Path(__file__).resolve().parents[3]
    return f'cd "{root}" && "{sys.executable}" -m projects.stackchan_next.mouth'


def parse_listen(text: str) -> tuple[str, int]:
    """**`HOST:PORT` を2つに割る。** ⛔ **番号は数として読む。**

    ⚠️ **ここが受け取るのは、基板が dial してくる住所である。**
    `192.168.0.103:3333`——**基板の NVS に入っている値が、そのまま来る。**
    """
    host, _, port = text.rpartition(":")
    if not host or not port:
        raise ValueError(f"not HOST:PORT: {text}")
    return host, int(port)


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


class _Silent(Exception):
    """**行が届かなかった。** ⛔ **断りではない**——何も言わずに閉じる（既存の規則）。"""


def _read_text(connection: socket.socket) -> str:
    """**1行を読み、UTF-8 の文にする。** ⚠️ **体とメタで、読み方は1つである。**

    ⛔ **断りの符号は、ここでは出さない**——体はそれをログの行にもするが、
    メタは返事にだけ載せる。**違うのはそこだけであり、写せば2つの綴りが生まれる。**
    """
    connection.settimeout(CLIENT_TIMEOUT)
    buffer = b""
    while b"\n" not in buffer:
        try:
            chunk = connection.recv(RECV)
        except OSError:
            raise _Silent from None
        if not chunk:
            raise _Silent
        buffer += chunk
        if len(buffer) > MAX_LINE:
            raise BadRequest("too-long")

    line = buffer.partition(b"\n")[0]
    try:
        return line.decode("utf-8")
    except UnicodeDecodeError:
        raise BadRequest("bad-value") from None


def handle(connection: socket.socket, room: NextRoom, outbound: Outbound, neck: Neck,
           at: float) -> None:
    """**1つの接続を読む。** ⚠️ **行が届かなければ、待ち続けずに閉じる。**

    ⚠️ **向こうの `handle` との違いは2行である**——要求が3つに割れ、判定へ
    `work` が渡る。**それ以外（長さの上限・UTF-8・断りの符号・枠より先に首・
    同じ `at`）は同じである。**
    """
    try:
        text = _read_text(connection)
        session, event, work = parse_request(text)
    except _Silent:
        return
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
          neck: Neck, link: Link | None = None,
          speaker: Speaker | None = None, greet: str | None = None) -> None:
    """**ソケットか、次の期限か、基板の dial か、合図まで待つ。** ⛔ **固定の刻みは無い。**

    ⚠️ **期限は2つある**——部屋の期限（点滅の期限を含む）と、首の次の姿勢の
    期限である。**早い方で目を覚まし、遅い方の作業を残さない。**
    ⛔ **`room.deadline` は `Presence` のものであり、部屋と点滅の早い方である。**

    ⚠️ **`link` は待つ対象であって、読む対象ではない。** ⛔ **基板の答えは首と枠が
    読む**——ここで `recv` すれば、**判定も姿勢も消える。** 切れたかどうかは
    `Link.alive()` が見る（`MSG_PEEK`、1バイトも食べない）。
    """
    while True:
        now = time.monotonic()
        neck.pump(now)

        timeout = None
        deadlines = [d for d in (room.deadline, neck.deadline) if d is not None]
        if deadlines:
            timeout = max(0.0, min(deadlines) - time.monotonic())

        watch = [listener, wake]
        if link is not None:
            watch.append(link.listener)
        readable, _, _ = select.select(watch, [], [], timeout)
        if wake in readable:
            os.read(wake, 64)
            return

        if link is not None and link.listener in readable:
            peer = link.accept()
            if peer is not None:
                # ⚠️ **誰が dial してきたかを残す。** ⛔ **初めての接続でなければ、
                #    前の1本は畳まれている**——体は1つである。
                emit({"link": "the board dialled in", "peer": peer})
                # ⚠️ **`--say` は計器である**（2026-10-21）。回線が開いたことを
                #    耳で確かめるために、1文だけ言う。⛔ **候補の道ではない**——
                #    候補を言うかどうかは §17.4 (c) の裁定であり、
                #    **文を作るのが誰かはまだ決まっていない**（§22.2）。
                if speaker is not None and greet is not None:
                    speaker.say(greet)
        elif link is not None and link.peer is not None and not link.alive():
            # ⛔ **切れたことは、黙って消さない。** 次の身振りは、これを知っている。
            emit({"link": "the board let go", "peer": link.peer})
            link.drop()
        elif link is not None and link.broken:
            # ⛔ **音声の塊を、途中で諦めた。** 続きはもう頭ではない——**回線の上の
            #    頭と標本の境目はずれており、戻す手は無い。** ⇒ **捨てる。**
            #    ⚠️ **閉じるのはこの糸だけである**（声の糸は `_broken` を立てるだけ）。
            emit({"link": "the song broke mid-block", "peer": link.peer})
            link.drop()

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


def meta_handle(connection: socket.socket, room: MetaRoom, at: float) -> None:
    """**メタの1接続を読む。** ⚠️ **体の `handle` を写したのではない**——順序が違う。

    体は `emit` → 首 → 枠 → `reply` である（§19.1）。ここは**1行読んで、数えて、
    1行返す**だけである——⛔ **待つものが1つも無い。** それが決定11の全部である。
    """
    try:
        text = _read_text(connection)
        session, event, work = parse_request(text)
    except _Silent:
        return
    except BadRequest as exc:
        # ⚠️ **断りも、体と同じ符号である。** 新しい符号を発明しない。
        # ⛔ **ログには残さない**——日の計器の5つの欄は、この行を知らない（§10.6）。
        reply(connection, refusal(exc.code))
        return

    # ⚠️ **時刻はここで1度だけ読む。** 核心（`MetaRoom`）は時計を持たない。
    says = room.observe(session, event, at, work)
    # ⚠️ **返事の形は今のうちに決めておく。** `context` が無ければ `null` である
    #    ——⛔ **鍵そのものを省かない**: 読む側（Phase 4 のフック）が、
    #    *返事が無い* と *返事の形が違う* を区別できなくなる。
    reply(connection, {"context": says})


def meta_loop(listener: socket.socket, room: MetaRoom) -> None:
    """**メタの糸。** ⛔ **体の `serve` の輪には入らない**——別の糸である。

    ⚠️ **例外はここで捕まえる**（§13）。糸の例外を `try` の外へ出せば、
    プロセスが落ち、**体も一緒に落ちる**——同じプロセスに住んでいる以上、
    これが唯一の危険である。
    """
    while True:
        try:
            connection, _ = listener.accept()
        except OSError:
            # ⚠️ **受口が閉じられた。** 片付けの最中である——静かに降りる。
            return
        with connection:
            try:
                meta_handle(connection, room, time.monotonic())
            except Exception as exc:  # noqa: BLE001 — 意図した catch である（§13）
                # ⛔ **自由文を入れない。** 型名だけである——`error` の欄は閉じている。
                emit({"meta": "error", "error": type(exc).__name__})


def voice_handle(connection: socket.socket, speaker: Speaker, link: Link | None,
                 hour: int) -> None:
    """**口の1接続を読む。** ⚠️ **文を受け取り、声の糸へ渡して、1語返すだけである。**

    ⛔ **ここで合成しない。** 合成は声の糸の仕事であり、**この糸を止めれば
    体のソケットも止まる**——同じプロセスに住んでいる（§13）。

    ⛔ **夜は鳴らさない。** §17.4 (c) の裁定は「**昼に限り**、候補を1文の声に
    してよい」であり、夜は表情だけである（§22.5）。⚠️ **規則は `quiet.py` に
    1つだけ在る**——音の欄を閉じるのと同じ関数である。⇒ **声だけ別の時刻を読まない。**
    """
    try:
        text = parse_voice(_read_text(connection))
    except _Silent:
        return
    except BadRequest as exc:
        # ⚠️ **断りも体と同じ符号である。** 新しい符号を発明しない。
        emit({"voice": "refused", "error": exc.code})
        reply(connection, {"voice": "refused", "error": exc.code})
        return

    # ⚠️ **板が居ないことは事実であり、規則ではない。** 先に見る——夜でも
    #    「板が居ない」は同じ事実であり、そして**無い回線へ3秒の合成をしない。**
    if link is None or link.peer is None:
        emit({"voice": "no-board"})
        reply(connection, {"voice": "no-board"})
        return

    if is_quiet(hour):
        emit({"voice": "night"})
        reply(connection, {"voice": "night"})
        return

    if not speaker.say(text):
        # ⚠️ **`Speaker` が `busy` の行を自分で書く。** ここで書けば2行になる。
        reply(connection, {"voice": "busy"})
        return
    # ⚠️ **返事は `queued` であり、行ではない。** この1文について残るのは、
    #    声の糸が鳴り終えたときに書く `spoke` の1行だけである——⛔ **`queued` を
    #    行にすれば、`voice` の値が1つ増え、計器がそれを `unreadable` と数える**
    #    （2026-10-21、本体プロセスで通したときに気づいた）。**受け取ったことは、
    #    鳴り終えた行が既に含んでいる。**
    reply(connection, {"voice": "queued"})


def voice_loop(listener: socket.socket, speaker: Speaker, link: Link | None) -> None:
    """**口の糸。** ⛔ **体の `serve` の輪にも、メタの糸にも混ぜない。**

    ⚠️ **3本目である理由は、`room.mouth_socket_path` に書いてある**——閉じた
    2本のどちらかへ自由な欄を足せば、この層のプライバシーが**スキーマの水準で
    偽になる。**

    ⚠️ **例外はこの糸の縁で捕まえる**（§13）。ここで飲まなければ、プロセスが
    落ち、**体も一緒に落ちる。**

    ⚠️ **時刻は接続ごとに読む。** ⛔ 糸を起こした時刻を覚えない——**21:00 を
    またいで走るデーモンが、夜に喋り続ける**（`quiet.py` の規則は壁時計である）。
    """
    while True:
        try:
            connection, _ = listener.accept()
        except OSError:
            # ⚠️ **受口が閉じられた。** 片付けの最中である——静かに降りる。
            return
        with connection:
            try:
                voice_handle(connection, speaker, link, datetime.datetime.now().hour)
            except Exception as exc:  # noqa: BLE001 — 意図した catch である（§13）
                # ⛔ **自由文を入れない。** 型名だけである。
                emit({"voice": "error", "error": type(exc).__name__})


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
    parser.add_argument("--listen", default=None, metavar="HOST:PORT",
                        help="wait for the board to dial in on HOST:PORT, and use "
                             "that connection instead of --port (default: none)")
    parser.add_argument("--motion", choices=("on", "off"), default="on",
                        help="whether the neck channel chooses gestures (default: on)")
    parser.add_argument("--sound", choices=("on", "off"), default="off",
                        help="whether the speaker channel is on (default: off); "
                             "the quiet hours 21:00-06:00 still close it")
    parser.add_argument("--presence", choices=PRESENCES, default=DEFAULT_PRESENCE,
                        help="how loud the layer added on 2026-10-20 may be "
                             "(default: %(default)s)")
    parser.add_argument("--meta", choices=META_DIALS, default="quiet",
                        help="how much the meta layer may say (default: %(default)s); "
                             "off opens no meta socket at all")
    parser.add_argument("--meta-socket", default=None, metavar="PATH",
                        help="the meta Unix socket to bind "
                             "(default: /tmp/ekl-stackchan-meta-<uid>.sock)")
    parser.add_argument("--say", default=None, metavar="TEXT",
                        help="say this one sentence when the board dials in "
                             "(an instrument for the voice path, not the candidate "
                             "path; needs --listen)")
    parser.add_argument("--voice", choices=("off", "on"), default="off",
                        help="whether the body's mouth is open: a mouth socket, "
                             "and the one clause in the prelude that tells the body "
                             "how to speak (default: off)")
    parser.add_argument("--mouth-socket", default=None, metavar="PATH",
                        help="the mouth's Unix socket to bind "
                             "(default: /tmp/ekl-stackchan-mouth-<uid>.sock)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # ⛔ **道とリンクの両方を名指さない。** どちらへ書くのかが2通りあれば、
    #    **片方は必ず読まれない**——そして、どちらが読まれなかったかを言う欄が無い。
    # ⚠️ **これはソケットを束縛する前に決める。** 束縛した後で断れば、
    #    **ソケットを片付ける道が4つに増える**——そのうち3つは必ず間違う。
    if args.port is not None and args.listen is not None:
        sys.stderr.write("--port and --listen name two ways to the same body; "
                         "choose one\n")
        return 1
    # ⛔ **`--say` は回線を要る。** 声は、基板が開いた回線へしか流れない
    #    （§17.4 の代価の表——Mac から基板へは、33回すべて届かなかった）。
    #    ⇒ **束縛する前に断る。** 束縛した後で断れば、片付ける道が4つに増える。
    if args.say is not None and args.listen is None:
        sys.stderr.write("--say needs --listen: the board dials us\n")
        return 1
    # ⛔ **口も回線を要る。** 鳴らす先が無い口は、**呼ばれるたびに `no-board` を
    #    返すだけの道具**になる——そしてそれは、著者には「声が出ない日」と
    #    同じに見える。⇒ **束縛する前に断る。**
    if args.voice == "on" and args.listen is None:
        sys.stderr.write("--voice on needs --listen: the board dials us\n")
        return 1
    watch: tuple[str, int] | None = None
    if args.listen is not None:
        try:
            watch = parse_listen(args.listen)
        except ValueError as exc:
            sys.stderr.write(f"--listen: {exc}\n")
            return 1

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

    link = None
    if watch is not None:
        try:
            link = Link(*watch)
        except OSError as exc:
            # ⛔ **束縛できなければ、始めない。** 待ち受けられないデーモンは、
            #    基板から見て「居ない」のであり、**それは静かに見える。**
            sys.stderr.write(f"cannot listen on {args.listen}: {exc}\n")
            listener.close()
            try:
                os.unlink(args.socket)
            except FileNotFoundError:
                pass
            os.close(wake_r)
            os.close(wake_w)
            return 1

    # ⛔ **`--meta off` なら、束縛しない。** ソケットが無いことが `off` の実装であり、
    #    フックはダイヤルを知らない（§6）。⚠️ **起動行には値を載せる**——さもなければ、
    #    「規則が鳴らなかった日」と「黙らされた日」が、どちらも候補0になる（§10.6）。
    meta_path = args.meta_socket or default_meta_socket()
    meta_listener = None
    if args.meta != "off":
        try:
            meta_listener = bind(meta_path)
        except OSError as exc:
            sys.stderr.write(f"cannot bind {meta_path}: {exc}\n")
            if link is not None:
                link.close()
            listener.close()
            try:
                os.unlink(args.socket)
            except FileNotFoundError:
                pass
            os.close(wake_r)
            os.close(wake_w)
            return 1
        if meta_listener is None:
            # ⚠️ **生きているメタの受口が在る。** 体の受口は空いていたのに、である
            #    ——それは、同じプロセスの2本が食い違っているということである。
            sys.stderr.write(f"another meta daemon is alive on {meta_path}\n")
            if link is not None:
                link.close()
            listener.close()
            try:
                os.unlink(args.socket)
            except FileNotFoundError:
                pass
            os.close(wake_r)
            os.close(wake_w)
            return 1

    # ⛔ **口は3本目である。** `--voice off` なら束縛しない——**開かないことが
    #    `off` の実装である**（メタと同じ形。§6）。⚠️ **そのとき前置きにも
    #    命令は載らない**——開いていない口の命令は、失敗する道具の1行にしかならない。
    mouth_path = args.mouth_socket or default_mouth_socket()
    mouth_listener = None
    if args.voice == "on":
        try:
            mouth_listener = bind(mouth_path)
        except OSError as exc:
            sys.stderr.write(f"cannot bind {mouth_path}: {exc}\n")
            if link is not None:
                link.close()
            listener.close()
            if meta_listener is not None:
                meta_listener.close()
                try:
                    os.unlink(meta_path)
                except FileNotFoundError:
                    pass
            try:
                os.unlink(args.socket)
            except FileNotFoundError:
                pass
            os.close(wake_r)
            os.close(wake_w)
            return 1
        if mouth_listener is None:
            sys.stderr.write(f"another mouth is alive on {mouth_path}\n")
            if link is not None:
                link.close()
            listener.close()
            if meta_listener is not None:
                meta_listener.close()
                try:
                    os.unlink(meta_path)
                except FileNotFoundError:
                    pass
            try:
                os.unlink(args.socket)
            except FileNotFoundError:
                pass
            os.close(wake_r)
            os.close(wake_w)
            return 1

    # ⚠️ **口が開いていれば、声の糸は `--say` が無くても要る。** ⛔ **`--say` は
    #    計器であり、口は道である**——同じ糸を使うが、開ける条件が違う（§22.10）。
    speaking = args.say is not None or args.voice == "on"
    speaker = Speaker(link.send, samples, emit=emit) if speaking else None
    if speaker is not None:
        speaker.start()

    room = NextRoom(presence=args.presence, motion=args.motion == "on",
                    sound=args.sound == "on")
    outbound = Outbound()
    neck = Neck(link if link is not None else args.port)
    # ⚠️ **口の語も起動行に載せる。** 載せなければ、「鳴らなかった日」と
    #    「口が閉じていた日」が、どちらも声0になる（§10.6 と同じ理屈である）。
    emit({"daemon": "listening", "socket": args.socket, "port": args.port,
          "listen": (None if link is None else link.address),
          "presence": args.presence, "meta": args.meta, "voice": args.voice})

    meta_thread = None
    if meta_listener is not None:
        # ⚠️ **糸は1本増える。** 共有する状態は無いので、ロックも無い（§7.1）。
        #    ⛔ **`daemon=True`**——降りるのはプロセスと一緒であり、
        #    **糸が落ちても体は生きる。**
        # ⚠️ **口の命令は、口が開いているときだけ渡る**（§22.10）。⛔ **規則の
        #    層は道を組み立てない**——住所を渡すのは縁である。
        meta_room = MetaRoom(
            eager=args.meta == "eager", emit=emit,
            mouth=mouth_command() if mouth_listener is not None else None)
        meta_thread = threading.Thread(
            target=meta_loop, args=(meta_listener, meta_room),
            name="meta", daemon=True)
        meta_thread.start()

    if mouth_listener is not None:
        # ⚠️ **声の糸は既に走っている。** 口の糸は、その前に立つ受付である。
        #    ⛔ **`speaker` はここで必ず在る**（`--voice on` は `--listen` を要り、
        #    `speaking` は真になる）。
        voice_thread = threading.Thread(
            target=voice_loop, args=(mouth_listener, speaker, link),
            name="mouth", daemon=True)
        voice_thread.start()

    try:
        serve(room, outbound, listener, wake_r, neck, link,
              speaker=speaker, greet=args.say)
    finally:
        # ⚠️ **声の糸を先に降ろす。** ⛔ **後なら、閉じた回線へ書く糸が残る。**
        if speaker is not None:
            speaker.stop()
        if link is not None:
            link.close()
        listener.close()
        if meta_listener is not None:
            meta_listener.close()
            try:
                os.unlink(meta_path)
            except FileNotFoundError:
                pass
        if mouth_listener is not None:
            mouth_listener.close()
            try:
                os.unlink(mouth_path)
            except FileNotFoundError:
                pass
        try:
            os.unlink(args.socket)
        except FileNotFoundError:
            pass
        os.close(wake_r)
        os.close(wake_w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
