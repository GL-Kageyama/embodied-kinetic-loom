#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""語彙の写像を検査する——**正典は `references/README.md` の1つの表である。**

⚠️ **この検査は 2026-09-28 に書かれた。** その日 **D-02 に答が出て**、
`references/README.md` は**固定の表ではなく写像**になった。**写像は規則を1つ持つ**
——*語を作らない*——**そして規則は、読むものが無ければ守られているか分からない。**
`references/README.md` がこの検査の名前を先に書き、**検査は同じコミットで来た。**

⚠️ **この検査が読むのは表であって、散文ではない。** 節の見出しも、効いている説明も、
**表そのものではない。** ⛔ **だから訳文の散文が違っても、この検査は鳴らない**
（それは `tools/check_i18n.py` の担当である）。

規則は5つ。**各規則に「鳴る例」と「鳴らない例」が `--self-test` に在る。**

    V0 型           `schemas/motion-intent.schema.json` から自由度の一覧が読める
    V1 表           6列の表が**ちょうど1つ**在る（0でも2つでも鳴る）
    V2 列           見出し・区切り・データのすべてが6列。2行目が区切り行である
    V3 自由度       データ行が1つ以上あり、各行の自由度が**型の名指せるもの**である
    V4 パス         各行の最後の欄が、リポジトリに**実在する**パスである
    V5 ミラー       `-ja` / `-zh` の表が、正典と**行数・自由度の欄・パスの欄**で一致する

⚠️ **V1 は列の数で表を選ぶ。** 見出しの文言は3言語で違うので、選ぶ目印にできない。
**だから同じ6列の表がもう1つ現れたら、選ばずに鳴る**——**黙って片方を選ぶ検査は、
選ばなかったほうを検査していないと言えない。**

⚠️ **V3 は自由度の一覧をスキーマから読む。** この3つの名前をここに写さない——
**同じ規則を2箇所に持てば、片方が更新される**（`tools/purity.py` と同じ理由である）。

⚠️ **V5 が見るのはデータ行だけである。** ⛔ **見出し行は比べない**——**欄の名は訳される**
（`degree of freedom` ＝ `自由度` ＝ `自由度`）。**比べるのは、自由度の欄と使われた場所の欄である。**

⚠️ **V5 はミラーを「正典と一致するか」で見る。** ミラーの行を V3・V4 で**検査し直さない**
——**リポジトリに実在することを要求されるのは正典の行だけである。**
ミラーの務めは正典と同じことを言うことであり、**それだけを見る。**

⚠️ **この検査が捕まえないもの:**
  * ⛔ **写像が正しいかどうか。** 「small forward tilt が +40 カウントである」ことは、
    **この表の外に照合する先が無い。** **書き手の判断を通る往復だけが、検査を持たない段である。**
  * ⛔ **表に無い語が `Motion Intent` に書かれていないか。** それは `references/` を
    **読む側**の話であり、静的に見る方法が無い（**語はスキーマの欄ではない**）。
  * **量と時間の値が妥当か。** 数は選択であり、測定ではない。
  * **訳文の散文が正しいか。**（上に書いたとおり、`check_i18n.py` の担当である）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: 正典。**写像はこの1本の表である。**
CANONICAL = "references/README.md"

#: ミラーの言語接尾辞。**正典は英語なので `en` は無い。**
LANGS = ("ja", "zh")

#: 自由度の一覧を読む先。**この3つの名前はここに書かない。**
SCHEMA = "schemas/motion-intent.schema.json"
DOF_POINTER = ("$defs", "move", "properties", "dof", "enum")

#: 語彙の表の列数。**表はこの数で選ばれる**（見出しの文言は3言語で違う）。
COLUMNS = 6

#: 自由度が入っている欄（0から数える）。**V1 で6列と決めたうえでの位置である。**
DOF_COLUMN = 1

#: 使われた場所が入っている欄。**最後の欄である。**
PATH_COLUMN = 5

