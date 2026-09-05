# -*- coding: utf-8 -*-
"""国税庁の法人番号データで、市町ごとの法人を数える。

## なぜ要るか

「大洲に会社は何社あるか」「そのうち何社が無くなったか」は、
どこにも答えが書いていない。国税庁が全法人の一覧を配っているので、
**自分で数えるしかない。**

このファイルは、その数え方を残しておくためのもの。記事に書いた数字を
あとから誰でも作り直せるようにしてある。数字の出どころが「クロコが
数えた」だけだと、次に見た人が確かめられない。

## データについて

  https://www.houjin-bangou.nta.go.jp/download/zenken/

から都道府県ごとのzipを落とす(愛媛県は fileNo=28019)。
CSVはShift_JIS、30列。この道具が使うのは次の列。

  [ 6] 商号又は名称
  [ 8] 法人種別(301=株式会社 302=有限会社 …)
  [13] 都道府県コード   [14] 市区町村コード
  [18] 登記記録の閉鎖等年月日   ← 空でなければ「もう無い」
  [19] 登記記録の閉鎖等の事由(01=清算の結了等 11=合併 21=登記官による閉鎖)
  [22] 法人番号指定年月日  ← 2015-10-05 より後なら、そのころ新しくできた

**「閉鎖」は廃業とは限らない。** 合併で消えた分も入るし、逆に事業を
やめても登記だけ残っている会社はここに出てこない。制度が始まったのは
2015年10月なので、それ以前に廃業した会社はそもそも入っていない。

## 使い方

    python tools/houjin.py --pref 38 --city 207          大洲市を数える
    python tools/houjin.py --pref 38 --city 207 --names  閉じた法人の名前も出す
    python tools/houjin.py --pref 38 --compare           県内の市を比べる
    python tools/houjin.py --selftest                    この道具を試す

初回はzipを落として tools/_houjin_cache/ に置く。次からはそれを使う。
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import re
import sys
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
CACHE = TOOLS / "_houjin_cache"

# 法人番号公表サイトのダウンロード番号(都道府県コード -> fileNo)
FILENO = {"38": 28019}

KIND = {"101": "国の機関", "201": "地方公共団体", "301": "株式会社", "302": "有限会社",
        "303": "合名会社", "304": "合資会社", "305": "合同会社",
        "399": "その他の設立登記法人", "401": "外国会社等", "499": "その他"}

JIYU = {"01": "清算の結了等", "11": "合併による解散等",
        "21": "登記官による閉鎖", "31": "その他"}

# 愛媛県の市(市区町村コード)
EHIME_CITIES = [("松山市", "201"), ("今治市", "202"), ("宇和島市", "203"),
                ("八幡浜市", "204"), ("新居浜市", "205"), ("西条市", "206"),
                ("大洲市", "207"), ("伊予市", "210"), ("四国中央市", "213"),
                ("西予市", "214"), ("東温市", "215")]

# 名前から業種を推し量る。**正確ではない**。傾向を見るだけのもの
GYOSHU = [
    ("建設・土木", r"建設|工務|土木|建築|舗装|設備|電気工事|工業"),
    ("運送・タクシー", r"運送|運輸|急便|物流|海運|汽船|タクシー|交通"),
    ("農林水産", r"農|林業|木材|製材|水産|漁業|園芸|畜産|養蚕"),
    ("飲食・宿泊", r"食堂|レストラン|料理|寿司|うどん|ラーメン|割烹|居酒屋|カフェ|旅館|ホテル"),
    ("小売・商事", r"商店|ストア|マート|商事|商会|販売|物産"),
    ("医療・福祉", r"医療|病院|医院|歯科|薬局|介護|福祉|ケア"),
    ("神社・寺", r"神社|寺$|寺院|教会|神宮"),
    ("不動産", r"不動産|地所|住宅|ハウス"),
]

CLOSED, REASON, PREF, CITY, NAME, TYPE, ASSIGNED = 18, 19, 13, 14, 6, 8, 22


def download(pref: str) -> Path:
    """都道府県のCSVを落として、キャッシュに置く"""
    CACHE.mkdir(exist_ok=True)
    got = sorted(CACHE.glob("%s_*_all_*.csv" % pref))
    if got:
        return got[-1]

    import requests
    sys.path.insert(0, str(TOOLS))
    import check_numbers as cn

    if pref not in FILENO:
        raise SystemExit("  この県のダウンロード番号を知りません: %s\n"
                         "  https://www.houjin-bangou.nta.go.jp/download/zenken/ を開いて\n"
                         "  doDownload(<番号>) を読み、FILENO に足してください" % pref)

    s = requests.Session()
    s.headers.update(cn.HEADERS)
    u = "https://www.houjin-bangou.nta.go.jp/download/zenken/"
    t = s.get(u, timeout=90).text
    m = re.search(r'name="(jp\.go\.nta[^"]+token)"\s+value="([^"]+)"', t)
    if not m:
        raise SystemExit("  ダウンロード用のトークンが取れませんでした")
    r = s.post(u + "index.html",
               data={m.group(1): m.group(2), "event": "download",
                     "selDlFileNo": str(FILENO[pref])},
               timeout=300, headers={"Referer": u})
    if r.status_code != 200 or len(r.content) < 100000:
        raise SystemExit("  ダウンロードに失敗: HTTP %d" % r.status_code)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    out = None
    for n in z.namelist():
        if n.endswith(".csv"):
            out = CACHE / n
            out.write_bytes(z.read(n))
    print("  落としました: %s (%.1fMB)" % (out, out.stat().st_size / 1024 / 1024))
    return out


def load(pref: str):
    p = download(pref)
    with io.open(p, encoding="cp932", errors="replace") as f:
        return [r for r in csv.reader(f) if len(r) > 22], p


def pick(rows, pref, city):
    return [r for r in rows if r[PREF] == pref and r[CITY] == city]


def report(rows, label: str, names: bool = False) -> None:
    closed = [r for r in rows if r[CLOSED]]
    print()
    print("  === %s ===" % label)
    print("  法人 %d件 / 登記が閉じられたもの %d件 (%.1f%%) / 残り %d件"
          % (len(rows), len(closed), 100 * len(closed) / len(rows) if rows else 0,
             len(rows) - len(closed)))

    print()
    print("  ・種類ごと")
    for k, v in collections.Counter(r[TYPE] for r in rows).most_common():
        a = [r for r in rows if r[TYPE] == k]
        c = [r for r in a if r[CLOSED]]
        print("      %-20s %5d件 / 閉鎖 %4d件 (%.1f%%)"
              % (KIND.get(k, k), v, len(c), 100 * len(c) / v))

    print()
    print("  ・閉じた理由")
    for k, v in collections.Counter(r[REASON] for r in closed).most_common():
        print("      %-20s %4d件 (%.0f%%)" % (JIYU.get(k, k), v, 100 * v / len(closed)))

    print()
    print("  ・登記官が閉じた日(まとめて処理されるので日付が固まる)")
    k21 = [r for r in closed if r[REASON] == "21"]
    for d, n in sorted(collections.Counter(r[CLOSED] for r in k21).items()):
        print("      %s  %s %d件" % (d, "■" * min(n, 40), n))

    print()
    print("  ・名前から見た業種(正確ではない。傾向だけ)")
    for lab, pat in GYOSHU:
        a = [r for r in rows if re.search(pat, r[NAME])]
        c = [r for r in a if r[CLOSED]]
        if a:
            print("      %-14s %4d件 / 閉鎖 %3d件 (%.1f%%)"
                  % (lab, len(a), len(c), 100 * len(c) / len(a)))

    print()
    print("  ・新しく法人番号がついた年(2015-10-05 の一斉付番より後だけ)")
    new = [r for r in rows if r[ASSIGNED] > "2015-10-06"]
    ny = collections.Counter(r[ASSIGNED][:4] for r in new)
    cy = collections.Counter(r[CLOSED][:4] for r in closed)
    print("      年     新設   閉鎖    差")
    for y in sorted(set(list(ny) + list(cy))):
        a, b = ny.get(y, 0), cy.get(y, 0)
        print("      %s   %4d   %4d   %+4d" % (y, a, b, a - b))

    if names:
        print()
        print("  ・登記官が閉じた法人の名前")
        for r in sorted(k21, key=lambda x: x[CLOSED]):
            print("      %s  %s" % (r[CLOSED], r[NAME]))


def compare(rows, pref: str) -> None:
    # 県全体でも、登記官が閉じた日が固まっているかを見る。
    # 市だけ見ていると「たまたま」に見えるが、県で見ると一斉処理だと分かる
    ken = [r for r in rows if r[PREF] == pref]
    k21 = [r for r in ken if r[REASON] == "21"]
    print()
    print("  === 県全体で、登記官が閉じた日 (計 %d件) ===" % len(k21))
    for d, n in sorted(collections.Counter(r[CLOSED] for r in k21).items()):
        print("      %s  %4d件" % (d, n))

    print()
    print("  === 愛媛県内の市(閉じた率の高い順) ===")
    out = []
    for name, code in EHIME_CITIES:
        a = pick(rows, pref, code)
        if not a:
            continue
        c = [r for r in a if r[CLOSED]]
        out.append((100 * len(c) / len(a), name, len(a), len(c)))
    out.sort(reverse=True)
    for pct, name, n, c in out:
        print("      %-10s 法人 %5d件 / 閉鎖 %4d件 → %.1f%%" % (name, n, c, pct))


def selftest() -> int:
    """その場で作ったCSVで、数え方が壊れていないか試す"""
    print()
    print("  自己診断: その場でデータを作って、数えられるか試します...")
    print()
    blank = [""] * 30

    def mk(name, kind, closed="", reason="", assigned="2015-10-05"):
        r = list(blank)
        r[NAME], r[TYPE], r[PREF], r[CITY] = name, kind, "38", "207"
        r[CLOSED], r[REASON], r[ASSIGNED] = closed, reason, assigned
        return r

    rows = [mk("株式会社あ", "301"),
            mk("有限会社い", "302", "2020-01-20", "21"),
            mk("有限会社う", "302", "2021-03-01", "01"),
            mk("え神社", "399"),
            mk("株式会社お建設", "301", "", "", "2022-05-01")]
    ok = True
    closed = [r for r in rows if r[CLOSED]]
    cases = [("全件を数える", len(rows) == 5),
             ("閉鎖を数える", len(closed) == 2),
             ("登記官による閉鎖だけ数える", len([r for r in closed if r[REASON] == "21"]) == 1),
             ("種類ごとに分ける", len([r for r in rows if r[TYPE] == "302"]) == 2),
             ("新しく番号がついたものを見つける",
              len([r for r in rows if r[ASSIGNED] > "2015-10-06"]) == 1),
             ("名前から業種を拾う",
              len([r for r in rows if re.search(GYOSHU[0][1], r[NAME])]) == 1),
             ("神社を拾う", len([r for r in rows if re.search(GYOSHU[6][1], r[NAME])]) == 1)]
    for lab, good in cases:
        print("    [%s] %s" % ("OK " if good else "NG ", lab))
        ok = ok and good
    print()
    print("  自己診断%s" % ("OK。" if ok else "に失敗しました。"))
    print()
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="国税庁の法人番号データで市町の法人を数える")
    ap.add_argument("--pref", default="38", help="都道府県コード(既定38=愛媛)")
    ap.add_argument("--city", default="207", help="市区町村コード(既定207=大洲市)")
    ap.add_argument("--names", action="store_true", help="閉じた法人の名前も出す")
    ap.add_argument("--compare", action="store_true", help="県内の市を比べる")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.selftest:
        return selftest()

    rows, path = load(args.pref)
    print()
    print("  もと: %s (%d件)" % (path.name, len(rows)))
    if args.compare:
        compare(rows, args.pref)
        return 0
    name = dict((c, n) for n, c in EHIME_CITIES).get(args.city, args.city)
    report(pick(rows, args.pref, args.city), name, args.names)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
