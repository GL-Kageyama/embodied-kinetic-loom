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

⚠️ **そして 2026-10-19 から、音には時刻の門がある**——21:00–05:00 は静かな時間であり、
`sound` の欄が閉じる（`quiet.py`）。⛔ **顔も光も首は従わない。**
**静かであることは、居ないことではない。**

✅ **そして 0.19.14 から、首は同じ輪で動く**——遷移が身振りを選んだとき、
デーモンは `neck/` の純粋な予定表を1つ持ち、**同じ `at` から姿勢の行を流す**。
⚠️ **枠と姿勢の行で、同じ身振りを2度動かさない**: 流すとき、枠の `gesture` は `None` である
（基板の `PlayGesture` はメインループを数秒塞ぎ、その間の姿勢は遅れて適用される）。
✅ **そして 0.19.23 から、身振りを引き受けるたびに、首の位置を尋ねる**——`bench pos` を1行書き、
⚠️ **`PORT_WAIT` で縛って同じ fd で読む**（`neck/readback.py`）。⇒ **始点は推測ではなく、
その瞬間の測定である**——起動後の最初の遷移も、始点が測れれば流せる。
⛔ **答えなければ、今まで通り基板に演じさせる**——**尋ねることは、待つことではない。**
⚠️ **尋ねるのは身振りの瞬間だけである**: 背景で定期に尋ねると、`bench` を打っている
行の途中に割り込む——**コンソールは人のものでもある。**
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import select
import signal
import socket
import sys
import time
from dataclasses import replace

from engine.backend import protocol_stackchan as wire
from engine.backend.protocol_stackchan_pose import Pose
from projects.stackchan.behaviors import Decision
from projects.stackchan.neck import gestures, readback
from projects.stackchan.neck.stream import Stream
from projects.stackchan.outbound import Frame, Outbound
from projects.stackchan.quiet import is_quiet

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


#: **1行が、端末に受け取られるのを待つ上限（秒）。**
#: ⛔ **待ちに上限が無いことが、2026-10-19 にデーモンを止めた。**
PORT_WAIT = 0.5

#: **窓のあいだに届いた文字を、ログ1行に収まる長さで残す。**
#: ⛔ **改行は潰さない**——繋がった行は、改行が無いこと自体が証拠である。
SEEN_LIMIT = 160

#: **流しの終わりに、基板自身の判定を待つ上限（秒）。**
#: ⚠️ **2026-10-19 に測った。** 静止した流しでは **0.489 秒**、機体の7つの身振りでは
#: **0.429〜0.991 秒**——**メインループが動いているあいだは遅れる。**
#: ⇒ **1.5 秒を上限にし、届いた時点で閉じる。**
#: ⚠️ **1.0 秒では、実測の最大 0.991 秒にほとんど触れていた**——**上限は、届く前に切れては意味が無い。**
#: ⛔ **この待ちは、コンソールを人の手から長く借りる。** その代償を、
#: この行が測ったものと引き換えに払う——**払わなければ、基板の数は誰にも読まれない。**
VERDICT_WAIT = 1.5

#: **判定を読みに行く間隔（秒）。** ⚠️ **上限まで持ち続けないためである。**
#: ⛔ **輪は期限でしか目を覚まさない**——上限だけを期限にすれば、0.49 秒で届いた日でも
#: **1.0 秒ぶんコンソールを握る。** ⇒ **短い期限を重ね、届いた時点で閉じる。**
VERDICT_POLL = 0.05


#: **問いを飲み込んだ行の印。** ⚠️ **基板が「この行は取らなかった」と言う綴りである。**
#: ⛔ **2026-10-19 まで2つしか無かった**——`console: unknown command` と `frame: refused`。
#: **そして、その日に残った3つの失敗は、どれも3つ目の綴りだった**:
#: `pose: refused (malformed)`——**尋ねた行が、前の姿勢の行と繋がって届いた**印である
#: （`at=22397.9` / `24989.5` / `25330.7`）。⇒ **尋ね直しは一度も発火しなかった。**
#: ⚠️ **`(too-long)` も同じ印である**: 繋がった行は 64 バイトの上限を越える。
#: ⇒ **符号を1つずつ書かない。** `pose: refused` は「その行を取らなかった」であり、
#: **符号そのものは `read` に残る**——**尋ね直しは、その区別を消さない。**
_MANGLED = re.compile(
    r"^(?:console: unknown command|frame: refused|pose: refused)", re.M)


