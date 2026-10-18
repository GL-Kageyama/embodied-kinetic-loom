# -*- coding: utf-8 -*-
"""**デーモンのログを読み返す。** ⛔ **この計器は、何も動かさない。**

⚠️ **2つに割ってある。** `summary.py` は中核であり、**ファイルも時計も読まない**——
行を渡せば数える。`__main__.py` は縁であり、**パスを開くのはそこだけである**。
✅ **8段目（日々ともに暮らせるか）の「1日を書き留める」は、まだ無い。**
⇒ **これはその日ではない。** その日が来たときに引用できる数を、先に作っておく計器である。
"""
from __future__ import annotations

from .summary import Summary, render, summarize

__all__ = ["Summary", "render", "summarize"]
