#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i18n のミラーを検査する——**正典は英語である。**

⚠️ **この検査は `semantic-visual-loom` から写した。** 規則も自己検査も同じである。
**違うのは `DOCS` だけである。**

⚠️ **本リポジトリに、これ以外の検査は無い。** ⚠️ **そしてこの検査は、文書のミラーしか見ない**
——**`claude plugin validate --strict .` と合わせても、リポジトリの作法の15項目のうち5項目しか見ていない。**

規則は5つ。**各規則に「鳴る例」と「鳴らない例」が `--self-test` に在る。**

    R1 存在と非空   正典 ↔ `-ja` ↔ `-zh` が在り、0バイトでない
    R2 版           ヘッダが3本でバイト一致し、`canonical:` が正典を指す
    R3 切替行       `**Language:**` 行が3本でバイト一致し、3つの名前をその順で指す
    R4 不変ブロック `←` を含むフェンスが3本でバイト一致。見出しの水準列も3本で一致
    R5 範囲         ミラーを持つ文書はすべて `DOCS` に在り、ミラーには正典が在る

⚠️ **R5 は 2026-10-19 に足した。** それまで `DOCS` は**手で並べる一覧**であり、
**並べ忘れた文書は、ミラーを持ったまま検査の外で腐った**——実測で6組が外に在った
（`docs/stackchan-daemon.md` と `records/` の5本）。**規則が一覧を読むだけなら、
一覧の穴は規則の穴である。**

⚠️ **R2 は「1行目」ではなく「frontmatter を除いた最初の非空行」を見る。**

    frontmatter が無ければ      → 最初の非空行は1行目である（既存の文書はこれ）
    frontmatter が有れば        → 閉じの `---` の直後の非空行である（Skill はこれ）

**なぜ位置を動かしたか。** Claude Code は **1行目が `---` でなければ Skill の frontmatter を読まず**、
**`---` と YAML を本文として読む。** ⚠️ **Skill は登録されるので、静かに壊れる**——
いちばん悪い壊れ方である。だから **Skill の1行目は frontmatter に明け渡し**、
ヘッダをその後ろへ置く。⚠️ **それでも `DOCS` から外さない**——検査の外に出せば、
外に出したこと自体が見えなくなる。

⚠️ **frontmatter を読み飛ばす場所はもう1つある。** `heading_levels()` である——
見出しを選ぶ `HEADING_RE` は**行頭の `#` を見出しとして数える**ので、
読み飛ばさないと**訳文の `description` に `#` が混ざっただけで水準列がずれる。**

⚠️ **R4 は推定である。** 「不変ブロック」を宣言から読むのではなく、
**`←` を含むフェンス**という構造で選んでいる。⚠️ **この選び方は、このリポジトリでは実測されていない**
——**写した先（`semantic-visual-loom`）の実測である**（リポジトリ全体で `←` を含むフェンスは
**1つだけ**であり、**それは唯一「日本語0行」のフェンス**であった。他のフェンスはすべて訳すべき散文である）。
⚠️ **本リポジトリには、いま `←` を含むフェンスが1つも無い**——**ゆえにこの版では、R4 の不変ブロックは空である。**
**「空を OK と言わない」ために、`main()` がそれを明示して印字する。**
だから——
  * **どれを不変とみなしたかを報告する**（報告しない検査は、通った検査に見える）。
  * **規則が捕まえないもの**を下に書く。

