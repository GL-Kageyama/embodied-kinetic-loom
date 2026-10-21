# -*- coding: utf-8 -*-
"""**口 —— 本体が書いた1文を、体のスピーカーで言わせる。**

`python3 -m projects.stackchan_next.mouth '長かった。25回、書いてた。'`

⚠️ **なぜ本体が書くか。** 設計 §11.2 が「言葉は本体のものである」と決めており、
**規則の層は日本語を綴れない**——綴れば、言語も文脈も知らない側が
「ミニロボットアシスタントの口調」（§22.7）を決めることになる。⇒ **文は本体が書き、
ここはその1文をデーモンへ渡すだけである**（§22.10）。

⛔ **鳴らすのはデーモンである。** 回線（基板が dial してきた TCP）を持っているのは
デーモンであり、**2人目の書き手を作らない**——`Link.writing` の錠は1つである（§22.9）。

⛔ **黙って失敗しない**（フックとは逆である）。**フックは欠けても体の故障ではない**が、
**この道具は「鳴らなかったこと」を言うために呼ばれている**。⇒ **どの道も1語を印字する:**
`queued` / `night` / `no-board` / `busy` / `refused:<符号>` / `no-daemon`。
⚠️ **どの語も、文そのものを含まない。**

⚠️ **`queued` と `night` だけが 0 で終わる。** `night` は故障ではない——**規則が
働いた日である**（§17.4 (c)：夜は候補を声にしない）。
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys

from ..daemon.room import mouth_socket_path

#: ⚠️ **待つのは返事の1行だけである。** 声の糸は即答する（合成は自分の糸で走る）。
#: ⛔ **合成をここで待たない**——待てば、本体のターンが声の長さだけ止まる。
REPLY_WAIT = 1.0

#: ⚠️ **0 で終わる語は2つだけである。** 残りは「鳴らなかった」である。
QUIET = frozenset({"queued", "night"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m projects.stackchan_next.mouth",
        description=(
            "Say one sentence through the body's speaker. The sentence is "
            "written by the caller: the rules layer never composes words. "
            "Prints one word and exits 0 only for queued or night."
        ),
    )
    parser.add_argument("text", nargs="+", help="the one sentence to say")
    parser.add_argument("--socket", default=None, metavar="PATH",
                        help="the mouth's Unix socket "
                             "(default: %(default)s)")
    return parser


def state_of(reply: bytes) -> str:
    """**返事の1行を、1語にする。** ⛔ **読めない返事は `unreadable` である。**

    ⚠️ **返事が無いことと、返事が違う形であることは、別である**——だが
    **どちらも「鳴ったとは言えない」**ので、この道具は2つを1語に落とす。
    """
    line = reply.partition(b"\n")[0]
    try:
        payload = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return "unreadable"
    if not isinstance(payload, dict):
        return "unreadable"
    state = payload.get("voice")
    if state == "refused":
        # ⚠️ **断りの理由は載せる。** 符号は閉じた集合である（`REFUSAL_CODES`）。
        code = payload.get("error")
        return f"refused:{code}" if isinstance(code, str) else "refused"
    if not isinstance(state, str):
        return "unreadable"
    return state


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    text = " ".join(args.text).strip()
    path = args.socket or mouth_socket_path(os.getuid())

    line = json.dumps({"text": text}, ensure_ascii=False) + "\n"
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(REPLY_WAIT)
        try:
            client.connect(path)
            client.sendall(line.encode("utf-8"))
            chunks = b""
            while b"\n" not in chunks:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks += chunk
        except OSError:
            # ⛔ **デーモンが居ないことは、故障ではない**（フックと同じ理屈である）。
            #    だが**鳴らなかったことは言う**。
            print("no-daemon")
            return 1

    state = state_of(chunks)
    print(state)
    return 0 if state in QUIET else 1


if __name__ == "__main__":
    raise SystemExit(main())
