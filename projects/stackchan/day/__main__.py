# -*- coding: utf-8 -*-
"""**ログの1本を、数える縁。** `python3 -m projects.stackchan.day <path>`。

⛔ **パスに既定値を置かない。** ログの場所は設置されたジョブ（plist）に1度だけ書かれており、
**ここに2つ目の綴りを作れば、片方が古くなる**（`CLAUDE.md`: 数は1度だけ名指す）。

⚠️ **読むだけである。** ポートを開かず、時計も読まず、何も送らない。
"""
from __future__ import annotations

import sys

from .summary import render, summarize


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        sys.stderr.write("usage: python3 -m projects.stackchan.day <path-to-daemon-log>\n")
        return 2
    try:
        with open(args[0], encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        sys.stderr.write(f"cannot read {args[0]}: {exc}\n")
        return 1
    print(render(summarize(text.splitlines())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