⚠️ **この検査が捕まえないもの:**
  * **散文の訳が正しいか。** 意味が食い違っていても、行数と見出しが合っていれば通る。
  * **ミラーが古いか。** `i18n-version` は**人が上げる**ものであり、内容の同一性は見ていない。
  * **ミラーが正典に無いことを言っていないか。**
  * **訳が日本語のまま残っていないか。**（`--self-test` ではなく、必要なら `grep` で見る）
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: 正典の一覧。**リポジトリ内の相対パスで書く。**
#: ⚠️ ここを足すときは、`-ja` / `-zh` も同時に置くこと——**R1 がそれを読む。**
DOCS = (
    "CLAUDE.md",
    "README.md",
    "docs/verification-boundary.md",
    # ⚠️ **`docs/` の2本目も並べる。** ✅ **2026-09-28、実機の前で開く手順表が入った。**
    # ⛔ **この1本は、リポジトリで唯一「主張を持たない文書」である**——**確認の一覧であり、
    # 検査に鳴るものが無い**（**その理由と代価は、頁自身が書いている**）。
    # **それでも `DOCS` から外さない**——**外に出せば、外に出したこと自体が見えなくなる。**
    "docs/first-contact.md",
    # ⚠️ **`docs/` の3本目も並べる。** ✅ **2026-10-15、機体2の手順表が入った。**
    # ⛔ **この1本も「主張を持たない文書」である**——**そして1本目とは向きが逆である**:
    # **あちらは「項目は1つも行われていない」で、こちらは「ほとんどが既に行われている」。**
    # **それでも `DOCS` から外さない**——**外に出せば、外に出したこと自体が見えなくなる。**
    "docs/first-contact-stackchan.md",
    # ⚠️ **`docs/` の4本目も並べる。** ✅ **2026-10-15、構築メモが入った。**
    # ⛔ **この1本は、上の3本と種類が違う**——**主張を持たないのではなく、意図的に写しである。**
    # **それでも `DOCS` から外さない**——**外に出せば、外に出したこと自体が見えなくなる。**
    "docs/construction-memo.md",
    # ⚠️ **`docs/` の5本目も並べる。** ✅ **2026-10-19、`R5` がこの1本を見つけた。**
    # ⛔ **2026-10-18 に書かれ、ミラーも3本そろっていたのに、この一覧に無かった**
    # ——**検査は緑のまま、この1本だけを見ていなかった。**
    "docs/stackchan-daemon.md",
    # ⚠️ **`docs/` の6本目も並べる。** ✅ **2026-10-19、コーディングエージェントの体へ
    # 向けた進捗表が入った**——**8つの行の状態を、行ごとに1つの源から引く地図である。**
    # ⛔ **この頁は「何分の何」を名乗らない**（行は問いであり、重みではない）。
    "docs/stackchan-progress.md",
    # ⚠️ **`engine/` と `schemas/` の1本も並べる。**
    # **実装を書いた日に文書が増える**——**並べ忘れれば、その3本は検査の外で腐る。**
    "engine/README.md",
    "schemas/README.md",
    # ⚠️ **`tests/` の中の1本も並べる。** 検査の外に出せば、**外に出したこと自体が見えなくなる。**
    "tests/README.md",
    # ⚠️ **`projects/` の下の1本も並べる。** 同じ理由である——**決定 C がコードを
    # 内側に置いたので、内側の文書も検査の内側に置く。**
    "projects/pet/README.md",
    # ⚠️ **`projects/` の下の2本目も並べる。** ✅ **2026-10-18、焼く前の層が入った。**
    # ⛔ **この1本は、機体2について「無い」ことの一覧を持つ**——**外に出せば、
    # 外に出したこと自体が見えなくなる**（同じ規則である）。
    "projects/stackchan/README.md",
    # ⚠️ **`projects/` の下の3本目も並べる。** ✅ **2026-10-18、機体2の電線の機体側が入った。**
    # ⛔ **この1本は、いま「頭が回った」と「枠は1つも届いていない」を同じ頁に持つ**——
    # **外に出せば、外に出したこと自体が見えなくなる**（同じ規則である）。
    "projects/stackchan-firmware/README.md",
    # ⚠️ **`records/` の1本も並べる。** ✅ **2026-10-18、機体2が初めて動いた日の記録が入った。**
    # ⛔ **この1本は、プログラムが言えないことを言うために在る**——**観察が背骨で、
    # 数字はその内側の証拠である。** **検査の外に出せば、外に出したこと自体が見えなくなる**
    # （同じ規則である）。
    "projects/stackchan-firmware/records/2026-10-18-first-arrival.md",
    # ⚠️ **`records/` の2本目も並べる。** ✅ **2026-10-18、光が初めて点いた日の記録が入った。**
    # ⛔ **この1本は、レジスタが正しいことと光ること が別であると分かった日を書く**——
    # **観察が背骨で、数字はその内側の証拠である**（同じ規則である）。
    "projects/stackchan-firmware/records/2026-10-18-the-lights.md",
    # ⚠️ **`records/` の3〜7本目も並べる。** ✅ **2026-10-19、`R5` がこの5本を見つけた。**
    # ⛔ **5本とも同じ日にミラーを3本そろえて書き、同じ日にこの一覧から漏れていた**
    # ——**記録の背骨は人の観察であり、その頁が検査の外に在れば、
    # 外に出したこと自体が見えなくなる**（同じ規則である）。
    "projects/stackchan-firmware/records/2026-10-18-the-gestures.md",
    "projects/stackchan-firmware/records/2026-10-18-the-face.md",
    "projects/stackchan-firmware/records/2026-10-18-the-voice.md",
    "projects/stackchan-firmware/records/2026-10-18-the-neck.md",
    "projects/stackchan-firmware/records/2026-10-19-the-join.md",
    # ✅ **`records/` の8本目は、ゴールの記録である。** 2026-10-19、著者が
    # **「そこに何かが居る」**と言った。⛔ **この1本は、検証ではなく観察である**
    # ——**検査の外に出せば、ゴールについて何も言わないまま、頁だけが腐る。**
    "projects/stackchan-firmware/records/2026-10-19-something-is-there.md",
    # ✅ **`records/` の9本目は、バスが答えた日に書いた。** 2026-10-19、著者は
    # **「1:動いた」「2:鳴った」**と答え、**「もう一回動作確認したい」**のあと**「ok」**と言った。
    # ⛔ **その頁も検証ではない**——**読み戻しが位置を運ぶようになったことは数で、
    # 何かが居ることは言っていない。**
    "projects/stackchan-firmware/records/2026-10-19-the-bus-answered.md",
    # ✅ **`records/` の10本目は、機械が自分で戻った日に書いた。** 2026-10-19、
    # レールを切って手を離し、基板が15秒でバスを取り戻した。⛔ **その頁は
    # 診断ではない**——**引き金はまだ名づけられておらず、回復は診断ではない。**
    "projects/stackchan-firmware/records/2026-10-19-the-machine-recovers-itself.md",
    # ✅ **`records/` の11本目は、最初の一日を書き留めた。** 2026-10-19、著者は
    # **「たまに音が鳴っていた」**と答えた。⛔ **その一文がこの頁の背骨であり、
    # 97という音の数はその内側の証拠である**——**午後のチャイムはすべて
    # このセッション自身の仕事に帰っており、耳がどれを捉えたかは確定しない。**
    "projects/stackchan-firmware/records/2026-10-19-the-sounds.md",
    # ✅ **`records/` の12本目は、答えなかった基板の頁である。** 2026-10-21 の朝、
    # ホストも USB の機器も揃っていたのに **8つの枠が `sent: true` で `accepted` が0**、
    # 探針は `position: null`、`esptool.py read_mac` は `No serial data received`。
    # 著者が線を差し直すと基板は `alive` を返した。⛔ **この頁は診断ではない**
    # ——**回復は診断ではなく、黙った基板と死んだ基板はここからは同じに見える。**
    "projects/stackchan-firmware/records/2026-10-21-the-board-that-would-not-answer.md",
    # ✅ **`records/` の13本目は、二つの向きの頁である。** 2026-10-21、著者の問いは
    # 一行だった——**「そもそもwifi接続できているか？」**。✅ **ラジオは繋がっており、
    # その一行の前に起動ループを1つ払った**（`sys_evt` のスタック、既定 2304 → 4096）。
    # ⛔ **そして向きが分かれた**: Mac から基板へは `EHOSTUNREACH` が **0.1 ミリ秒**で
    # 返り（正しい MAC を握ったまま）、基板から Mac へは毎回届いて答えが戻った
    # ——**外へ開いた TCP の1本が両方向を運んだ。** ⚠️ **この頁は診断ではない**
    # ——**線の上の枠は一度も見ておらず、2台目のクライアントも無い。**
    "projects/stackchan-firmware/records/2026-10-21-two-directions.md",
    # ✅ **`records/` の14本目は、基板が外へ dial した頁である。** 2026-10-21、著者の問いは
    # **「最終的には、usb接続なしで動くようになるよね？」**。✅ **基板は起動時に、誰も
    # 何も打たないまま NVS の住所を読んで Mac へ接続し、`ready` を印字する前に繋がっていた**;
    # `bench pos` の答えも、枠の受理の行も、姿勢の判定も、**同じソケットを戻ってきた**。
    # ⛔ **そしてケーブルは一度も抜かれていない**——**この頁が測ったのは、体の会話を丸ごと
    # 運ぶリンクであり、ケーブル無しで体が生き延びることではない。** ⚠️ **デーモンはまだ
    # このリンクを使っておらず**、向こう側に居たのはそのために書かれた探針である。
    "projects/stackchan-firmware/records/2026-10-21-the-board-dials-out.md",
    # ⚠️ **`references/` の1本も並べる。** ✅ **2026-09-28、このディレクトリに最初の1行が入った**
    # ——**D-12 が決めた「覆えない差」の欄を持つ表である。**
    # ✅ **同じ日、この1本は D-02 の答えになった**——**語彙は固定の表ではなく、引ける写像である。**
    # ⛔ **そして表そのものは `tools/check_vocabulary.py` が読む**（**この検査は見出しの水準列しか見ない**）。
    "references/README.md",
    # ⚠️ **`skills/` の1本も並べる。** ✅ **2026-09-28、D-02 に答が出た同じ日に、書き手が1本入った。**
    # ⛔ **この1本だけは frontmatter を1行目に持つ**——**R2 は「frontmatter を除いた最初の非空行」を読む**
    # （**Claude Code は1行目が `---` でなければ Skill の frontmatter を読まない**）。
    # **ゆえにこの1本は、R4 の見出しの水準列が frontmatter を数えないことの、唯一の実例である。**
    "skills/embodied-kinetic-loom/SKILL.md",
)

