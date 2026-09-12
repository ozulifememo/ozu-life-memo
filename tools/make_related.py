# -*- coding: utf-8 -*-
"""記事どうしの「近さ」を本文から測って、関連記事の地図を作る。

なぜ作ったか(2026-09-12)。

これまでの「あわせて読みたい」は、同じタグを持つ記事を新しい順に5本出していた。
ところがタグは12種類しかなく、「まちづくり」だけで62本ある。
つまり、まちづくりの記事をどれ開いても、並ぶ5本はほぼ同じだった。
本人の指摘:「今もあると思うけど、もっと、ちゃんとしてほしい。」

そこで、タグではなく**本文の言葉**で近さを測ることにした。
記事ごとに言葉を取り出し、その記事にだけよく出る言葉を重く見る(TF-IDF)。
「肱川」「空き家」「指定管理」のような、その記事を言い当てる言葉が
両方に出ていれば近い、という測り方である。

出すのは `assets/js/related-map.js`。記事を足したり書き直したら走らせ直す。
出た地図には**なぜ関連なのか(共通の言葉)**も入れてあるので、画面に出せる。

    python tools/make_related.py
    python tools/make_related.py --show <スラッグ>   # 1本ぶんだけ確かめる
"""
import argparse
import collections
import io
import math
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
DIRS = ("eachnews", "jiyu-kenkyu", "book")
OUT = REPO / "assets" / "js" / "related-map.js"
N_RELATED = 6

# どの記事にも出てきて、近さの手がかりにならない言葉。
# 「大洲市」で結ぶと全記事が関連になってしまう。
STOP = {
    "大洲", "大洲市", "愛媛", "愛媛県", "本市", "同市", "市内", "市役所", "市議会",
    "令和", "平成", "昭和", "年度", "今年",
    "記事", "出典", "資料", "調査", "場合", "以下", "以上", "自分", "内容",
    "ページ", "サイト", "リンク", "クリック", "メモ",
    "こと", "もの", "ため", "とき", "ところ",
}


def read_meta():
    """news-data.js から、記事のタイトル・カテゴリ・タグを拾う"""
    t = io.open(REPO / "assets" / "js" / "news-data.js", encoding="utf-8").read()
    meta = {}
    for m in re.finditer(r"\{\s*slug:\s*\"(.*?)\".*?\}", t, re.S):
        blk, slug = m.group(0), m.group(1)
        if "title:" not in blk:
            continue
        title = re.search(r'title:\s*"(.*?)"', blk)
        cat = re.search(r'category:\s*"(.*?)"', blk)
        tags = re.search(r"tags:\s*\[(.*?)\]", blk, re.S)
        meta[slug] = {
            "title": title.group(1) if title else slug,
            "cat": cat.group(1) if cat else "",
            "tags": [x.strip().strip("\"'") for x in tags.group(1).split(",") if x.strip()]
                    if tags else [],
        }
    return meta


def body_text(html):
    """本文だけを取り出す。出典欄・脇の柱・関連記事は近さの手がかりにしない。

    出典を混ぜると「同じ省庁を引いている記事」が上位に来てしまい、
    読者にとっての近さとずれる。"""
    h = re.sub(r"<div class=\"content-block source-box\".*", "", html, flags=re.S)
    h = re.sub(r"<aside.*?</aside>", "", h, flags=re.S)
    h = re.sub(r"<script.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<style.*?</style>", "", h, flags=re.S)
    h = re.sub(r"<svg.*?</svg>", "", h, flags=re.S)
    i = h.find("<h1")
    if i > 0:
        h = h[i:]
    return re.sub(r"<[^>]+>", " ", h)


KANJI = re.compile(r"[一-龯々]{2,10}")
KATA = re.compile(r"[ァ-ヶ]{2,12}")
ALPHA = re.compile(r"[A-Za-z]{3,20}")


