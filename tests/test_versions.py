# -*- coding: utf-8 -*-
"""⚠️ **版は3点一致**——**この規則を、初めて鳴らす検査である。**

`CLAUDE.md` の Git 節はこう書いている——**「The manifest version tracks `HISTORY.md`.」
そして「Two files, one version — and a third value that must agree: the newest
`## <version>` in `HISTORY.md`, which is the first one, because that file is
written newest-first.」**

⚠️ **2点は既に見えていた。** `tests/README.md` が書いているとおり、
`claude plugin validate --strict .` が `.claude-plugin/plugin.json` と
`.claude-plugin/marketplace.json` を**突き合わせている**。

⛔ **3点目は、2026-09-28 まで、どこも見ていなかった。**
**`HISTORY.md` の先頭の `## <版>` だけが、誰にも見られていなかった。**
⇒ **規則だけが在って、検査が無かった**——**この器がいちばん嫌う形である。**

⚠️ **なぜ危ないか。** 3つのうち2つが一致していれば `validate` は緑を返す。
**そして、緑はいちばん読まれる。** 古い `HISTORY.md` は、
**「この版で何が入ったか」を読む唯一の場所である**——
⛔ **`README.md` と `HISTORY.md` が別の版を指していても、誰も鳴らさなかった。**

⚠️ **そして、このリポジトリは既にこの形を1度踏んでいる**（`HISTORY.md` の `## 0.6.0`）。
**決定が、コードの中の1行を偽にした。** 4つの検査はどれも鳴らさなかった。
⇒ **だからここは、読む者が見落とす場所ではなく、機械が見る場所に置く。**

⚠️ **この検査が捕まえないもの。**

- ⛔ **版が正しいかどうか。** 3つが一致することしか言わない。
  **その版に値する中身が入ったかは、この検査の外である。**
- ⛔ **`HISTORY.md` の2番目以降の版。** 見ているのは**先頭の1つだけ**である。
  **途中の版が飛んでいても、重複していても、この検査は鳴らない**——
  **それは「いちばん新しい版」の問いではない。**
- ⛔ **`i18n-version`**（文書のミラーの版）。**別の数を数えている**——
  `tools/check_i18n.py` が見るものであり、**版3点とは無関係である。**
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
HISTORY = ROOT / "HISTORY.md"

#: ⚠️ **`## 0.6.0 — 2026-09-28 語彙が…` の形。** **見出しの水準は2である**——
#: `# HISTORY — …` は水準1であり、**版ではない。**
_VERSION_HEADING = re.compile(r"^##[ \t]+(\d+\.\d+\.\d+)(?![0-9.])")


def newest_version(text: str) -> str | None:
    """`HISTORY.md` の本文から、**いちばん新しい版**を返す。**見つからなければ `None`。**

    ⚠️ **このファイルは新しい順に書かれている**（`CLAUDE.md` の Git 節）。
    ⇒ **「いちばん新しい」は「最初に現れる」である。**

    ⛔ **`None` を返す道を残してある。** **空を緑にしないためである**——
    見つからなかったときに `""` か何かを返せば、3点は一致してしまう。
    """
    for line in text.splitlines():
        found = _VERSION_HEADING.match(line)
        if found:
            return found.group(1)
    return None


def _read(path: Path) -> str:
    """⛔ **ファイルが無ければ落ちる。** `skip` は使わない——**無いことは緑ではない。**"""
    assert path.is_file(), f"⛔ **無い**: {path}"
    return path.read_text(encoding="utf-8")


def _manifest_version(path: Path) -> str:
    data = json.loads(_read(path))
    if path.name == "plugin.json":
        return data["version"]
    #: ⚠️ **`marketplace.json` の版は、`plugins` の各項の中に在る**
    #: （`metadata` には版が無い）。**取り違えると `KeyError` になる。**
    plugins = data["plugins"]
    assert len(plugins) == 1, f"⚠️ **項が1つでない**: {len(plugins)}"
    return plugins[0]["version"]


def test_the_parser_finds_nothing_when_there_is_no_heading() -> None:
    """⛔ **この検査自身が、空の入力で緑にならないことを主張する。**

    **検算器は「相手が空なら落ちる」を入れよ**——この工房の規則である。
    ここが `""` を返すようになった日、下の3つは**全部いっしょに緑になる。**
    """
    assert newest_version("# HISTORY — 開発履歴\n\n本文だけ。\n") is None
    #: 水準が違えば版ではない。
    assert newest_version("# 0.6.0\n") is None
    assert newest_version("### 0.6.0 — 深い見出し\n") is None
    #: ⚠️ **前置きの数字を版と読まない。**
    assert newest_version("## 0.6.0.1 — 4つ目の数\n") is None


def test_the_parser_reads_the_heading_this_repository_actually_writes() -> None:
    """⚠️ **実物の見出しを1つ、逐語で置く。** 形が変われば、ここが落ちる。"""
    assert newest_version("## 0.6.0 — 2026-09-28 語彙が目録になった\n") == "0.6.0"


def test_history_has_a_version_heading_at_all() -> None:
    """⛔ **先に見つかることを主張する。** **見つからなければ、以下の3つは意味を持たない。**"""
    found = newest_version(_read(HISTORY))
    assert found is not None, "⛔ **`HISTORY.md` に `## <版>` が1つも無い**"
    assert re.fullmatch(r"\d+\.\d+\.\d+", found)


def test_the_two_manifests_agree() -> None:
    """⚠️ **`validate --strict` も見ている2点である。** それでも書く——
    **この検査は pytest の中で走る**ので、**道具を持たない者にも読める。**"""
    assert _manifest_version(PLUGIN) == _manifest_version(MARKETPLACE)


def test_history_agrees_with_the_manifests() -> None:
    """⛔ **2026-09-28 まで、誰も見ていなかった1点である。**"""
    assert newest_version(_read(HISTORY)) == _manifest_version(PLUGIN)