#: ミラーの言語接尾辞。**正典は英語なので `en` は無い。**
LANGS = ("ja", "zh")

#: 不変ブロックを選ぶ目印。**この文字を含むフェンスが不変である。**
INVARIANT_MARK = "←"

#: R5 が歩かないディレクトリ。**検査の対象ではない木である。**
#: ⚠️ **この一覧を広げることは、検査の範囲を狭めることである**——**理由を書かずに足さない。**
SKIP_DIRS = {".git", "node_modules", "site-packages", "__pycache__", ".venv"}

HEADER_RE = re.compile(
    r"^<!-- i18n-version: (\S+) \| canonical: (\S+) \| translated: (\S+) -->$"
)
SWITCHER_RE = re.compile(
    r"^\*\*Language:\*\* \[English\]\(([^)]+)\) \| \[日本語\]\(([^)]+)\) \| \[中文\]\(([^)]+)\)$"
)
FENCE_RE = re.compile(r"^\s*```")
HEADING_RE = re.compile(r"^(#+)\s")

#: frontmatter の区切り。**Skill は1行目にこれを置く。**
FRONTMATTER_FENCE = "---"


def mirror_of(rel: str, lang: str) -> str:
    """`README.md` + `ja` → `README-ja.md`（**同じディレクトリに並ぶ**）。"""
    p = Path(rel)
    return str(p.with_name(f"{p.stem}-{lang}{p.suffix}"))


