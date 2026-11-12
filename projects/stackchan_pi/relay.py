# -*- coding: utf-8 -*-
"""**橋の規則。** 住所をどう歩くか、名乗りをどう読むか、バイトをどう渡すか。

⛔ **このファイルはソケットを作らない。** `projects/` の決定論を守る検査
（`tests/test_pet_purity.py` → `tools/purity.py` の `FORBIDDEN`）が `socket` を
禁じている。**ソケットを作るのは入口（`__main__.py`）だけである**——
`projects/stackchan*/daemon/__main__.py` と同じ分け方である。
⚠️ **`recv` を呼ぶことは禁じていない。** 禁じているのは**輸入**である——
規則と配線を分けるのは、この層の仕事である。

## 1. どこを向くか

⚠️ **基板は自分から dial してくる。** ホストは基板へ dial できない——
**33回の接続が 0.1 ms で拒まれた**（`records/2026-10-21-two-directions.md`）。
⇒ **橋も同じ向きで立つ**: 基板を待ち受け、**橋から Mac へ dial する**。

⛔ **上流の住所を1つに固定しない。** 名指しの住所を**最初に**試し、駄目なら
同じ /24 を**近い順**に掃く。順序は `main/dial_scan.cpp` の `candidates` と同じで、
⚠️ **2つ隣へ動いたホストは3回で見つかる**。**この順序は2か所に写っている**——
片方を変えたら、もう片方も変える（`tests/test_stackchan_dial_scan.py` と
`tests/test_stackchan_pi_relay.py` が同じ7つを問う）。

## 2. 誰を通すか

⛔ **名乗りを確かめずに繋いだら、3333 を持つ何者でも体を動かす。** ホストは
接続ごとに `loom` を最初の1行に書く（`GREET = b"loom\\n"`）。⇒ **橋は上流から
1行だけ読み、`loom` でなければ閉じて次の住所へ行く。**

## ⛔ 2-1. その1行は、基板へ渡す

**2026-11-13、実機がこれを教えた。** 橋が名乗りを**読み捨てた**ところ、
基板は答えなかった——

```
dial: 192.168.0.104:3333 did not greet — not this host
```

⛔ **基板も `loom` を待っている。** 名乗りは橋の検査のためだけのものではなく、
**この接続がどのホストのものかを基板に告げる1行**である。⇒ **確かめた後、
そのまま下流へ書く。** ⚠️ **原型（`/tmp/bridge.py`）が通ったのは、名乗りを
確かめずに素通ししていたからである**——検査を足した瞬間、渡すのを忘れた。

## 3. 切れたらどうするか

✅ **上流が死んだら、下流も落とす**（裁定3）。⛔ **繋いだまま黙る橋は、
体を眠らせない**——`sleep_rule.h` は**リンクそのもの**を在席の信号にしている。
⇒ **閉じれば、体は眠れる。** 閉じなければ、体は「誰かが居る」と思い続ける。

⚠️ **どちらか片方が終われば、両方を閉じる。** 片道だけ生きているソケットは、
**上流から見れば繋がったままの体**であり、下流から見れば**黙ったホスト**である。
"""

from __future__ import annotations

from typing import List

#: ホストが接続ごとに書く1行（`projects/stackchan/daemon/__main__.py` の `GREET`）。
#: ⚠️ **橋はこれを書かない。読む。**
GREETING = b"loom\n"

#: 名乗りとして受け入れる語の長さの上限。⛔ **切れた名乗りは名乗りではない。**
GREETING_MAX = 64

#: 1つの /24 で試せる住所の数（`.0` と `.255` を除く）。
MAX_CANDIDATES = 254

#: `socket.SHUT_WR` の値。⛔ **`socket` を輸入できないので、ここに置く。**
#: ⚠️ **これは定数ではなく、いまの CPython と POSIX の値である**——
#: `socket.SHUT_WR` が 1 でなくなったら、テストが落ちる（`tests/test_stackchan_pi_relay.py`）。
SHUT_WR = 1

#: 上流へ繋ぐときの待ち。⚠️ **掃き出しは254回まで試す**ので、1回を短く保つ。
CONNECT_SECONDS = 0.6

#: 名乗りを待つ時間。⚠️ **これも短い**——黙っている相手は、このホストではない。
GREETING_SECONDS = 1.5