FENCE_RE = re.compile(r"^\s*```")
SEPARATOR_RE = re.compile(r"^:?-{1,}:?$")


def mirror_of(rel: str, lang: str) -> str:
    """`README.md` + `ja` → `README-ja.md`（**同じディレクトリに並ぶ**）。"""
    p = Path(rel)
    return str(p.with_name(f"{p.stem}-{lang}{p.suffix}"))


def strip_code(cell: str) -> str:
    """セルから `` ` `` と `**` を落とす。**表の見た目は変えてよいが、意味は変えない。**"""
    return cell.replace("`", "").replace("**", "").strip()


def fences(lines: list[str]) -> list[tuple[int, int]]:
    """(開き行の添字, 閉じ行の添字) を返す。**閉じないフェンスは無視する。**"""
    out: list[tuple[int, int]] = []
    opened = None
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            if opened is None:
                opened = i
            else:
                out.append((opened, i))
                opened = None
    return out


def inside_fence(lines: list[str]) -> set[int]:
    """フェンスの中にある行の添字。**表を数えるとき、これを除く。**"""
    covered: set[int] = set()
    for a, b in fences(lines):
        covered.update(range(a, b + 1))
    return covered


def split_row(line: str) -> list[str]:
    """`| a | b |` → `["a", "b"]`。"""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def tables(lines: list[str]) -> list[tuple[int, list[list[str]]]]:
    """`|` で始まる行の連続を1つの表とする。**フェンスの中は数えない。**

    ⚠️ **空行は表を切る。** 見出しと区切りとデータが離れていれば、それは別の表である。
    """
    skip = inside_fence(lines)
    out: list[tuple[int, list[list[str]]]] = []
    opened: tuple[int, list[list[str]]] | None = None
    for i, line in enumerate(lines):
        if i not in skip and line.strip().startswith("|"):
            if opened is None:
                opened = (i, [split_row(line)])
            else:
                opened[1].append(split_row(line))
        elif opened is not None:
            out.append(opened)
            opened = None
    if opened is not None:
        out.append(opened)
    return out


def dof_names(root: Path) -> tuple[tuple[str, ...] | None, str | None]:
    """型から自由度の一覧を読む。**読めなければ理由を返す。**"""
    p = root / SCHEMA
    if not p.is_file():
        return None, f"{SCHEMA} が無い"
    try:
        schema = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"{SCHEMA} が JSON として読めない（{e.__class__.__name__}）"
    node = schema
    for key in DOF_POINTER:
        if not isinstance(node, dict) or key not in node:
            return None, f"{' → '.join(DOF_POINTER)} が無い"
        node = node[key]
    if not isinstance(node, list) or not node or not all(isinstance(x, str) for x in node):
        return None, f"{' → '.join(DOF_POINTER)} が、空か、文字列の並びでない"
    return tuple(node), None


def vocabulary_table(lines: list[str]) -> tuple[int, list[list[str]]] | None:
    """語彙の表（**6列の表**）を1つだけ選ぶ。**0でも2つでも `None` を返す。**

    ⚠️ **選べなかったことを黙って隠さないために、呼ぶ側が鳴らす。**
    """
    cands = [(i, rows) for i, rows in tables(lines) if rows and len(rows[0]) == COLUMNS]
    return cands[0] if len(cands) == 1 else None