def _seen(text: str) -> str:
    """**届いた文字の末尾。** ⚠️ **先頭ではなく末尾である**——答えは最後に来る。"""
    return text[-SEEN_LIMIT:] if len(text) > SEEN_LIMIT else text


class Neck:
    """**首の縁。** ⚠️ **純粋な予定表（`Stream`）と、最後に命じた姿勢だけを持つ。**

    ⚠️ **ポートは、1つの身振りの間だけ持つ。** ⛔ **行ごとに開かない。**
    2026-10-19 に測った: 20 ms ごとの `open`/`write`/`close` は、基板が
    コンソールを読まなくなった瞬間に **`open` が割り込み不能のまま返らず**、
    デーモンごと止まる。**開くのは身振りに1回、閉じるのは終わりに1回**であり、
    書くたびに `PORT_WAIT` を上限に待つ——⚠️ **基板が読まなければ、流れは止まる。**

    ⛔ **最初の1回は、基板に演じさせる**——ただし、**位置を尋ねて答えが返らなかったときだけ**である。
    ✅ **0.19.23 から、身振りを引き受けるたびに `bench pos` を1行書き、同じ fd で読む**
    （`neck/readback.py`）。⇒ **始点は推測ではなく、その瞬間の測定である。**
    ⛔ **答えなければ、知らない位置を始点にしない**: 枠の `gesture` に任せ、**その終わりの姿勢**を覚える。
    ⚠️ **それは推測である**: 基板が演じ切ったことを、このホストは知らない
    （この機体は何も報告しない）。**命令は届くものとして扱う。**

    ⛔ **背景で定期的に尋ねない。** コンソールは人のものでもある——2秒ごとの問い合わせは、
    `bench` を打っている行の途中に割り込む。**尋ねるのは、身振りを引き受ける瞬間だけ**であり、
    ⚠️ **その瞬間が、位置の要る唯一の瞬間である。**
    """

    def __init__(self, port: str | None, *, period: float = gestures.DEFAULT_PERIOD,
                 hold: float = gestures.DEFAULT_HOLD) -> None:
        self.port = port
        self._period = period
        self._stream = Stream(period=period, hold=hold)
        self._parked = None
        self._fd: int | None = None
        self._verdict_at: float | None = None
        self._verdict_next = 0.0
        self._verdict_name: str | None = None
        self._verdict_text = ""

    @property
    def deadline(self) -> float | None:
        """**次に起こすべき時刻。** ⚠️ **流しの後にもう1つある**——基板の判定である。"""
        if self._fd is None:
            return None
        if self._verdict_at is not None:
            return min(self._verdict_at, self._verdict_next)
        return self._stream.deadline

    def _open(self) -> bool:
        """**1つの身振りのために、1回だけ開く。** ⛔ 行ごとに開くと止まる。

        ⚠️ **`O_RDWR` である**——同じ fd で `bench pos` を書き、答えを読む。
        2つ目の fd を開けば、2回目の `open` がまた止まりうる。
        """
        self._close()
        if self.port is None:
            return False
        try:
            # ⚠️ **`O_APPEND` は tty には効かないが、普通のファイルでは効く。**
            #    これが無いと、試験のファイルの先頭を姿勢の列が上書きする。
            self._fd = os.open(self.port, os.O_RDWR | os.O_NOCTTY
                               | os.O_NONBLOCK | os.O_APPEND)
        except OSError:
            self._fd = None
            return False
        return True

    def _close(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        # ⚠️ **閉じたら、待っていた判定も捨てる**——次の身振りの始点に混ぜない。
        self._verdict_at = None
        self._verdict_next = 0.0
        self._verdict_name = None
        self._verdict_text = ""

    def _write_to(self, fd: int, payload: bytes) -> bool:
        """**その fd へ1行。** ⛔ **待ちには上限がある。**

        ⚠️ **短く書けた行は、続きを書く。** それでも `PORT_WAIT` を越えたら
        失敗である——**読まない端末を、行の列で埋めない。**
        """
        deadline = time.monotonic() + PORT_WAIT
        while True:
            try:
                written = os.write(fd, payload)
            except BlockingIOError:
                written = 0
            except OSError:
                return False
            if written == len(payload):
                return True
            if written:
                payload = payload[written:]
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                return False
            try:
                _, writable, _ = select.select([], [fd], [], remaining)
            except (OSError, ValueError):
                return False
            if not writable:
                return False

    def _write(self, payload: bytes) -> bool:
        return self._fd is not None and self._write_to(self._fd, payload)

    def _read_some(self, fd: int) -> str:
        """**待たずに、いま届いている分だけ読む。** ⛔ **ここでは一度も待たない。**

        ⚠️ **待つのは `pump` の期限の側である。** 読む側が自分で待つと、
        ソケットの見張りを止める——**判定は1秒待てるが、事象は待てない。**
        ⚠️ **試験台（普通のファイル）では先頭から読む**——書き込みは `O_APPEND` なので
        位置は動かず、先に置いた判定を読める。tty は `ESPIPE` を返すので、
        そのときは今の位置から読む。
        """
        try:
            os.lseek(fd, 0, os.SEEK_SET)
        except OSError:
            pass
        out = b""
        while True:
            try:
                ready, _, _ = select.select([fd], [], [], 0.0)
            except (OSError, ValueError):
                break
            if not ready:
                break
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                break
            except OSError:
                break
            if not chunk:
                break
            out += chunk
        return out.decode("ascii", "replace")

    def _settle(self, at: float) -> None:
        """**基板自身の判定を、1行にする。** ⛔ **届いた時点で閉じる。**

        ⚠️ **2つの行は別である**: `verdict` が `None` なら**基板は何も言わなかった**、
        `{"applied": …, "refused": 0, "clamped": 0}` なら**言った**。
        **「断らなかった」と「何も言わなかった」を、同じ行にしない。**
        """
        if self._verdict_at is None or self._fd is None:
            return
        self._verdict_text += self._read_some(self._fd)
        found = readback.verdict(self._verdict_text)
        if found is None and at < self._verdict_at:
            # ⚠️ **まだ届いていない。** 上限まで握らず、短い期限で見に戻る。
            self._verdict_next = at + VERDICT_POLL
            return
        emit({
            "neck": self._verdict_name,
            "verdict": found,
            "read": _seen(self._verdict_text),
            "at": at,
        })
        self._close()

    def _probe(self, fd: int) -> tuple[bool, Pose | None, str]:
        """**`bench pos` を書き、答えを `PORT_WAIT` まで読む。** ⛔ **上限を越えない。**

        ⚠️ **3つを返す**: **基板が何か答えたか**、**姿勢が読めたか**、そして
        **その窓のあいだに実際に届いた文字**である。
        ⛔ **この3つを混ぜない**——`bench: yaw=no answer pitch=no answer` は
        **コンソールが答えた**（サーボが答えなかった）のであり、沈黙ではない。

        ⚠️ **3つ目は 2026-10-19 に足した。** その日、レールの電源サイクル以降の13回の問いのうち
        7回が `heard: false` で終わり、**ログは「何も届かなかった」としか言えなかった**
        ——**基板が別の行を返していたのか、行が繋がって拒まれていたのか、
        何も届いていなかったのかを、区別する手立てが無かった。**
        ⇒ **届いた文字を残す。** ⛔ **捨てた文字は、次に尋ねたときに捨てられる。**

        ⚠️ **尋ねる前に、溜まっていた出力を捨てる。** 読まなかった `alive` や、
        前の答えを、今の答えとして読まない——**古い姿勢は、無い姿勢より悪い。**
        ⚠️ **普通のファイルは試験台である。** tty では `lseek` が失敗するので、
        そのときだけ捨てる（ファイルでは、先に置いた答えを読むため先頭へ戻る）。
        """
        try:
            os.lseek(fd, 0, os.SEEK_SET)
        except OSError:
            # ⚠️ **tty である。** 読めるものは、今の答えではない。
            while True:
                try:
                    if not os.read(fd, 4096):
                        break
                except BlockingIOError:
                    break
                except OSError:
                    break
        if not self._write_to(fd, readback.QUERY):
            return False, None, ""
        try:
            # ⚠️ **試験台（普通のファイル）では、先頭から読む。** tty は `ESPIPE` を返す。
            os.lseek(fd, 0, os.SEEK_SET)
        except OSError:
            pass
        deadline = time.monotonic() + PORT_WAIT
        text = ""
        reasked = False
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                return readback.answered(text), readback.parse(text), _seen(text)
            try:
                ready, _, _ = select.select([fd], [], [], remaining)
            except (OSError, ValueError):
                return readback.answered(text), readback.parse(text), _seen(text)
            if not ready:
                return readback.answered(text), readback.parse(text), _seen(text)
            try:
                chunk = os.read(fd, 256)
            except BlockingIOError:
                continue
            except OSError:
                return readback.answered(text), readback.parse(text), _seen(text)
            if not chunk:
                return readback.answered(text), readback.parse(text), _seen(text)
            text += chunk.decode("ascii", "replace")
            pose = readback.parse(text)
            if pose is not None:
                return True, pose, _seen(text)
            # ⚠️ **問いが行として届かなかったなら、1回だけ尋ね直す。**
            #    2026-10-19 に測った: 基板の `ConsoleTask` は `HandleFrame` の中で
            #    `PlayGesture` と `sound::play` を**その場で**呼ぶので、身振りや音の
            #    あいだは STDIN を読まない。**その窓に書いた行は、次の行と繋がるか、
            #    落ちる**——記録に残った答えは `console: unknown command` と
            #    `frame: refused (malformed)` であった。⇒ **繋がった行は、問いを
            #    飲み込む。** 尋ね直しは同じ `PORT_WAIT` の内側で、1回だけである。
            if (not reasked and not readback.answered(text)
                    and _MANGLED.search(text)):
                reasked = True
                self._write_to(fd, readback.QUERY)

    def take(self, decision: Decision, at: float) -> bool:
        """**身振りを引き受ける。** ⚠️ **流し始めたときだけ `True`。**

        ⛔ **枠と姿勢の行で、同じ身振りを2度動かさない。** `True` を返したら、
        呼ぶ側は枠の `gesture` を `None` にして送る——基板の `PlayGesture` は
        メインループを数秒塞ぎ、その間の姿勢は遅れて適用される。

        ⚠️ **始点の優先は3つ**: **いま尋ねた姿勢**（最も新しく、最も確か）→ 最後に出した行
        （流れが終わった後も残る）→ 基板に演じさせた身振りの終わり（推測）。
        ⛔ **尋ねるのは、身振りを引き受けた後である**——割り込まれた流れを止め、
        ポートを開き、その同じ fd で尋ねる。**2度開かない。**
        """
        if self.port is None or decision.gesture is None:
            return False

        if self._stream.running:
            # ⚠️ **割り込まれた動きも、送った数として残す。**
            self._stream.stop(at)
            summary = self._stream.take_summary()
            self._close()
            if summary is not None:
                emit({"neck": summary.name, "applied": summary.applied,
                      "late": summary.late, "held": summary.held,
                      "at": summary.at, "interrupted": True})

        # ⛔ **開けなければ、流さない。** 枠が身振りを運び、基板が演じる——
        #    開けない端末に、行だけを数えて「送った」と言わない。
        if not self._open():
            self._parked = gestures.ends(decision.gesture)
            return False

        heard, measured, seen = self._probe(self._fd)
        # ⚠️ **1つの問いに、1つの形である。** ⛔ **2026-10-19 まで、成功した探針は
        #    `{"position": [...], "at": …}` という2つ目の形で書かれていた**——
        #    `heard` を持たないので、`projects/stackchan/day/summary.py` は
        #    **成功した読み戻しを1行も数えられず、58行を `unreadable` に入れていた**
        #    （その日のログ: `readbacks 46`、`positions 0`、`unreadable 58`）。
        #    ⇒ **読み戻しが段7の計器であるなら、読者はその行を読めなければならない。**
        # ⛔ **成功は `heard: True` である**——位置が読めたなら、コンソールは答えた。
        emit({
            "position": (None if measured is None else
                         [measured.yaw_tenths, measured.pitch_tenths]),
            "heard": heard,
            "read": _seen(seen),
            "at": at,
        })

        starts = measured
        if starts is None:
            starts = self._stream.last_pose
        if starts is None:
            starts = self._parked
        if starts is None:
            # ⛔ **位置を知らないまま流さない。** 最初の1回は基板に演じさせる。
            self._close()
            self._parked = gestures.ends(decision.gesture)
            return False

        plan = gestures.plan(decision.gesture, starts, period=self._period)
        if gestures.still(plan) or gestures.within_floor(plan):
            # ⛔ **動かない列は、流さない。** 2026-10-19、85の身振りのうち38が
            #    これだった——首は `look_up` に停まっており、`look_up` がまた来る。
            #    ⚠️ **それでも身振りは引き受ける**（`True` を返す）: 枠が運べば、
            #    基板の `PlayGesture` がメインループを数秒塞ぐ——**動かない姿勢のために。**
            # ⚠️ **2つの問いを並べる。** `still` は列が1歩も動かないこと（数を使わない）、
            #    `within_floor` は動くが**この機体が動かさない**こと（測った床）。
            #    ✅ **位置を尋ねて答えが返る日は、後者が主である**: `look_up` の 80 は
            #    `93` と読まれ、列は動くが、サーボは 4 counts では動かない。
            self._parked = plan.ends
            self._close()
            emit({
                "neck": decision.gesture,
                "from": [starts.yaw_tenths, starts.pitch_tenths],
                "to": [plan.ends.yaw_tenths, plan.ends.pitch_tenths],
                "skipped": "no motion",
                "at": at,
            })
            return True
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
        """**期限の来た行を、すべて書く。** ⚠️ 終わったら、要約を1行だけ残す。

        ✅ **0.19.38 から、要約の後にもう1つある**——**基板自身の判定**である。
        ⛔ **閉じる前に読む。** 閉じた後では、基板が印字した行は誰のものでもない。
        """
        if self._fd is None:
            return
        if self._verdict_at is not None:
            # ⚠️ **流しは終わっている。** 判定が届いたか、期限が来たかだけを見る。
            self._settle(at)
            if self._fd is None:
                return
        while True:
            line = self._stream.line(at)
            if line is None:
                break
            if not self._write(line):
                # ⛔ **書けなかった列を、書いた列として続けない。**
                emit({"neck": self._stream.name, "sent": False, "at": at})
                self._stream.stop(at)
                self._close()
                break
        summary = self._stream.take_summary()
        if summary is not None:
            emit({"neck": summary.name, "applied": summary.applied,
                  "late": summary.late, "held": summary.held, "at": summary.at})
            # ✅ **最後の行を書いた後、基板は自分の数を印字する。**
            #    ⛔ **ここで閉じれば、その行は誰にも読まれない**——2026-10-19 まで、
            #    そうだった。⇒ **判定の期限を置き、届いた時点で閉じる。**
            self._verdict_at = summary.at + VERDICT_WAIT
            self._verdict_next = summary.at
            self._verdict_name = summary.name
            self._verdict_text = ""
            self._settle(at)


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

    ⛔ **枠の前に、改行を1つ置く。2026-10-19 に測った理由で置く。**
    基板のコンソールは `\\n` までを溜める（`main.cpp` の `ConsoleTask`）ので、
    **終端の欠けた切れ端が溜めの中に残っていると、次に書いた行はそれに繋がれて壊れる。**
    その日、同じ枠を単独で書けば通り、切れ端の後ろに書けば
    `frame: refused (malformed)` で落ちることを、この機体で確かめた。
    ⇒ **空行は基板が捨てる**（`g_line_len > 0` のときだけ行を渡す）ので、1バイトで足りる。
    ⚠️ **問い（`bench pos`）には置かない**——そこには既に尋ね直しが在り、
    そちらは「答えを読み直す」ことで直る（0.19.33）。枠は、尋ね直す相手ではない。
    """
    line = frame_line(frame)
    sent = send_line(port, "\n" + line) if port is not None else False
    emit(frame_row(line, at, session, sent))


def decide(room: Room, session: str, event: str, at: float,
           hour: int | None = None) -> Decision:
    """**事象1つを、部屋に渡す。** ⚠️ **静かな時間は、この縁が読む。**

    ⛔ **中核は時計を持たない**（`room.py`）。`quiet.py` の規則が**真偽として**渡り、
    **音の欄だけを閉じる**——顔も光も首も従わない。

    ⚠️ **`hour` は試験のために在る。** 渡さなければ、**壁時計のローカル時を1度読む**。
    ⇒ **渡せば、その時が結論を決める**——**時計を止めずに、境界を測れる。**
    """
    if hour is None:
        hour = datetime.datetime.now().hour
    return room.offer(session, event, at, quiet=is_quiet(hour))


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

    decision = decide(room, session, event, at)
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
                        help="whether the speaker channel is on (default: off); "
                             "the quiet hours 21:00-05:00 still close it")
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