def fences(lines: list[str]) -> list[tuple[int, int, list[str]]]:
    """(開き行の添字, 閉じ行の添字, フェンスを含む行の並び) を返す。

    ⚠️ **閉じないフェンスは無視する**——閉じ行が無ければ、それはフェンスではない。
    """
    out: list[tuple[int, int, list[str]]] = []
    opened = None
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            if opened is None:
                opened = i
            else:
                out.append((opened, i, lines[opened : i + 1]))
                opened = None
    return out


def inside_fence(lines: list[str]) -> set[int]:
    """フェンスの中にある行の添字。**見出しを数えるとき、これを除く。**"""
    covered: set[int] = set()
    for a, b, _ in fences(lines):
        covered.update(range(a, b + 1))
    return covered


def frontmatter_span(lines: list[str]) -> int:
    """先頭の frontmatter が占める行数。**無ければ 0。**

    ⚠️ **閉じない frontmatter も 0 を返す**——閉じていなければ、それは frontmatter ではない。
    その壊れ方は **R2 が鳴らす**（ここで黙って読み飛ばすと、見出しだけが静かにずれる）。
    """
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        return 0
    end = next(
        (i for i in range(1, len(lines)) if lines[i].strip() == FRONTMATTER_FENCE), None
    )
    return 0 if end is None else end + 1