def check(root: Path) -> tuple[list[str], dict]:
    """違反の一覧と、**何を見たか**の記録を返す。"""
    bad: list[str] = []
    stats: dict = {
        "table": None,  # (行番号, 行数, データ行数)
        "dof": (),  # 型から読んだ一覧
        "paths": [],  # (パス, 在るか)
        "mirrors": [],  # (rel, 行数, 一致したか)
    }

    # ---- V0 型
    dofs, why = dof_names(root)
    if dofs is None:
        return [f"V0 {SCHEMA}: 自由度の一覧が読めない——{why}"], stats
    stats["dof"] = dofs

    # ---- V1 表
    cpath = root / CANONICAL
    if not cpath.is_file():
        return [f"V1 {CANONICAL}: ファイルが無い"], stats
    text = cpath.read_text(encoding="utf-8")
    lines = text.split("\n") if text.strip() else []
    if not lines:
        return [f"V1 {CANONICAL}: 空である（0バイト、または空白だけ）"], stats

    cands = [(i, rows) for i, rows in tables(lines) if rows and len(rows[0]) == COLUMNS]
    if not cands:
        return [
            f"V1 {CANONICAL}: {COLUMNS}列の表が無い——**語彙の写像が消えている**"
        ], stats
    if len(cands) > 1:
        return [
            f"V1 {CANONICAL}: {COLUMNS}列の表が{len(cands)}つある"
            f"（{[i + 1 for i, _ in cands]} 行目）"
            f"——**どれを語彙とするか決められない**"
        ], stats
    start, rows = cands[0]

    # ---- V2 列
    for n, row in enumerate(rows, start=start + 1):
        if len(row) != COLUMNS:
            bad.append(f"V2 {CANONICAL}:{n}: 列が{len(row)}（{COLUMNS}であること）")
    header = rows[0]
    if len(rows) < 2 or not all(SEPARATOR_RE.match(c) for c in rows[1]):
        bad.append(
            f"V2 {CANONICAL}:{start + 2}: 2行目が区切り行でない"
            f"——**見出しとデータの境目が無い**"
        )

    # ---- V3 自由度 / V4 パス
    data = rows[2:]
    stats["table"] = (start + 1, len(rows), len(data))
    if not data:
        # ⚠️ **空を OK と言わない。**
        bad.append(
            f"V3 {CANONICAL}: データ行が0である"
            f"——**語彙が空になったことを、空のまま通さない**"
        )
    for n, row in enumerate(data, start=start + 3):
        if len(row) != COLUMNS:
            continue  # ⚠️ 列数は V2 が既に鳴らしている。ここで二度鳴らさない。
        dof = strip_code(row[DOF_COLUMN])
        if dof not in dofs:
            bad.append(
                f"V3 {CANONICAL}:{n}: 自由度 `{dof}` を型が名指せない"
                f"（型が持つのは {' / '.join(dofs)}）"
            )
        path = strip_code(row[PATH_COLUMN])
        exists = bool(path) and (root / path).exists()
        stats["paths"].append((path, exists))
        if not path:
            bad.append(f"V4 {CANONICAL}:{n}: 最後の欄が空である（**使われた場所が無い行**）")
        elif not exists:
            bad.append(f"V4 {CANONICAL}:{n}: `{path}` がリポジトリに無い")

    # ---- V5 ミラー
    for lang in LANGS:
        rel = mirror_of(CANONICAL, lang)
        p = root / rel
        if not p.is_file():
            bad.append(f"V5 {rel}: ファイルが無い")
            continue
        mtext = p.read_text(encoding="utf-8")
        mlines = mtext.split("\n") if mtext.strip() else []
        m = vocabulary_table(mlines)
        if m is None:
            bad.append(
                f"V5 {rel}: {COLUMNS}列の表がちょうど1つ無い"
                f"——**正典と比べる相手が決まらない**"
            )
            continue
        _mstart, mrows = m
        # ⚠️ **見出し行は比べない。** 欄の名は訳される——**比べるのはデータ行だけである。**
        mdata = mrows[2:]
        same = True
        if len(mrows) != len(rows):
            bad.append(
                f"V5 {rel}: 行数が違う（正典 {len(rows)} / ミラー {len(mrows)}）"
            )
            same = False
        else:
            for n, (a, b) in enumerate(zip(data, mdata), start=start + 3):
                if len(a) != COLUMNS or len(b) != COLUMNS:
                    continue
                for col, label in ((DOF_COLUMN, "自由度"), (PATH_COLUMN, "使われた場所")):
                    if strip_code(a[col]) != strip_code(b[col]):
                        bad.append(
                            f"V5 {rel}:{n}: {label}の欄が正典と違う"
                            f"（正典 `{strip_code(a[col])}` / ミラー `{strip_code(b[col])}`）"
                        )
                        same = False
        stats["mirrors"].append((rel, len(mrows), same))

    return bad, stats


