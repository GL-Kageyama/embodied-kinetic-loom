# -*- coding: utf-8 -*-
"""**2つ目の層のフックの縁。**

`python3 -m projects.stackchan_next.hook` が1事象につき1プロセスで走り、
1行を自分のデーモンへ送って消える。

⚠️ **既存のフックと同じ仕事を、別の戸口へ向かってする。** ソケットの綴りが
1つの prefix で違うので、2つの層が同じ瞬間に走れる
（`projects.stackchan_next.daemon.room.socket_path`）。
"""
