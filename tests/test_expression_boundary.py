# -*- coding: utf-8 -*-
"""⛔ **表現の族が、機体へ降りないこと。**

[02_調査/02] §9.2 の逐語——**「機体へ降ろす段で端の速度ゼロの族へ写す。
Back / Elastic / Bounce をそのまま機体へ通さない」**。`engine/trajectory/easing.py` は
**表現の族**（CSS の名前つきベジェ）を持ち、**それは機体の族ではない**——
**Back / Elastic / Bounce は開始時に逆走する。画面では「ため」に見えるが、機体では逆向きの加速度である。**

⚠️ **そして [08_語彙と日本語] §4 が、この検査を「鳴らない」の欄に置いていた**——
**「CSS 族の名前が、Backend の入力に現れないか」は `grep` で書ける**、と §4 自身が書いている。
**このファイルは、その1本である。**

⛔ **但し §4 が想像していた形では書かない。** §4 は
**「`engine/backend/` のどれかが `engine/trajectory/easing.py` を import していないか」**と書いた。
**それをそのまま測ると、緑になる理由が規則とずれる**——`engine/backend/transmit.py` は
`..trajectory.plan` を輸入しており、**その1行が `engine/trajectory/__init__.py` を走らせ、
その `__init__` が `easing` を再輸出する。** ⇒ **モジュールは、実際に読み込まれている**
（**この事実は下の `test_loading_a_backend_module_also_loads_the_expression_module` が押さえる**）。
**ゆえにこの検査が見るのは「モジュール」ではなく「名前」である**——
**表現の語が、機体の側に書かれないこと。**

⚠️ **散文は鳴らさない。** AST で見るが、**docstring は除く**——除かないと、この検査は
**自分が書いた説明文に当たる**（`CLAUDE.md`「自分が今足した語を検索語にすると必ず当たる」）。
**見るのは、コードの中で値になっている文字列だけである。**
⚠️ **そして `quality` の説明文のように、語を名指しする散文はリポジトリに既に在る**——
**あれを鳴らす検査は、正しい文書を鳴らし続ける。**

⛔ **緑は「守られている」ではない。** いま `engine/backend/` は表現の族を1度も名指していない——
**「まだ破っていない」である。**
"""
from __future__ import annotations

import ast
import json
import pathlib
import subprocess
import sys

from engine.trajectory.easing import CURVES

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKEND = ROOT / "engine" / "backend"
SCHEMA = ROOT / "schemas" / "motion-intent.schema.json"

#: ⛔ **語彙である。2つ書かない**——**CSS の名前は `CURVES` から取る**（あちらが正典である。
#: **増えれば、この検査も増える**）。**残りは規則そのものの理由である**——
#: [02_調査/02] §9.2 が名指しした3つ。⚠️ **その3つは、リポジトリの中に名前を持たない**
#: （**`CURVES` には入っていない**——**入れれば、この検査が守るものが正典になる**）。
OVERSHOOT = frozenset({"back", "elastic", "bounce"})

#: ⚠️ **区切りを落として比べる**（`ease-out` / `easeOut` / `ease_out` を1つと見る）。
EXPRESSION_WORDS = frozenset(
    word.replace("-", "").replace("_", "").lower() for word in (set(CURVES) | OVERSHOOT)
)

#: `easing.py` が外へ出している名前。**輸入を、名前の側から見るためである**
#: （`from ..trajectory.easing import curve` は、モジュール名を書かずに済む）。
EXPRESSION_EXPORTS = frozenset({"CURVES", "cubic_bezier", "curve", "MAPPING_TO_MACHINE"})


def _normalise(word: str) -> str:
    return word.replace("-", "").replace("_", "").lower()


def imported_expression_names(tree: ast.AST) -> set[str]:
    """**`easing` を名指す輸入**——モジュールとしても、名前としても。"""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[-1] == "easing":
                found.add(f"from {(node.module or '')} import ...")
            for alias in node.names:
                if alias.name in EXPRESSION_EXPORTS:
                    found.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "easing" in alias.name.split("."):
                    found.add(f"import {alias.name}")
    return found


def _docstring_strings(tree: ast.AST) -> set[int]:
    """⚠️ **散文を、値と読み違えない。** docstring の `Constant` の住所を集める。"""
    prose: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            first = body[0] if body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                prose.add(id(first.value))
    return prose


def written_expression_words(tree: ast.AST) -> list[tuple[int, str]]:
    """**コードの中で値になっている表現の語**——docstring は数えない。"""
    prose = _docstring_strings(tree)
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in prose:
            if _normalise(node.value) in EXPRESSION_WORDS:
                found.append((node.lineno, node.value))
    return found


def _sources(root: pathlib.Path) -> dict[str, ast.AST]:
    files = sorted(root.rglob("*.py"))
    assert files, f"⛔ {root} に .py が1つも無い——検査が空を回っている"
    return {
        path.relative_to(ROOT).as_posix(): ast.parse(path.read_text(encoding="utf-8"))
        for path in files
    }


def schema_words(doc: object) -> list[str]:
    """**型が名乗っている語**——`description`（散文）は見ない。"""
    found: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "description":
                    continue
                if key == "properties" and isinstance(value, dict):
                    for name in value:
                        if _normalise(name) in EXPRESSION_WORDS:
                            found.append(f"{path}/properties/{name}")
                elif key == "enum" and isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and _normalise(item) in EXPRESSION_WORDS:
                            found.append(f"{path}/enum/{item}")
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}/{index}")

    walk(doc, "$")
    return found