def header_line(lines: list[str]) -> tuple[str | None, str | None]:
    """`i18n-version` ヘッダの行と、**見つからなかった理由**を返す。

    ⚠️ **位置は「1行目」ではなく「frontmatter を除いた最初の非空行」である。**
    frontmatter が無ければ、それは**1行目**である（既存の文書はそのまま通る）。
    """
    if not lines:
        return None, "空である"
    start = frontmatter_span(lines)
    if start == 0 and lines[0].strip() == FRONTMATTER_FENCE:
        return None, "1行目の `---` が閉じない（frontmatter の終わりが無い）"
    for i in range(start, len(lines)):
        if not lines[i].strip():
            continue
        if HEADER_RE.match(lines[i]):
            return lines[i], None
        where = "frontmatter の直後" if start else "1行目"
        return None, f"{where}の行が `i18n-version` ヘッダでない（`{lines[i].strip()[:48]}`）"
    return None, "ヘッダが無い（frontmatter の後ろが空である）" if start else "ヘッダが無い"


def heading_levels(lines: list[str]) -> list[int]:
    """見出しの水準の列。**フェンスの中と frontmatter の中は数えない。**

    ⚠️ 見出しの**文言は訳す**ので、比べるのは数と深さだけである。
    ⚠️ **frontmatter を数えない理由**は `HEADING_RE` が YAML のコメント `# …` にも当たるためである。
    """
    skip = inside_fence(lines) | set(range(frontmatter_span(lines)))
    return [
        len(m.group(1))
        for i, line in enumerate(lines)
        if i not in skip and (m := HEADING_RE.match(line))
    ]


def invariant_blocks(lines: list[str]) -> dict[int, list[str]]:
    """`←` を含むフェンスを、開き行の添字 → 中身 で返す。"""
    return {
        a: body
        for a, _b, body in fences(lines)
        if any(INVARIANT_MARK in line for line in body)
    }


def mirror_sets(root: Path) -> list[str]:
    """ディスク上でミラーを持つ正典の相対パス。**正典が無くても、名を返す。**

    ⚠️ **1本でもミラーが在ればその組である**——**片方だけ在る壊れ方は R1 が鳴らす。**
    """
    found: set[str] = set()
    for p in root.rglob("*.md"):
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        for lang in LANGS:
            suffix = f"-{lang}.md"
            if p.name.endswith(suffix):
                canon = p.with_name(p.name[: -len(suffix)] + ".md")
                found.add(canon.relative_to(root).as_posix())
                break
    return sorted(found)


