# -*- coding: utf-8 -*-
"""リポジトリ直下の `conftest`。

⚠️ **これがやっているのは1つだけである**——**`tests/` からリポジトリの根を `import` できるようにする。**
pytest は `rootdir` を `sys.path` に入れないので、`tests/` の外に置いたモジュール
（`tools/` など）は、これが無いと `import` できない。

⚠️ **そして、このファイルは何も検査しない。** **`tests/` に試験が入ったので、
このファイルは「置き場」から「土台」になった**——**実測 2026-09-27、8ファイル・80テスト。**
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
