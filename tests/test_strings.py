# -*- coding: utf-8 -*-
"""**縁の言葉が、本当に3言語で在るか。**

⛔ **このファイルが押さえるのは、翻訳の質ではない。** **穴である。**
表は `locales/` に在り、引くのは `projects/pet/strings.py` である——
**鍵が1つ足りなければ、その言語の利用者はそこで止まる。**

⚠️ **静的に見るものと、実行して見るものを分けてある。**

- **静的に見る**（AST）: **核が投げうるコードの集合**。`Rejection` は
  `engine/` の奥で組まれ、**入口からは全部を踏めない**——ゆえに字面を歩く。
- **実行して見る**: **入口のヘルプ**。`build_parser(lang)` を3言語で組み立てる——
  **これが、`pet_cli` の6つの鍵を1つ残らず踏む唯一の道である**
  （`build_parser` は `t(name)` で引くので、AST からは鍵が見えない）。

⚠️ **そして、`resolve()` が環境を読まないことを、ここで主張する。**
**読むのは入口だけである**——`time` と同じ形である。
"""
from __future__ import annotations

import ast
import io
import pathlib
import string

import pytest

from conftest import FakeClock
from engine.backend.mock import MockBox
from engine.intent import Intent, Move
from engine.trajectory import Rejection, admit
from projects.pet import strings
from projects.pet.__main__ import build_parser, language_of
from projects.pet.expressions import State
from projects.pet.motion import demo_rig, load_expression, perform
from projects.pet.report import report
from projects.pet.screen import Screen

REPO = pathlib.Path(__file__).resolve().parent.parent
ENGINE = REPO / "engine"
PROJECTS = REPO / "projects"

#: ⚠️ **`_meta` も節として数える。** **表自身の素性も、3本で揃っていなければならない。**
SECTIONS = ("refusal", "pet_cli", "pet_report")


def _python_files(root: pathlib.Path):
    return sorted(p for p in root.rglob("*.py"))