def check(root: Path, docs: tuple[str, ...] = DOCS) -> tuple[list[str], dict]:
    """違反の一覧と、**何を見たか**の記録を返す。"""
    bad: list[str] = []
    stats = {
        "canonical": len(docs),
        "present": 0,
        "mirror_sets": 0,
        "invariant": [],  # (rel, 開き行の番号, 行数)
        "frontmatter": [],  # (rel, frontmatter が占める行数)
    }

    # ---- R5 範囲
    # ⚠️ **規則が一覧を読むだけなら、一覧の穴は規則の穴である。**
    #    並べ忘れた文書は、ミラーを持ったまま検査の外で腐る。
    on_disk = mirror_sets(root)
    stats["mirror_sets"] = len(on_disk)
    for rel in on_disk:
        if not (root / rel).is_file():
            bad.append(f"R5 {rel}: ミラーだけが在り、正典が無い")
        elif rel not in docs:
            bad.append(f"R5 {rel}: ミラーを持つが `DOCS` に無い——**検査の外で腐る**")

    for rel in docs:
        cpath = root / rel
        present: dict[str, list[str] | None] = {}
        for lang in ("",) + LANGS:
            p = cpath if lang == "" else root / mirror_of(rel, lang)
            if not p.is_file():
                present[lang] = None
                continue
            text = p.read_text(encoding="utf-8")
            # ⚠️ **空ファイルは内容でない。**
            present[lang] = text.split("\n") if text.strip() else []
            stats["present"] += 1

        # ---- R1 存在と非空
        for lang in ("",) + LANGS:
            name = rel if lang == "" else mirror_of(rel, lang)
            if present[lang] is None:
                bad.append(f"R1 {name}: ファイルが無い")
            elif not present[lang]:
                bad.append(f"R1 {name}: 空である（0バイト、または空白だけ）")

        if any(v is None or not v for v in present.values()):
            continue

        canon = present[""]

        # ---- R2 版
        heads = {}
        for lang in ("",) + LANGS:
            name = rel if lang == "" else mirror_of(rel, lang)
            span = frontmatter_span(present[lang])
            if span:
                stats["frontmatter"].append((name, span))
            head, why = header_line(present[lang])
            if head is None:
                bad.append(f"R2 {name}: {why}")
                heads[lang] = None
                continue
            heads[lang] = head
            m = HEADER_RE.match(head)
            if m.group(2) != rel:
                bad.append(
                    f"R2 {name}: `canonical: {m.group(2)}` が正典 `{rel}` を指していない"
                )
        if heads[""] is not None:
            for lang in LANGS:
                if heads[lang] is not None and heads[lang] != heads[""]:
                    bad.append(
                        f"R2 {mirror_of(rel, lang)}: ヘッダが正典と食い違う\n"
                        f"      正典: {heads['']}\n      ミラー: {heads[lang]}"
                    )

        # ---- R3 切替行
        want = (Path(rel).name, Path(mirror_of(rel, "ja")).name, Path(mirror_of(rel, "zh")).name)
        switchers = {}
        for lang in ("",) + LANGS:
            name = rel if lang == "" else mirror_of(rel, lang)
            hits = [x for x in present[lang] if SWITCHER_RE.match(x)]
            if len(hits) != 1:
                bad.append(f"R3 {name}: 切替行が {len(hits)} 本（1本であること）")
                switchers[lang] = None
                continue
            switchers[lang] = hits[0]
            got = SWITCHER_RE.match(hits[0]).groups()
            if got != want:
                bad.append(
                    f"R3 {name}: 切替行の指す先が違う\n      期待: {want}\n      実際: {got}"
                )
        if switchers[""] is not None:
            for lang in LANGS:
                if switchers[lang] is not None and switchers[lang] != switchers[""]:
                    bad.append(f"R3 {mirror_of(rel, lang)}: 切替行が正典とバイト一致しない")

        # ---- R4 不変ブロック
        blocks = {}
        for lang in ("",) + LANGS:
            name = rel if lang == "" else mirror_of(rel, lang)
            blocks[lang] = invariant_blocks(present[lang])
            for a, body in sorted(blocks[lang].items()):
                stats["invariant"].append((name, a + 1, len(body)))
        # ⚠️ **数だけでなく位置も見る。** 数が合っていても位置が違えば写しは食い違う
        #    ——そして、そこを `KeyError` で落とすのは「鳴る」ではない（検査が壊れるだけである）。
        keys = {lang: sorted(blocks[lang]) for lang in ("",) + LANGS}
        if len(blocks[""]) != len(blocks["ja"]) or len(blocks[""]) != len(blocks["zh"]):
            bad.append(
                f"R4 {rel}: 不変ブロックの数が違う"
                f"（正典 {len(blocks[''])} / ja {len(blocks['ja'])} / zh {len(blocks['zh'])}）"
            )
        elif keys[""] != keys["ja"] or keys[""] != keys["zh"]:
            bad.append(
                f"R4 {rel}: 不変ブロックの位置が違う"
                f"（正典 {[k + 1 for k in keys['']]} 行目 /"
                f" ja {[k + 1 for k in keys['ja']]} 行目 /"
                f" zh {[k + 1 for k in keys['zh']]} 行目）"
            )
        else:
            for key in keys[""]:
                ref = blocks[""][key]
                for lang in LANGS:
                    if blocks[lang][key] != ref:
                        bad.append(
                            f"R4 {mirror_of(rel, lang)}: 不変ブロックが正典とバイト一致しない"
                            f"（正典 {key + 1} 行目から {len(ref)} 行）"
                        )

        # ---- R4 見出しの水準列
        lv = {lang: heading_levels(present[lang]) for lang in ("",) + LANGS}
        for lang in LANGS:
            if lv[lang] != lv[""]:
                bad.append(
                    f"R4 {mirror_of(rel, lang)}: 見出しの水準列が正典と違う"
                    f"（正典 {lv['']} / ミラー {lv[lang]}）"
                )

    return bad, stats


# --------------------------------------------------------------------------
# 自己検査
# --------------------------------------------------------------------------

OK_HEADER = "<!-- i18n-version: 1.0.0 | canonical: {rel} | translated: 2026-09-14 -->"
OK_BODY = """
**Language:** [English]({stem}.md) | [日本語]({stem}-ja.md) | [中文]({stem}-zh.md)

# Title {lang}

Some prose in {lang}.

```text
Master Prompt   ← §1 + §7 + §8
  A {{DURATION}} continuous cinematic take.
```

## Section A

More prose.
"""


