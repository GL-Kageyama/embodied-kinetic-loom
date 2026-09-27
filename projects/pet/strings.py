# -*- coding: utf-8 -*-
"""**縁の言葉。** 表は `locales/`、読み手はここである。

⛔ **この層が要る理由。** `engine/` は `os` を import しない——`tools/purity.py` が
**「環境（environ）」**として禁じている。**ゆえに言語の解決は核の中に置けない。**
決定論的な核が返すのは**コード**であり（`Rejection.code`）、
**それを人間の文にするのは、核の外側の仕事である。**

⚠️ **言語の決まり方（3段。姉妹5本と同じ形である）:**

    1. `--lang {en,ja,zh}`
    2. 環境変数 `EMBODIED_KINETIC_LOOM_LANG`
    3. 既定 `en`——`CLAUDE.md`「**既定の言語は `en`**」

⛔ **`resolve()` は環境を読まない。** 読むのは入口（`__main__.py`）だけである——
**`time` とまったく同じ形である**: 外の世界を読むのは縁で、核は値を受け取る。
⇒ **ゆえに順序は、環境変数を触らずに検査できる**（`tests/test_strings.py`）。

⚠️ **引けない語は、黙って既定へ落ちない。** `text()` は送出する。
**落ちれば、表の穴が検査で鳴る**——**黙って落ちれば、穴は誰にも見えない**
（`CLAUDE.md`「空白は中立ではない」）。
"""
from __future__ import annotations

import json
import pathlib
import sys

__all__ = ["SUPPORTED", "DEFAULT", "ENV_VAR", "TABLE_DIR", "resolve", "load",
           "text", "template", "refusal"]

#: ⚠️ **姉妹5本と同じ3言語。** 文書のミラーが既に3言語である。
SUPPORTED = ("en", "ja", "zh")

#: ⛔ **既定は `en`。** `CLAUDE.md` の Language 節がそう定めている。
DEFAULT = "en"

#: ⚠️ **環境変数の名。** 姉妹の作法（`ELEVATE_DRAFT_ENGINE_LANG`）に倣う。
ENV_VAR = "EMBODIED_KINETIC_LOOM_LANG"

#: ⚠️ **表はリポジトリの根に在る**——`projects/pet/strings.py` から3つ上である。
TABLE_DIR = pathlib.Path(__file__).resolve().parents[2] / "locales"

_cache: dict[str, dict] = {}


def resolve(cli: str | None = None, env: str | None = None) -> str:
    """**どの言語で話すかを決める。** ⛔ **環境を読まない**——値として受け取る。

    順序は `cli` → `env` → `DEFAULT`。⚠️ **知らない言語は既定へ落ち、stderr で告げる。**
    **黙って落ちると、綴りを間違えた者は「その言語が無い」ことに気づけない。**
    """
    lang = (cli or env or DEFAULT).strip().lower()
    if lang not in SUPPORTED:
        sys.stderr.write(
            f"Warning: unsupported language {lang!r}, "
            f"falling back to {DEFAULT!r}（supported: {', '.join(SUPPORTED)}）\n"
        )
        return DEFAULT
    return lang


def load(lang: str | None = None) -> dict:
    """表を1つ読む。⚠️ **正典の名で引く**——`None` は `DEFAULT` である。"""
    name = resolve(lang)
    if name not in _cache:
        path = TABLE_DIR / f"{name}.json"
        _cache[name] = json.loads(path.read_text(encoding="utf-8"))
    return _cache[name]


def template(section: str, key: str, lang: str | None = None) -> str:
    """⛔ **生の雛形を返す。** 穴が埋まっていないことに意味がある場合だけ使う。"""
    table = load(lang)
    if section not in table or key not in table[section]:
        raise KeyError(
            f"表に無い語である: {section}.{key}"
            f"（{resolve(lang)}。在るのは {sorted(table.get(section, {}))}）"
        )
    return table[section][key]


def text(section: str, key: str, lang: str | None = None, **fmt) -> str:
    """**文を1つ引く。** ⚠️ `fmt` が空なら、雛形をそのまま返す。

    ⛔ **無い語は送出する。** **既定へ落ちる版では、訳し忘れが永久に見えない。**
    ⚠️ **第2引数が `key` なのは、`name` が穴の名と衝突するからである**——
    `report()` は `name=<演技の名>` を穴として渡す。
    """
    out = template(section, key, lang)
    return out.format(**fmt) if fmt else out


def refusal(rejection, lang: str | None = None) -> str:
    """**弾かれた理由を、人間の文にする。**

    ⚠️ **核が渡すのはコードと値だけである**（`Rejection.code` / `.values`）。
    **文を持っているのは表の側である**——ゆえにここで初めて言葉になる。
    """
    return text("refusal", rejection.code, lang, **rejection.mapping())
