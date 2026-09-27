#!/usr/bin/env bash
#
# embodied-kinetic-loom installer
#
# 基盤の本体が持つ Skill は1本である——**Motion Intent を書く者**。
# それを Claude Code の検出場所へインストールする。
#
# Usage:
#   ./install.sh            # Global: ~/.claude/skills/（どのプロジェクトからも呼べる）
#   ./install.sh --local    # Project: .claude/skills/（このリポジトリのみ）
#   ./install.sh --uninstall
#
# インストールは symlink：正本は ./skills/ のまま。リポジトリへの編集が即反映される。
#
# ⚠️ **配列は1要素である**（D-03、2026-09-27——スキルは1本と決まった）。
#    ⛔ **glob にしない。** SVL の install.sh がその理由を書いている——
#    **glob にすると、意図せず次の1本が入る。** 入れる本は名指しで並べる。
#
# ⚠️ **呼び出し名には名前空間が付く**——`/embodied-kinetic-loom:embodied-kinetic-loom` のように。
#    単一スキルのリポジトリでは、ディレクトリ名がそのままスキル名になる（SAL・DEE の形）。
#
# ⚠️ **この Skill は文書であって、プログラムではない。** 走るコードはこのリポジトリに無い
#    ——**書くのはセッションの Claude であり、この Skill はその導きである**（D-03）。
#    ゆえに `--uninstall` で消えるのは、**入口であって、機構ではない。**

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$REPO_DIR/skills"

#: インストールする Skill の名。**`skills/` の下のディレクトリ名と一致する。**
#: ⛔ **1要素である。** 増やすときは、`skills/` にディレクトリを置いてから、ここに名前を足す。
SKILLS=(embodied-kinetic-loom)

MODE="global"
ACTION="install"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)    MODE="local" ;;
    --global)   MODE="global" ;;
    --uninstall) ACTION="uninstall" ;;
    -h|--help)
      echo "Usage: ./install.sh [--local|--global] [--uninstall]"
      echo ""
      echo "  --local      Install to .claude/ (this project only)"
      echo "  --global     Install to ~/.claude/ (default; callable from anywhere)"
      echo "  --uninstall  Remove the installed skills (default: global target)"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

if [[ "$MODE" == "local" ]]; then
  TARGET_DIR="$REPO_DIR/.claude/skills"
else
  TARGET_DIR="$HOME/.claude/skills"
fi

if [[ "$ACTION" == "uninstall" ]]; then
  echo "==> Uninstalling from: $TARGET_DIR"
  for name in "${SKILLS[@]}"; do
    target="$TARGET_DIR/$name"
    if [[ -L "$target" || -e "$target" ]]; then
      rm -rf "$target"
      echo "    ✓ removed $name"
    else
      echo "    (not installed) $name"
    fi
  done
  exit 0
fi

# ⚠️ **先に全部を確かめてから張る。** 途中で欠けていると、
#    **入ったように見えて、実は入っていない**という壊れ方をする。
#    そして1要素のうちの1つが欠けるとは、**この配列が指す先がディスクに無い**ことである。
for name in "${SKILLS[@]}"; do
  if [[ ! -f "$SKILLS_DIR/$name/SKILL.md" ]]; then
    echo "    ✗ missing: skills/$name/SKILL.md" >&2
    exit 1
  fi
done

echo "==> Installing ${#SKILLS[@]} skill(s) to: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
for name in "${SKILLS[@]}"; do
  target="$TARGET_DIR/$name"
  rm -rf "$target"              # 前回のインストール（symlink かファイル）を除去
  if [[ "$MODE" == "local" ]]; then
    # ⚠️ **リポジトリの中は相対で張る。** 絶対で張ると、**clone した人の環境では
    #    リンクが他人のホームを指す**——コミットされるのはこの形だからである。
    ln -s "../../skills/$name" "$target"
  else
    # ⚠️ **ホームの側は絶対で張る。** 相対にすると、`~/.claude/skills` から
    #    リポジトリまでの距離を数えることになり、置き場所を変えるたびに壊れる。
    ln -s "$SKILLS_DIR/$name" "$target"
  fi
  # ⚠️ **張った後で、届くかを確かめる。** 「ln が成功した」は「Skill が読める」ではない
  #    ——**symlink は、指す先が消えていても作れる。**
  if [[ ! -f "$target/SKILL.md" ]]; then
    echo "    ✗ $name: the link was made but SKILL.md does not resolve through it" >&2
    exit 1
  fi
  echo "    ✓ $name"
done

echo ""
echo "==> Done. Callable as:"
for name in "${SKILLS[@]}"; do
  echo "      /embodied-kinetic-loom:$name"
done
echo ""
echo "    Note: restart Claude Code or run /skills once to reload the listing."
echo "    Note: this skill writes a Motion Intent. It does not reach the machine —"
echo "          the serial layer is gated on the control box's generation."
