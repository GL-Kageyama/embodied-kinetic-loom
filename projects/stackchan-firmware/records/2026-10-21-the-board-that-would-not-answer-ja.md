<!-- i18n-version: 1.0.0 | canonical: projects/stackchan-firmware/records/2026-10-21-the-board-that-would-not-answer.md | translated: 2026-10-21 -->

**Language:** [English](2026-10-21-the-board-that-would-not-answer.md) | [日本語](2026-10-21-the-board-that-would-not-answer-ja.md) | [中文](2026-10-21-the-board-that-would-not-answer-zh.md)

# 答えなかった基板 — 2026-10-21

⛔ **このファイルの背骨は観察である。プログラムの数は、その内側に証拠として引用される。** tty が受け取った枠は、基板が受け取った枠ではない。

**数えたもの。** 1台、1つの Mac、1本の USB ケーブル、その抜き差し1回、そして設置済みデーモンのログ——ログイン時の起動から、答えが戻った枠まで。**数えていないもの:** なぜ基板が黙ったか、電源スイッチが入っていたか、黙っているあいだに何かが動いたか、ガラスに何が映っていたか。

## 見えたもの

**著者自身の説明は一行である:** 2026-10-20 に Mac を落とし、**そのとき基板の電源も落とした。** 2026-10-21 の朝、Mac が戻り、デーモンも一緒に起きた。

**抜き差しの前に、ホストが見たもの:**

- launchd のジョブは動いており（`embodied-kinetic-loom.stackchan-next`、PID 822）、ソケットも生きていた
- `/dev/cu.usbmodem101` は在り、USB には **`USB JTAG_serial debug unit`（Espressif）**が見えていた
- デーモンは**枠を8つ書き、8つとも `sent: true` で、`accepted: true` は1つも無かった**

**ホストが得られなかったもの:** `SessionStart` のデーモン自身の探針は `{"position": null, "heard": false, "read": ""}` を読み、手で書いた `bench pos` は**何も**返さず、IDF 環境の `esptool.py read_mac` は **`No serial data received`** で失敗した——2回、素で1回、`--before usb_reset` で1回。

⇒ **USB の機器はそこに在り、チップは答えていなかった。**

## 推測から組まれた身振り

⚠️ **デーモンは待たなかった。** `SessionStart` で `look_up` を流した: `{"neck": "look_up", "from": [0, 30], "to": [80, 500], "poses": 40, "seconds": 0.783}`。

⛔ **`from: [0, 30]` は測定ではない。** 基板が何も答えていなかったので、最後の姿勢も探針も無く、**計画は既定値から組まれた。** 判定はついに届かなかった（`verdict: null`、`read: ""`）。

⚠️ **この頁が必要になったのはこの形である:** 黙った基板と死んだ基板は、ここからは同じに見え、**予定表はその二つを区別しない。**

## 抜き差し

著者は「差し直した」と書いた——ケーブルを抜いて、挿し直した。**そして同じホスト、同じコードから:**

```
bench: yaw=ok pitch=ok
bench: yaw raw 482, angle 6.8 deg (zero 460)
bench: pitch raw 778, angle 49.3 deg (zero 620)
alive
```

そして手で書いた枠は `(sent, accepted) = (True, True)` を返した。**デーモン自身の次の枠は `accepted: true` を運んだ。**

## 数の証拠

| 何を | 値 | どこから |
|---|---|---|
| 黙っているあいだに書いた枠 | 8、すべて `sent: true` | デーモンのログ |
| 黙っているあいだに受理された枠 | **0** | デーモンのログ |
| デーモンの探針 | `position: null`、`heard: false`、`read: ""` | デーモンのログ |
| 手で書いた `bench pos` | 空 | ホスト自身の tty |
| `esptool.py read_mac` | `No serial data received`、2回 | IDF の venv、esptool 4.12.0 |
| `[0, 30]` から流した pose | 40——`applied` も `late` も確認されず | デーモンのログ |
| 抜き差しの後 | `yaw raw 482`、`pitch raw 778`、`alive` | 基板自身の行 |
| その後の枠 | `sent: true`、`accepted: true` | 基板自身の行 |

## このファイルが言わないこと

- ⛔ **基板がなぜ黙ったかは言わない。** 電源スイッチ、ケーブルの接触、固まったファームウェア、ROM の状態——**4つの候補であり、どれも切り分けていない。**
- ⛔ **黙っているあいだに何かが動いたかは言わない。** 40 pose が書かれ、**1つも確認されず**、基板の判定は届かなかった。
- ⛔ **ガラスが黒かったとは言わない。** ⚠️ **ファームウェアは起動時に顔を描かない**ので、動いている基板と動いていない基板は画面上では同じに見える——**それがこのファイルの存在理由であり、今朝についての所見ではない。**
- ⚠️ **診断ではない。** **回復は診断ではない**——2026-10-19 の頁がレールについて言ったのとまったく同じ形が、二度目に出ている。