def _write_tree(root: Path, rel: str, *, header: str | None = None, switcher: str | None = None,
                invariant: str | None = None, headings: int | None = None,
                frontmatter: str | None = None, frontmatter_mirror: str | None = None) -> None:
    """合成の木を1本ぶん作る。**各引数は「壊す」ためのものである。**

    ⚠️ `frontmatter` は**生の文字列**をそのまま先頭に置く——**閉じない frontmatter を
    作れるようにするためである**（`---` を書かなければ閉じない）。
    `{lang}` は言語名に置き換わる。
    """
    stem = Path(rel).stem
    for lang in ("",) + LANGS:
        p = root / (rel if not lang else mirror_of(rel, lang))
        p.parent.mkdir(parents=True, exist_ok=True)
        h = header if (header is not None and not lang) else OK_HEADER.format(rel=rel)
        body = OK_BODY.format(stem=stem, lang=lang or "en")
        fm = frontmatter
        if lang and frontmatter_mirror is not None:
            fm = frontmatter_mirror
        fm = (fm or "").replace("{lang}", lang or "en")
        if switcher is not None and not lang:
            body = body.replace(
                f"**Language:** [English]({stem}.md) | [日本語]({stem}-ja.md) | [中文]({stem}-zh.md)",
                switcher,
            )
        if invariant is not None and not lang:
            body = body.replace("  A {DURATION} continuous cinematic take.", invariant)
        if headings is not None and lang == "ja":
            body = body.replace("## Section A", "\n".join(["## Section A"] * headings))
        p.write_text(fm + h + "\n" + body, encoding="utf-8")


def _rm(root: Path, rel: str, lang: str) -> None:
    p = root / (rel if lang == "" else mirror_of(rel, lang))
    p.unlink()


def _blank(root: Path, rel: str, lang: str) -> None:
    p = root / (rel if lang == "" else mirror_of(rel, lang))
    p.write_text("   \n\n", encoding="utf-8")


def _orphan_mirror(root: Path, rel: str) -> None:
    """正典を置かずに、ミラーだけを置く。**R5 の「正典が無い」を作る。**"""
    p = root / mirror_of(rel, "ja")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        OK_HEADER.format(rel=rel) + "\n" + OK_BODY.format(stem=Path(rel).stem, lang="ja"),
        encoding="utf-8",
    )


def _shift(root: Path, rel: str, lang: str) -> None:
    """フェンスの前に1行挿す。**数は同じで位置だけが違う**を作る。"""
    p = root / (rel if lang == "" else mirror_of(rel, lang))
    lines = p.read_text(encoding="utf-8").split("\n")
    at = next(i for i, x in enumerate(lines) if x.strip().startswith("```"))
    lines.insert(at, "An extra line of prose that the canonical does not have.")
    p.write_text("\n".join(lines), encoding="utf-8")


#: Skill の frontmatter。**1行目に置くものであり、ヘッダはその後ろへ回る。**
SKILL_FRONTMATTER = "---\nname: a\ndescription: A skill that does a thing ({lang})\n---\n"