def test_the_vocabulary_is_not_empty():
    """⛔ **空の語彙で検索すると、必ず緑になる。**"""
    assert EXPRESSION_WORDS >= {"ease", "easeinout", "linear", "back", "elastic", "bounce"}, (
        f"語彙が痩せている: {sorted(EXPRESSION_WORDS)}"
    )
    assert len(CURVES) == 5, f"正典の族が5つでない: {sorted(CURVES)}"


def test_no_backend_module_reaches_for_the_expression_module():
    """⛔ **`engine/backend/` は、表現の族を名指ししない。**"""
    hits = []
    for rel, tree in _sources(BACKEND).items():
        for name in sorted(imported_expression_names(tree)):
            hits.append(f"{rel}: {name}")
    assert not hits, "表現の族を、機体の側が名指している:\n" + "\n".join(hits)


def test_no_expression_word_is_written_into_the_backend():
    """⛔ **`engine/backend/` は、表現の語を値として持たない。**"""
    hits = []
    for rel, tree in _sources(BACKEND).items():
        for line, word in written_expression_words(tree):
            hits.append(f"{rel}:{line}: {word!r}")
    assert not hits, "表現の語が、機体の側に書かれている:\n" + "\n".join(hits)


def test_the_import_detector_fires_on_a_source_that_does_it():
    """⛔ **鳴らない検査は、検査ではない。**"""
    by_module = ast.parse("from ..trajectory.easing import curve")
    by_name = ast.parse("from ..trajectory import CURVES")
    by_root = ast.parse("import engine.trajectory.easing")
    for tree in (by_module, by_name, by_root):
        assert imported_expression_names(tree), "禁じた輸入を、検出器が拾っていない"
    assert not imported_expression_names(ast.parse("from ..trajectory.plan import Trajectory")), (
        "⚠️ **禁じていない輸入を、拾っている**"
    )


def test_the_word_detector_fires_on_a_source_that_does_it():
    """⛔ **そして、散文では鳴らないこと**——両方を、ここで主張する。"""
    assert written_expression_words(ast.parse('x = curve("ease-out")')), "値の語を拾っていない"
    assert written_expression_words(ast.parse('x = curve("easeInOut")')), "綴りの違いを拾っていない"
    assert not written_expression_words(ast.parse('"""これは ease-out の説明である。"""')), (
        "⛔ **散文を鳴らしている**——この検査は、正しい説明文に当たり続ける"
    )


def test_the_intent_type_names_no_expression_word():
    """⛔ **型が窓口である**——**機体へ渡る語は、まずここを通る。**

    ⚠️ **`quality` の説明文は語を名指ししている**（**あれは散文である**）。
    そして **`quality` が開いていること自体は、[`test_intent.py`] が既に主張している**——
    **この検査は、そこを二度は数えない。**
    """
    doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
    enums = [
        node["enum"]
        for node in (doc["$defs"]["move"]["properties"]["dof"],)
        if isinstance(node.get("enum"), list)
    ]
    assert enums and enums[0], "⚠️ **型に `enum` が1つも無い**——検索する先が空である"
    assert not schema_words(doc), f"型が表現の語を名乗っている: {schema_words(doc)}"


def test_the_schema_detector_fires_on_a_schema_that_names_one():
    """⛔ **鳴らない検査は、検査ではない**（型の側）。"""
    assert schema_words({"properties": {"ease-out": {"type": "number"}}})
    assert schema_words({"$defs": {"move": {"properties": {"dof": {"enum": ["pitch", "bounce"]}}}}})
    assert not schema_words({"description": "ease-out という語は使わない", "properties": {"dof": {}}}), (
        "⚠️ **散文を鳴らしている**"
    )


def test_loading_a_backend_module_also_loads_the_expression_module():
    """⚠️ **この検査の境界を、機械で押さえる。**

    **`engine/backend/transmit.py` は `..trajectory.plan` を輸入している。**
    その1行が `engine/trajectory/__init__.py` を走らせ、**その `__init__` が `easing` を再輸出する。**
    ⇒ **`engine.trajectory.easing` は、機体の側を読み込むだけで読み込まれる。**

    ⛔ **これは欠陥ではない。** **`__init__` が再輸出するのは、[`tests/test_easing.py`] と
    `engine/trajectory/__init__.py` の公開の形の話である。** **ここに置くのは、
    「モジュールが無い」と読まれないためである**——**上の2つが主張しているのは、
    「名指ししていない」であって、「読み込まれていない」ではない。**

    ⚠️ **この検査が落ちたとき、コードの欠陥ではない。****事実が変わったのである**——
    **`__init__` が `easing` を遅延させるようになったなら、この docstring と
    `tests/README.md` の1行を書き換える。消してはいけない。**
    """
    code = "import sys, engine.backend.transmit; print('engine.trajectory.easing' in sys.modules)"
    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert done.stdout.strip() == "True", (
        "⛔ **事実が変わった**——`engine.trajectory.easing` は、もう輸入の副作用では読み込まれない。\n"
        f"stdout={done.stdout!r} stderr={done.stderr!r}"
    )