# --------------------------------------------------------------------------
# 自己検査
# --------------------------------------------------------------------------

DOF_ENUM = ("pitch", "roll", "yaw")
ROW_PATH = "projects/x/motions/a.json"

HEADER_ROW = (
    "| the words | degree of freedom | the amount | the time"
    " | ⛔ the difference | where it was used |"
)
SEP_ROW = "|---|---|---|---|---|---|"


def _row(dof: str = "pitch", path: str = ROW_PATH) -> str:
    return f"| `a word` → `return` | `{dof}` | `+40` counts | `600` ms | **none** | `{path}` |"


def _doc(
    rows: list[str] | None = None,
    *,
    header: bool = True,
    sep: bool = True,
    wide: bool = False,
    extra_table: bool = False,
) -> str:
    """合成の表。**各引数は「壊す」ためのものである。**"""
    body = [_row()] if rows is None else rows
    out = ["# references/", "", "## A section", "", "Some prose.", ""]
    if header:
        out.append(HEADER_ROW)
    if sep:
        out.append(SEP_ROW)
    for r in body:
        out.append(r + (" | extra" if wide else ""))
    if extra_table:
        out += [
            "",
            "| a | b | c | d | e | f |",
            "|---|---|---|---|---|---|",
            "| 1 | 2 | 3 | 4 | 5 | 6 |",
        ]
    return "\n".join(out) + "\n"


def _write_tree(
    root: Path,
    *,
    canon: str | None = None,
    ja: str | None = None,
    zh: str | None = None,
    schema: bool = True,
    path_file: bool = True,
) -> None:
    """合成の木を1本ぶん作る。"""
    (root / "references").mkdir(parents=True, exist_ok=True)
    for lang, body in (("", canon), ("ja", ja), ("zh", zh)):
        rel = CANONICAL if not lang else mirror_of(CANONICAL, lang)
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_doc() if body is None else body, encoding="utf-8")
    if schema:
        p = root / SCHEMA
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"$defs": {"move": {"properties": {"dof": {"enum": list(DOF_ENUM)}}}}}),
            encoding="utf-8",
        )
    if path_file:
        q = root / ROW_PATH
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text("{}\n", encoding="utf-8")