def terms(text):
    """日本語を単語に割る道具は入れず、漢字の連なりとカタカナの連なりを言葉として扱う。

    長い連なりは、そのままだと他の記事と一致しない(「公共施設等総合管理計画」)。
    そこで2字・3字の窓もあわせて取る。ありふれた窓はTF-IDFが勝手に軽くする。

    返すのは (言葉ぜんぶ, そのうち語として自然なもの)。
    窓は近さを測るのには効くが、「水害訴」のように途中で切れていて、
    画面に「なぜ関連か」として出すと意味が分からない。だから分けておく。"""
    out, natural = [], set()
    for m in KANJI.finditer(text):
        w = m.group(0)
        if len(w) <= 6:
            out.append(w)
            natural.add(w)
        for n in (2, 3):
            if len(w) > n:
                for i in range(len(w) - n + 1):
                    out.append(w[i:i + n])
    for m in KATA.finditer(text):
        w = m.group(0)
        out.append(w)
        natural.add(w)
    for m in ALPHA.finditer(text):
        w = m.group(0).lower()
        out.append(w)
        natural.add(w)
    return ([w for w in out if w not in STOP], natural - STOP)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", help="このスラッグの関連だけを表示して終わる")
    args = ap.parse_args()

    meta = read_meta()
    docs = {}          # path -> {slug, title, tf}
    for d in DIRS:
        for p in sorted((REPO / d).glob("*.html")):
            if p.name.startswith("_") or p.name == "index.html":
                continue
            slug = p.stem
            html = io.open(p, encoding="utf-8").read()
            ws, natural = terms(body_text(html))
            tf = collections.Counter(ws)
            if not tf:
                continue
            m = meta.get(slug, {})
            title = m.get("title")
            if not title:
                h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
                title = re.sub(r"<[^>]+>", "", h1.group(1)).strip() if h1 else slug
            docs[d + "/" + p.name] = {
                "slug": slug, "title": title, "tf": tf, "natural": natural,
                "cat": m.get("cat", ""), "tags": m.get("tags", []), "dir": d,
                # 関連リンクの箱があるのは eachnews だけ。他は行き先にだけなる
                "src": d == "eachnews" and slug in meta,
            }

    N = len(docs)
    df = collections.Counter()
    for v in docs.values():
        for w in v["tf"]:
            df[w] += 1

    # どの記事にも出る言葉と、1本にしか出ない言葉は、近さを測る役に立たない
    keep = {w for w, n in df.items() if 2 <= n <= N * 0.25}
    vecs = {}
    for path, v in docs.items():
        vec = {}
        for w, c in v["tf"].items():
            if w not in keep:
                continue
            vec[w] = (1 + math.log(c)) * math.log(N / df[w])
        norm = math.sqrt(sum(x * x for x in vec.values())) or 1.0
        vecs[path] = {w: x / norm for w, x in vec.items()}

    # 言葉から記事を引ける表を作る。全組み合わせを回すと302×302になるので、
    # 同じ言葉を持つ記事だけを候補にする
    inv = collections.defaultdict(list)
    for path, vec in vecs.items():
        for w in vec:
            inv[w].append(path)

    rel = {}
    for path, vec in vecs.items():
        if not docs[path]["src"]:
            continue
        a = docs[path]
        score = collections.defaultdict(float)
        why = {}
        for w, x in vec.items():
            for other in inv[w]:
                if other == path:
                    continue
                add = x * vecs[other].get(w, 0.0)
                score[other] += add
                # いちばん効いた言葉を「なぜ関連か」として覚えておく。
                # 窓(「水害訴」)は近さの計算には効くが、画面に出すと意味が分からない。
                # 両方の記事で語として自然に出ている言葉を優先する。
                ok = w in a["natural"] and w in docs[other]["natural"]
                cur = why.get(other)
                w_rank = (ok, len(w) if ok else 0, add)
                if cur is None or w_rank > cur[1]:
                    why[other] = (w, w_rank)
        for other in list(score):
            b = docs[other]
            if b["tags"] and a["tags"] and set(a["tags"]) & set(b["tags"]):
                score[other] += 0.04
            if a["cat"] and a["cat"] == b["cat"]:
                score[other] += 0.02
        top = sorted(score.items(), key=lambda kv: -kv[1])[:N_RELATED]
        rel[path] = [(o, why[o][0], round(s, 4)) for o, s in top if s > 0.01]

    if args.show:
        hit = [p for p in docs if docs[p]["slug"] == args.show]
        if not hit:
            sys.exit("そのスラッグが見つかりません: " + args.show)
        p = hit[0]
        print(docs[p]["title"])
        for o, w, s in rel[p]:
            print("  %.3f  [%s]  %s" % (s, w, docs[o]["title"][:46]))
        return

    lines = ["// 記事どうしの近さの地図。tools/make_related.py が作る。手で直さない。",
             "// 中身は {記事のスラッグ: [[行き先のパス, 共通する言葉, 題], ...]}。",
             "// 題は、記事一覧(news-data.js)に載っていない自由研究・読書のときだけ入れる。",
             "// 近さは本文のTF-IDFで測っている。作り直し方は make_related.py の冒頭。",
             "var OZU_RELATED = {"]
    for path in sorted(rel):
        if not rel[path]:
            continue
        parts = []
        for o, w, s in rel[path]:
            if docs[o]["dir"] == "eachnews":
                parts.append('["%s","%s"]' % (o, w))
            else:
                parts.append('["%s","%s","%s"]'
                             % (o, w, docs[o]["title"].replace('"', "'")))
        lines.append('"%s":[%s],' % (docs[path]["slug"], ",".join(parts)))
    lines.append("};")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")

    have = sum(1 for v in rel.values() if v)
    print("記事 %d本 / 関連が付いた %d本" % (N, have))
    print("言葉 %d語(のべ %d語から絞り込み)" % (len(keep), len(df)))
    print("書き出し: %s  %.1f KB" % (OUT.relative_to(REPO), OUT.stat().st_size / 1024))


if __name__ == "__main__":
    main()