def _call_names(path: pathlib.Path, attr: str) -> list[tuple[str, ...]]:
    """⚠️ **`<何か>.<attr>("…", "…")` の文字列引数を拾う。** 見るのは字面だけである。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = getattr(func, "attr", None) or getattr(func, "id", None)
        if called != attr:
            continue
        args = [a.value for a in node.args if isinstance(a, ast.Constant)
                and isinstance(a.value, str)]
        out.append(tuple(args))
    return out


def _placeholders(template: str) -> set[str]:
    """⚠️ **`{dof!r}` も `{worst_ms:.3f}` も、名前は同じ1つである。**"""
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


# ───────────────────────── 言語の決まり方 ─────────────────────────


def test_the_default_language_is_en():
    assert strings.DEFAULT == "en"
    assert strings.resolve() == "en"


def test_the_environment_variable_is_used_when_no_flag_is_given():
    assert strings.resolve(env="ja") == "ja"


def test_the_flag_wins_over_the_environment_variable():
    assert strings.resolve(cli="zh", env="ja") == "zh"


def test_an_empty_flag_does_not_win_over_the_environment():
    """⚠️ **`--lang ""` は「指定しない」と同じである。** 空文字は偽である。"""
    assert strings.resolve(cli="", env="ja") == "ja"


def test_an_unsupported_language_falls_back_to_en_and_says_so(capsys):
    assert strings.resolve(cli="fr") == "en"
    err = capsys.readouterr().err
    assert "fr" in err, "⛔ **黙って落ちると、綴りを間違えた者は気づけない**"


def test_case_and_padding_do_not_matter():
    assert strings.resolve(cli="  JA ") == "ja"


def test_resolve_does_not_read_the_environment(monkeypatch):
    """⛔ **境界そのものの検査である。**

    環境変数が立っていても、`resolve()` は**それを見ない**——
    **見るのは入口（`language_of`）だけである**（`time` と同じ形）。
    ⚠️ **この1行が落ちる日は、核の側に環境が漏れた日である。**
    """
    monkeypatch.setenv(strings.ENV_VAR, "ja")
    assert strings.resolve() == "en"
    assert language_of([]) == "ja", "⚠️ **入口は読む**"


def test_the_entry_point_reads_the_flag_before_building_the_parser(monkeypatch):
    """⚠️ **ヘルプの文が翻訳されるので、言語は parser より先に要る。**"""
    monkeypatch.setenv(strings.ENV_VAR, "ja")
    assert language_of(["--motion", "greeting"]) == "ja"
    assert language_of(["--motion", "greeting", "--lang", "zh"]) == "zh"


# ───────────────────────── 表そのもの ─────────────────────────


def test_the_table_directory_holds_exactly_the_supported_languages():
    on_disk = {p.stem for p in strings.TABLE_DIR.glob("*.json")}
    assert on_disk == set(strings.SUPPORTED), "⚠️ **表が在るのに、名乗っていない**"


def test_every_table_carries_the_same_keys():
    """⛔ **ミラーの規則を、JSON の側でも押さえる。**

    `tools/check_i18n.py` が見るのは**文書**である——**見出しの水準、`Language:` の行、
    `←` を含むフェンス。** **JSON の表は、その検査の外に在る。**
    """
    keys = {lang: {s: set(strings.load(lang).get(s, {})) for s in SECTIONS}
            for lang in strings.SUPPORTED}
    for section in SECTIONS:
        first = keys["en"][section]
        assert first, f"表の節が空である: {section}"
        for lang in strings.SUPPORTED[1:]:
            assert keys[lang][section] == first, (
                f"{lang} の {section} が en と違う: "
                f"足りない {sorted(first - keys[lang][section])} / "
                f"余分 {sorted(keys[lang][section] - first)}"
            )


def test_every_translation_fills_the_same_holes():
    """⚠️ **鍵が揃っていても、穴が違えば落ちる。**

    `{frames}` を `{frame}` と書いた訳文は、**その言語でだけ送出する。**
    """
    for section in SECTIONS:
        en = strings.load("en")[section]
        for name, template in en.items():
            holes = _placeholders(template)
            for lang in strings.SUPPORTED[1:]:
                other = strings.load(lang)[section][name]
                assert _placeholders(other) == holes, (
                    f"{lang}.{section}.{name} の穴が違う: "
                    f"{sorted(_placeholders(other))} ≠ {sorted(holes)}"
                )


def test_no_entry_is_empty_and_en_is_named_canonical():
    for lang in strings.SUPPORTED:
        table = strings.load(lang)
        assert table["_meta"]["canonical"] == "en"
        assert table["_meta"]["language"] == lang
        for section in SECTIONS:
            for name, template in table[section].items():
                assert template.strip(), f"空の語である: {lang}.{section}.{name}"


# ───────────────────────── 引く ─────────────────────────


def test_a_missing_word_is_raised_not_defaulted():
    """⛔ **黙って既定へ落ちる版では、訳し忘れが永久に見えない。**"""
    with pytest.raises(KeyError) as caught:
        strings.text("pet_cli", "no_such_word", "en")
    assert "no_such_word" in str(caught.value)


def test_the_values_are_filled_in():
    out = strings.text("refusal", "unknown_dof_start", "ja", dof="pitch")
    assert "pitch" in out and "{" not in out


# ───────────────────────── 核 → 表 ─────────────────────────


def test_every_code_the_core_can_emit_is_in_the_table():
    """⛔ **核が投げうるのに、表が描けないコードを1つも残さない。**

    ⚠️ **`Rejection` は `engine/` の奥で組まれる。** 入口から全部を踏むのは難しい——
    **ゆえに字面を歩く。** そして、**字面が空ならこの検査は空を回っている**
    （`tools/purity.py` の `scan` と同じ作法で、数を先に主張する）。
    """
    codes = set()
    for path in _python_files(ENGINE):
        for args in _call_names(path, "Rejection"):
            if args:
                codes.add(args[0])

    assert codes, "engine/ から Rejection の字面が1つも取れない——検査が空を回っている"
    assert len(codes) >= 5, f"コードが減っている（{len(codes)}）: {sorted(codes)}"

    for lang in strings.SUPPORTED:
        table = set(strings.load(lang)["refusal"])
        assert codes <= table, f"{lang} が描けないコード: {sorted(codes - table)}"


def test_every_word_the_code_reaches_for_by_name_is_in_the_table():
    """⚠️ **字面で引いている語。** `build_parser` はここに入らない（下の検査が見る）。"""
    reached = set()
    for path in _python_files(PROJECTS):
        for attr in ("text", "template"):
            for args in _call_names(path, attr):
                if len(args) >= 2:
                    reached.add(args[:2])

    assert reached, "字面で引いている語が1つも無い——検査が空を回っている"
    for section, name in sorted(reached):
        for lang in strings.SUPPORTED:
            assert name in strings.load(lang).get(section, {}), (
                f"{lang} の表に {section}.{name} が無い"
            )


# ───────────────────────── 入口 ─────────────────────────


def test_the_parser_builds_in_every_language_and_the_help_actually_differs():
    """⛔ **`pet_cli` の6つの鍵を、1つ残らず踏む唯一の道である。**

    ⚠️ **「例外が出ない」だけでは足りない。** **同じ文が3言語から出るなら、
    表は引かれていない**——ゆえに、**違うことを主張する。**
    """
    helps = {}
    for lang in strings.SUPPORTED:
        parser = build_parser(lang)
        draws = []
        for action in parser._actions:
            draws.append(" ".join(action.option_strings))
            draws.append(action.help or "")
        draws.append(parser.description or "")
        text = "\n".join(draws)
        assert "pet_cli" not in text and "{" not in text
        helps[lang] = text

        # ⚠️ **綴りは言語ではない。** **旗の名と、状態の名は、3言語で同じである。**
        assert "--lang" in text and "--motion" in text and "--state" in text
        state_action = next(a for a in parser._actions if "--state" in a.option_strings)
        assert set(state_action.choices) == {s.value for s in State}

    assert helps["en"] != helps["ja"]
    assert helps["ja"] != helps["zh"]
    assert helps["en"] != helps["zh"]


def test_the_language_is_settled_before_a_state_is_drawn(monkeypatch):
    """⚠️ **`--lang` が引数として在ること自体**（ヘルプに出ないと気づけない）。"""
    parser = build_parser("en")
    assert parser.parse_args(["--lang", "ja"]).lang == "ja"
    assert parser.parse_args([]).lang is None


# ───────────────────────── 報告 ─────────────────────────


def _take():
    rig = demo_rig()
    return perform(load_expression("greeting"), rig, clock=FakeClock(overshoot=0.0005),
                   screen=Screen(io.StringIO()), box=MockBox(motors=rig.motors()))


def test_the_report_speaks_the_language_it_was_given():
    take = _take()
    assert take.ran, "⚠️ **この検査は、走った演技の上でしか意味を持たない**"

    en = report(take, "greeting", "en")
    ja = report(take, "greeting", "ja")
    assert en and ja and en != ja
    for out in (en, ja):
        assert "greeting" in out       # ⚠️ **名前は訳さない**
        assert "{" not in out          # ⛔ **穴が埋まっていない文を出さない**
        assert len(out.splitlines()) == 5


def test_a_refusal_is_rendered_with_its_values_in_every_language():
    """⛔ **核はコードしか渡さない。** **文にするのは表の側である。**

    ⚠️ **値を1つも持たない断りでは、この検査は半分しか鳴らない**——
    ゆえに**値を含む断り**（`unknown_dof_start`）で引く。
    """
    refusal = admit(Intent(moves=(Move(dof="roll", target=400, duration_ms=500, group=0),)), {}, {})
    assert isinstance(refusal, Rejection)

    for lang in strings.SUPPORTED:
        out = strings.refusal(refusal, lang)
        assert "roll" in out, f"{lang} が値を落としている: {out}"
        assert "{" not in out
    assert len({strings.refusal(refusal, l) for l in strings.SUPPORTED}) == 3


def test_the_refusal_line_says_no_frame_was_sent_in_every_language():
    """⚠️ **「送った 0 フレーム」と書かない。** **0 は緑に見える。**"""
    take = type(_take())(
        expression=load_expression("greeting"),
        admission=admit(Intent(moves=(Move(dof="roll", target=400, duration_ms=500, group=0),)), {}, {}),
        ticks=(), sets=(), steps=(), arrived=(),
    )
    assert not take.ran
    for lang in strings.SUPPORTED:
        out = report(take, "far", lang)
        assert len(out.splitlines()) == 2
        assert "{" not in out