def self_test() -> int:
    """**各規則に「鳴る例」と「鳴らない例」。**"""
    cases: list[tuple[str, callable, str | None]] = [
        ("V1 鳴らない — 6列の表がちょうど1つ", lambda r: _write_tree(r), None),
        (
            "V1 鳴る — 6列の表が無い（3列の表だけ）",
            lambda r: _write_tree(r, canon=_doc(["| a | b | c |"], header=False, sep=False)),
            "V1",
        ),
        (
            "V1 鳴る — 6列の表が2つある",
            lambda r: _write_tree(r, canon=_doc(extra_table=True)),
            "V1",
        ),
        (
            "V2 鳴る — 列が7つある",
            lambda r: _write_tree(r, canon=_doc(wide=True)),
            "V2",
        ),
        (
            "V2 鳴る — 区切り行が無い",
            lambda r: _write_tree(r, canon=_doc(sep=False)),
            "V2",
        ),
        (
            "V3 鳴る — 自由度を型が名指せない",
            lambda r: _write_tree(r, canon=_doc([_row(dof="twist")])),
            "V3",
        ),
        (
            "V3 鳴る — データ行が0である（空を OK と言わない）",
            lambda r: _write_tree(r, canon=_doc([])),
            "V3",
        ),
        (
            "V4 鳴る — パスがリポジトリに無い",
            lambda r: _write_tree(r, canon=_doc([_row(path="projects/x/motions/missing.json")])),
            "V4",
        ),
        (
            "V4 鳴る — 最後の欄が空である",
            lambda r: _write_tree(r, canon=_doc([_row(path="")])),
            "V4",
        ),
        (
            "V5 鳴る — ミラーの行数が違う",
            lambda r: _write_tree(r, ja=_doc([_row(), _row()])),
            "V5",
        ),
        (
            "V5 鳴る — ミラーの自由度の欄が違う",
            lambda r: _write_tree(r, ja=_doc([_row(dof="roll")])),
            "V5",
        ),
        (
            "V5 鳴る — ミラーの使われた場所の欄が違う",
            lambda r: _write_tree(
                r, zh=_doc([_row(path="projects/x/motions/missing.json")])
            ),
            "V5",
        ),
        (
            "V0 鳴る — スキーマが無い",
            lambda r: _write_tree(r, schema=False),
            "V0",
        ),
        ("V5 鳴らない — ミラーも同じ", lambda r: _write_tree(r), None),
    ]

    width = max(len(name) for name, _, _ in cases)
    failed = 0
    print("=== check_vocabulary.py 自己検査 ===")
    for name, build, expect in cases:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build(root)
            bad, _stats = check(root)
            fired = sorted({b.split()[0] for b in bad})
            if expect is None:
                ok = not bad
                got = "鳴らない" if ok else f"鳴った {bad}"
            else:
                ok = expect in fired
                got = "鳴った" if ok else f"鳴らなかった（{bad or '違反0'}）"
            print(f"  {name:<{width}}  {got:<24} {'期待どおり' if ok else '★食い違い'}")
            failed += 0 if ok else 1

    print()
    if failed:
        print(f"=== {len(cases)} 例中 {failed} 例が期待と違う")
        return 1
    print(f"=== {len(cases)} 例中 {len(cases)} 例が期待どおり")
    return 0


# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="語彙の写像を検査する（正典は references/README.md）")
    ap.add_argument("--self-test", action="store_true", help="各規則の鳴る例と鳴らない例を走らせる")
    ap.add_argument("--root", default=str(REPO), help="リポジトリの根（既定はこのファイルの親の親）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    root = Path(args.root)
    bad, stats = check(root)

    print(f"=== 型から読んだ自由度（{SCHEMA}）")
    print(f"    {' / '.join(stats['dof']) if stats['dof'] else '⚠️ 読めなかった'}")
    print()
    print(f"=== 写像 {CANONICAL}")
    if stats["table"] is None:
        print("    ⚠️ 表を選べなかった——**この検査は、この版では表を1つも見ていない。**")
    else:
        line, nrows, ndata = stats["table"]
        print(f"    {line} 行目から {nrows} 行（見出し1・区切り1・データ{ndata}）")
    print()
    print("=== 各行の使われた場所")
    if not stats["paths"]:
        print("    ⚠️ 1つも無い——**この検査は、パスを1つも見ていない。**")
    for path, exists in stats["paths"]:
        print(f"    {'✅' if exists else '⛔'} `{path}`")
    print()
    print("=== ミラー")
    if not stats["mirrors"]:
        print("    ⚠️ 1つも無い——**この検査は、ミラーを1つも見ていない。**")
    for rel, nrows, same in stats["mirrors"]:
        print(f"    {rel}: {nrows} 行  {'一致' if same else '★食い違い'}")
    print()
    print("=== この検査が捕まえないもの")
    print("    ⛔ **写像が正しいかどうか。** 表の外に照合する先が無い——**永遠に検査できない。**")
    print()
    if bad:
        print(f"=== 違反 {len(bad)} 件")
        for b in bad:
            print(f"  {b}")
        return 1
    print("=== 違反 0 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
