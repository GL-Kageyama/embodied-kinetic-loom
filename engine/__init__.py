# -*- coding: utf-8 -*-
"""このエンジンの中身。

⚠️ **`engine/` という名前は、このリポジトリの発明ではない。**
`semantic-visual-loom` が `engine/<話題>/` を使っている（姉妹の走査）。
⚠️ **`semantic-audio-loom` は `engine/` を持たない**——`semantic_audio_loom/` という
パッケージ名を使っている。**姉妹の作法は1つではない。**
⇒ **このリポジトリは `engine/` を採る。** 理由は、**`engine/` の中が1つの話題に閉じていること**である。

    中身
      trajectory/   決定論的な核心（補間・イージング・平滑化・制限）— **実装済み**
      intent.py     `Motion Intent` の読み込み
      （バックエンド・Pet の画面・音声は、まだ無い。**実機の応答が要る**）

⛔ **まだ無いものの方が多い。** `README.md` の「What is not here yet」を見よ。
"""