def candidates(known: str, limit: int = MAX_CANDIDATES,
               exclude=()) -> List[str]:
    """**名指しの住所を最初に、残りを近い順に。** `main/dial_scan.cpp` の写し。

    ⚠️ **`.+1`, `.-1`, `.+2`, `.-2`, …**——2つ隣へ動いたホストは3回で見つかる。

    ⛔ **住所でない文字列は、1つも返さない。** 名指しを持たない体が掃き出せば、
    その体は部屋の外へ歩き出す。

    ## ⛔ `exclude` — 橋だけが持つ引数

    **基板の `dial_scan` には無い。** 橋は**自分が待ち受けている /24 を掃く**
    ので、**掃き出しが自分自身を掴む**——掴めば、自分の accept に繋がり、
    そのセッションがまた上流を探す。⛔ **入れ子になる。**
    ⇒ **自分自身の住所は、候補から外す。**

    ⚠️ **名指しにも掛ける。** 名指しが自分自身なら、**その名前だけ落として、
    残りを掃く**——掃き出しは「名指しが違う」ための手段であり、
    ⛔ **自分を掴まないことと、歩かないことは別である。**
    ⇒ **上流が本当に無ければ、セッションが下流を閉じ、`upstream-missing` が残る。**
    """
    parts = known.split(".")
    if len(parts) != 4:
        return []
    if not all(part.isdigit() for part in parts):
        return []
    numbers = [int(part) for part in parts]
    if any(number > 255 for number in numbers):
        return []

    net = numbers[:3]
    last = numbers[3]
    prefix = "%d.%d.%d." % (net[0], net[1], net[2])
    if known in exclude:
        # ⛔ **名指しが自分自身なら、単に候補から外す。** 歩き出さない。
        out = []
    else:
        out = [known]
    # ⛔ **`.0` と `.255` は住所ではない。** 試せば、掃き出しは自分自身に訊くことになる。
    rest = [n for n in range(1, 255) if n != last]
    # ⚠️ **同距離なら + が先**（`103` → `104`, `102`, `105`, `101`, …）。
    rest.sort(key=lambda n: (abs(n - last), 0 if n > last else 1))
    for n in rest:
        if len(out) >= limit:
            break
        address = prefix + "%d" % n
        if address in exclude:
            continue
        out.append(address)
    return out[:limit]


def is_loom(line: bytes) -> bool:
    """**ホストの名乗りか。** ⛔ **接頭辞では一致させない**——`loomish` はこのホストではない。

    ⚠️ **区切りは `' '`, `'\\t'`, `'\\r'` の3つだけである**（`dial_scan.cpp`）。
    改行は**行に含めずに**渡す——含めれば、正しい名乗りが1つも通らなくなる。
    """
    if len(line) < 4 or not line.startswith(b"loom"):
        return False
    return len(line) == 4 or line[4:5] in (b" ", b"\t", b"\r")


def greeting_line(line: bytes) -> bytes:
    """**基板へ書く形に戻す。** ⛔ **読んだ1行を、捨てないためである。**

    ⚠️ **改行を付け直す。** `read_greeting` は改行の手前までしか返さない——
    橋が読むのは検査のためで、**基板が読むのは接続の挨拶としてである。**
    """
    return line + b"\n"


def read_greeting(sock, limit: int = GREETING_MAX) -> bytes:
    """**1行だけ読む。** ⛔ **改行の手前まで**——改行を含めると `is_loom` が落ちる。

    ⚠️ **上限で切る。** 名乗らない相手が無限に喋れば、橋はそこで止まる。
    ⚠️ **引数は `recv` を持つ何かである。** ソケットを作らないので、テストは
    `socketpair` の片方をそのまま渡せる。
    """
    buf = bytearray()
    while len(buf) < limit:
        chunk = sock.recv(1)
        if not chunk:
            break
        if chunk == b"\n":
            break
        buf += chunk
    return bytes(buf)


def pump(src, dst) -> None:
    """**片道を流し、終わったら書き込み側を閉じる。**

    ⛔ **読む側は閉じない。** 閉じれば、反対向きにまだ残っているバイトが落ちる。
    ⚠️ **例外は飲む。** 相手が消えたことは `recv` が `b""` を返すことで分かる——
    `OSError` を上へ投げても、橋ができることは何も変わらない。
    """
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(SHUT_WR)
        except OSError:
            pass