def self_test() -> int:
    """**各規則に「鳴る例」と「鳴らない例」。**"""
    docs = ("docs/a.md",)
    cases: list[tuple[str, callable, str | None]] = [
        ("R1 鳴らない — 3本そろっている", lambda r: _write_tree(r, docs[0]), None),
        ("R1 鳴る — ミラーが無い", lambda r: (_write_tree(r, docs[0]), _rm(r, docs[0], "zh")), "R1"),
        ("R1 鳴る — ミラーが空である", lambda r: (_write_tree(r, docs[0]), _blank(r, docs[0], "ja")), "R1"),
        (
            "R2 鳴る — 版が食い違う",
            lambda r: (
                _write_tree(r, docs[0]),
                (r / mirror_of(docs[0], "ja")).write_text(
                    "<!-- i18n-version: 9.9.9 | canonical: docs/a.md | translated: 2026-09-14 -->\n"
                    + OK_BODY.format(stem="a", lang="ja"),
                    encoding="utf-8",
                ),
            ),
            "R2",
        ),
        (
            "R2 鳴る — canonical が別のパスを指す",
            lambda r: _write_tree(
                r, docs[0],
                header="<!-- i18n-version: 1.0.0 | canonical: docs/WRONG.md | translated: 2026-09-14 -->",
            ),
            "R2",
        ),
        (
            "R2 鳴らない — 3本が同じヘッダ",
            lambda r: _write_tree(r, docs[0]),
            None,
        ),
        (
            "R2 鳴らない — frontmatter の後ろにヘッダが在る",
            lambda r: _write_tree(r, docs[0], frontmatter=SKILL_FRONTMATTER),
            None,
        ),
        (
            "R2 鳴る — frontmatter の後ろにヘッダが無い",
            lambda r: _write_tree(r, docs[0], frontmatter=SKILL_FRONTMATTER, header=""),
            "R2",
        ),
        (
            "R2 鳴る — frontmatter が閉じない",
            lambda r: _write_tree(r, docs[0], frontmatter="---\nname: a\ndescription: {lang}\n"),
            "R2",
        ),
        (
            # ⚠️ **frontmatter は行数を揃える**——ずらすと R4 が不変ブロックの位置で鳴り、
            #    見出しの検査を確かめたことにならない（実際に一度そうなった）。
            "R4 鳴らない — frontmatter の中の `#` を見出しに数えない",
            lambda r: _write_tree(
                r, docs[0],
                frontmatter="---\nname: a\n# note\ndescription: {lang}\n---\n",
                frontmatter_mirror="---\nname: a\nx note\ndescription: {lang}\n---\n",
            ),
            None,
        ),
        (
            "R3 鳴る — 切替行が旧名を指す",
            lambda r: _write_tree(
                r, docs[0],
                switcher="**Language:** [English](a-en.md) | [日本語](a.md) | [中文](a-zh.md)",
            ),
            "R3",
        ),
        (
            "R3 鳴る — 切替行が無い",
            lambda r: _write_tree(r, docs[0], switcher="(none)"),
            "R3",
        ),
        ("R3 鳴らない — 正しい切替行", lambda r: _write_tree(r, docs[0]), None),
        (
            "R4 鳴る — 不変ブロックが食い違う",
            lambda r: _write_tree(
                r, docs[0], invariant="  A {DURATION} 連続した一本のテイク。"
            ),
            "R4",
        ),
        (
            "R4 鳴る — 不変ブロックの位置が違う",
            lambda r: (_write_tree(r, docs[0]), _shift(r, docs[0], "ja")),
            "R4",
        ),
        (
            "R4 鳴る — 見出しの数が食い違う",
            lambda r: _write_tree(r, docs[0], headings=3),
            "R4",
        ),
        ("R4 鳴らない — 不変ブロックも見出しも同じ", lambda r: _write_tree(r, docs[0]), None),
        (
            "R5 鳴る — ミラーを持つが DOCS に無い",
            lambda r: (_write_tree(r, docs[0]), _write_tree(r, "docs/b.md")),
            "R5",
        ),
        (
            "R5 鳴る — ミラーだけが在り、正典が無い",
            lambda r: (_write_tree(r, docs[0]), _orphan_mirror(r, "docs/c.md")),
            "R5",
        ),
        ("R5 鳴らない — ミラーの組がすべて DOCS に在る", lambda r: _write_tree(r, docs[0]), None),
    ]

    width = max(len(name) for name, _, _ in cases)
    failed = 0
    print("=== check_i18n.py 自己検査 ===")
    for name, build, expect in cases:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            build(root)
            bad, _stats = check(root, docs)
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
    ap = argparse.ArgumentParser(description="i18n のミラーを検査する（正典は英語）")
    ap.add_argument("--self-test", action="store_true", help="各規則の鳴る例と鳴らない例を走らせる")
    ap.add_argument("--root", default=str(REPO), help="リポジトリの根（既定はこのファイルの親の親）")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    root = Path(args.root)
    bad, stats = check(root)

    print(f"=== 正典 {stats['canonical']} 本 / 在ったファイル {stats['present']} 本")
    print(f"=== ディスク上でミラーを持つ文書 {stats['mirror_sets']} 本（R5 が見る）")
    print("=== frontmatter を除いて読んだヘッダ")
    if not stats["frontmatter"]:
        print("    ⚠️ 1つも無い——**frontmatter を持つ文書は、この版には無い。**")
    for name, n in stats["frontmatter"]:
        print(f"    {name}: 先頭 {n} 行")
    print()
    print("=== 不変とみなしたブロック")
    if not stats["invariant"]:
        # ⚠️ **空を OK と言わない。**
        print("    ⚠️ 1つも無い——**この検査は不変ブロックを見ていない。**")
    for name, line, n in stats["invariant"]:
        print(f"    {name}:{line} から {n} 行")
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
