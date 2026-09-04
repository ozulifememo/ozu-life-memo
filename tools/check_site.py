#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OZU LIFE MEMO サイト点検スクリプト
====================================

サイト全体を機械的に点検して、崩れている箇所を一覧で出します。
ファイルは一切書き換えません(読むだけ)。安心して何度でも走らせてください。

使い方(PowerShellでリポジトリのフォルダに入ってから):

    python tools/check_site.py              ふつうの点検(ネット接続なし・数秒)
    python tools/check_site.py --urls       出典URLが生きているかも確認(数分かかる)
    python tools/check_site.py --slug ozu-mirai-note   1記事だけ点検
    python tools/check_site.py --json out.json          結果をJSONで保存(Notion照合用)

「エラー」は直した方がよいもの、「警告」は見て判断するものです。
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Windowsのコンソールでも日本語が化けないようにする
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# 点検ルールの設定(ここを直せば基準を変えられます)
# ---------------------------------------------------------------------------

# 全ページ共通で入っていないといけない部品
CHROME_REQUIRED = [
    ("data-site-header", "ヘッダーの置き場所"),
    ("data-site-footer", "フッターの置き場所"),
    ("assets/js/site-chrome.js", "共通部品スクリプト"),
    ("<html lang=", "言語属性(lang)"),
    ('name="viewport"', "スマホ表示設定(viewport)"),
]

# 記事ページ(eachnews)だけに必要な部品
#
# 【写真まわりについて / 2026-08-19】
# もともとは全記事の末尾にランダムで写真を出す方式(article-random-photo +
# random-photo.js)だった。これを「記事の内容に合う写真だけを選んで出す」方式
# (article-images.js)へ差し替える改修が入ったため、旧方式の2つは必須から外した。
# 新方式が全記事に行き渡ったら、下の ARTICLE_PHOTO_OPTIONAL を必須へ移すこと。
ARTICLE_REQUIRED = [
    # 部分一致だと source-box-title で通ってしまう(2026-08-29に判明)。囲いの形で探す
    ('class="content-block source-box"', "出典ブロックの装飾クラス"),
    ("article-summary", "冒頭の要点3行ボックス"),
    ("article-readtime", "読了時間の表示(tools/add_readtime.pyで入る)"),
    ("data-site-modal", "お問い合わせモーダル"),
    ("application/ld+json", "構造化データ(検索エンジン向け)"),
    ('rel="canonical"', "正規URL指定"),
    ("og:title", "SNSシェア用タイトル"),
    ("assets/js/news-data.js", "記事台帳スクリプト"),
    ("assets/js/photos-data.js", "写真データスクリプト"),
    ("assets/js/article-related.js", "あわせて読みたいスクリプト"),
    ("assets/js/main.js", "共通スクリプト"),
    ('name="description"', "検索結果に出る説明文(description)"),
    ("goatcounter", "アクセス解析タグ(無いと閲覧数が数えられない)"),
    ('type="application/rss+xml"', "RSS発見リンク(feed.xmlへの案内)"),
    ('class="memou-intro"', "冒頭のメモうの吹き出し(2026-08-30から標準部品)"),
    ('id="related-list-items"', "あわせて読みたいの置き場(無いとJSが差し込めない)"),
    ('class="source-box-posted"', "掲載日の表記"),
]

# 補足: assets/js/article-images.js は記事ページではなく一覧ページ(index/news/best)が
# 読み込むスクリプトになった(2026-08時点の実態)。記事側の必須部品には含めない。

# 読み物ページ(book / jiyu-kenkyu)に必要な部品
READING_REQUIRED = [
    ("application/ld+json", "構造化データ(検索エンジン向け)"),
    ('rel="canonical"', "正規URL指定"),
    ("og:title", "SNSシェア用タイトル"),
    ('name="description"', "検索結果に出る説明文(description)"),
    ("goatcounter", "アクセス解析タグ(無いと閲覧数が数えられない)"),
]

# タイトルの末尾に付く、サイト側の決まり文句
# (「記事名｜大洲の自由研究｜ OZU LIFE MEMO」のように二段重ねになる)
# 公開URLのパス部分。404ページなどが絶対パスで書いている
SITE_BASE = "/ozu-life-memo/"

SITE_SUFFIXES = [
    "OZU LIFE MEMO",
    "大洲の自由研究",
    "大洲と読書",
    "大洲ノート",
    "大洲の歴史",
    "大洲検定",
    "大洲のとなり人",
]

# 個人を特定しうる語の一覧は、このリポジトリには置かない。
# リポジトリの外(private-notes/banned-words.py、.gitignore 済み)から読み込む。
# そのファイルが無い環境では匿名性チェックだけを飛ばし、他の点検は通常どおり動く。
BANNED = []
SUSPECT = []
ALLOW = []
_words = Path(__file__).resolve().parent.parent / "private-notes" / "banned-words.py"
if _words.exists():
    _ns = {}
    exec(compile(_words.read_text(encoding="utf-8"), str(_words), "exec"), _ns)
    BANNED = _ns.get("BANNED", [])
    SUSPECT = _ns.get("SUSPECT", [])
    ALLOW = _ns.get("ALLOW", [])      # 当たっても見逃してよい文字列(実在の地名など)

# 敬体(ですます調)の語尾。常体に統一する方針なので混在を警告する
KEITAI = [r"ました。", r"ています。", r"ません。", r"します。", r"です。", r"ます。"]

# 数か月で消えるので出典に使ってはいけないドメイン
FRAGILE_DOMAINS = ["news.yahoo.co.jp"]

# 記事1本あたりの目安
MIN_SOURCES = 2   # 出典は2本以上(本人の明示指示)
MIN_SOURCES_KENKYU = 12   # 自由研究は12本以上が方針(2026-08-19に確立)
MIN_H2 = 2        # 出典欄を除いた見出しの最低数
MIN_STRONG = 1    # 太字の最低数
MAX_KEITAI = 3    # 敬体の語尾がこれを超えたら混在を疑う

# 「取ってつけた呼びかけ」で締めない、というルールは前から文章では書いてあった。
# それでも147本中3本に生き残っていた。文章で頼むのをやめて、機械に持たせる。
NG_PHRASES = [
    (r"知ってほしい", "取ってつけた呼びかけ"),
    (r"知っておいてほしい", "取ってつけた呼びかけ"),
    (r"知っていただきたい", "取ってつけた呼びかけ"),
    (r"考えてみてほしい", "取ってつけた呼びかけ"),
    (r"感じてほしい", "取ってつけた呼びかけ"),
]

# 1文の目安は40〜50字。ここを超えるものは読点でつなぎすぎた長い文になっている。
# 既存記事の実測(2026-08-29)では150字超が17本。そこを上限にした。
MAX_SENTENCE = 150

# 冒頭の要点ボックスは3行(急いでいる読者が3行で帰れる形)
SUMMARY_LINES = 3

# タイトルに残してはいけない、行政資料の目次言葉。
# ただし「〜を中高生でも分かるように読み解く」のように、日常語に翻訳する約束が
# タイトル自体に書いてあるときは成立しているので見逃す。
TITLE_JARGON = ["策定", "財源内訳", "地域移行", "KPI", "CLT",
                "利活用", "推進計画", "基本構想", "実施要綱", "見える化"]
TITLE_JARGON_OK = ["分かる", "わかる", "読み解く", "かみくだ", "やさしく", "とは何か"]

# 予讃線は非電化。「電車」と書くと事実が違う(本人の明示指示)
NONDENKA = ("予讃線", "電車")

# 公開URL(canonical / og:url の照合に使う)
BASE_URL = "https://ozulifememo.github.io/ozu-life-memo/"

# 個人のストレージへのリンクは貼らない(読者が開けないうえ、公開範囲の事故になる)
STORAGE_LINKS = ["drive.google.com", "docs.google.com", "dropbox.com"]

# Notionからの貼り戻しで紛れ込む「似ているが違う字」。check_mojibake.py の辞書から、
# ふつうの日本語文で正当に使われうる字(畔・喰・儒・畧など)を除いた分だけを見る。
# 誤検知がありうるので警告どまり(見て判断)。
MOJI_LOOKALIKE = "頨絤胝痑偿賫綌怱聢圈蠟戗櫔"

# 日本語の本文に混ざったら事故の文字体系(キリル・ハングル・タイ・デーヴァナーガリー等)
FOREIGN_SCRIPT = re.compile("[Ѐ-ӿ가-힯฀-๿ऀ-ॿ֐-׿؀-ۿ]")
# アクセント付きラテン文字。×(乗算)と÷(除算)は数式で正当に使うので除く。警告どまり
LATIN_ODD = re.compile("[À-ÖØ-öø-ɏ]")

# 打ち間違いの定番。左が誤り(かもしれない)字、右が理由。error=Trueは正解が1つのもの
TYPO_WORDS = [
    ("肘川", "川の名前は肱川(ひじかわ)。肘は誤字", True),
    ("大州", "市名は大洲。歴史的表記の引用なら見逃してよい", False),
    ("富士山", "大洲の山は冨士山(とみすやま)。静岡の富士山の話なら見逃してよい", False),
]

# 「今年」「去年」などの相対的な時期の言葉は、読まれる頃には意味がずれる。
# 公開済みの記事には適用せず、この日付以降に掲載する記事にだけ警告する(目安)。
RELATIVE_WORDS = ["今年", "去年", "昨年", "来年", "先月", "今月"]
RELATIVE_WORDS_SINCE = "2026-09-01"

# 「あとで追記したい」と書いた約束を月次で拾うための言い回し(--promises で一覧)
PROMISE_PHRASES = ["追記したい", "追記する", "分かり次第", "わかり次第", "続報"]


# ---------------------------------------------------------------------------
# 小さな道具
# ---------------------------------------------------------------------------

class Report:
    """見つけた問題をためておく入れ物"""

    def __init__(self):
        self.errors = []    # 直した方がよいもの
        self.warns = []     # 見て判断するもの
        self.section_status = {}

    def error(self, path, kind, message, detail=None):
        self.errors.append({"path": path, "kind": kind, "message": message, "detail": detail})

    def warn(self, path, kind, message, detail=None):
        self.warns.append({"path": path, "kind": kind, "message": message, "detail": detail})


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def strip_quotes(text: str) -> str:
    """引用符の中身を取り除く。

    「あの人は「そう思う」と言った」のように入れ子になっていると、
    単純な正規表現では外側が閉じられず除去に失敗する。内側から順に
    消して、変化がなくなるまで繰り返すことで入れ子に対応する。
    """
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"「[^「」]*」", "", text)
        text = re.sub(r"『[^『』]*』", "", text)
    return text


def strip_tags(html: str) -> str:
    """HTMLタグと、script/styleの中身を取り除いて本文だけにする"""
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def body_only(html: str) -> str:
    """<head>を除いた、実際に読者が読む部分だけを返す"""
    m = re.search(r"<body\b[^>]*>(.*)</body>", html, flags=re.S | re.I)
    return m.group(1) if m else html


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def page_type(path: Path) -> str:
    p = rel(path)
    if p.startswith("eachnews/"):
        return "article"
    if p.startswith("book/") and not p.endswith("/index.html"):
        return "book"
    if p.startswith("jiyu-kenkyu/") and not p.endswith("/index.html"):
        return "kenkyu"
    return "page"


def collect_pages() -> list[Path]:
    """点検対象のHTMLを集める(作業用ファイル・worktreeは除く)"""
    pages = []
    for p in REPO.rglob("*.html"):
        rp = p.relative_to(REPO).as_posix()
        # pr/ はSNS展開用の内部素材置き場(gitignore済み、GitHub Pagesに載らない)
        # tools/_gikai_cache/ は会議録のダウンロード置き場(記事ではない)
        if rp.startswith((".claude/", "node_modules/", "docs/", "pr/", "private-notes/", "tools/")):
            continue
        if p.name.startswith("_"):      # _measure.html などの検証用
            continue
        pages.append(p)
    return sorted(pages)


# ---------------------------------------------------------------------------
# 台帳(news-data.js)の読み取り
# ---------------------------------------------------------------------------

def load_registry() -> dict:
    """news-data.js から記事の一覧を取り出す。

    以前は正規表現で流し読みしていたが、体裁が少し変わると黙って
    記事を取りこぼす(実際に156本中2本を落としていた)。波かっこの
    深さを数えて1件ずつ切り出し、取りこぼしがあれば検査側で気づける
    ように、ファイル中の slug の出現数も一緒に控えておく。
    """
    js_path = REPO / "assets" / "js" / "news-data.js"
    if not js_path.exists():
        return {}
    js = read(js_path)
    m = re.search(r"const OZU_NEWS\s*=\s*\[", js)
    if not m:
        return {}

    records = {}
    depth = 0
    start = None
    order = []
    for i in range(m.end(), len(js)):
        ch = js[i]
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                block = js[start:i]
                rec = {}
                for fm in re.finditer(r'(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"', block):
                    rec[fm.group(1)] = fm.group(2).replace('\\"', '"').replace("\\\\", "\\")
                tm = re.search(r"tags\s*:\s*\[([^\]]*)\]", block)
                rec["tags"] = re.findall(r'"([^"]+)"', tm.group(1)) if tm else []
                if "slug" in rec:
                    records[rec["slug"]] = rec
                    order.append(rec["slug"])
        elif ch == "]" and depth == 0:
            break

    records["__order__"] = order
    records["__slug_mentions__"] = len(re.findall(r'slug\s*:\s*"', js))
    tags_m = re.search(r"const OZU_TAGS\s*=\s*\[([^\]]*)\]", js, flags=re.S)
    records["__all_tags__"] = re.findall(r'"([^"]+)"', tags_m.group(1)) if tags_m else []
    return records


def registry_articles(registry: dict) -> dict:
    """__〜__ の管理用キーを除いた、slug→記事情報だけの辞書"""
    return {k: v for k, v in registry.items() if not k.startswith("__")}


def load_sitemap() -> set:
    """sitemap.xml に載っているURLの一覧"""
    sm = REPO / "sitemap.xml"
    if not sm.exists():
        return set()
    return set(re.findall(r"<loc>\s*(.*?)\s*</loc>", read(sm)))


# ---------------------------------------------------------------------------
# 個々の点検
# ---------------------------------------------------------------------------

def source_urls(path, html) -> list:
    """そのページの出典URLを取り出す。書き方がページ種別で違う。

    記事(eachnews)・読書(book) … class="source-link" のリンク
    自由研究(jiyu-kenkyu)       … 脚注の <a href>(source-linkを使っていない)
    """
    body = body_only(html)
    if page_type(path) == "kenkyu":
        urls = re.findall(r'<a\s[^>]*href="(https?://[^"]+)"', body)
        urls = [htmllib.unescape(u) for u in urls]
        return [u for u in dict.fromkeys(urls) if "ozulifememo" not in u]
    urls = re.findall(r'class="source-link"\s+href="(https?://[^"]+)"', body)
    # HTMLでは & を &amp; と書くのが正しい。実際に叩くURLに戻してから確認する
    # (戻さないと e-stat のような ?a=1&amp;b=2 形式が全部404に見える)
    urls = [htmllib.unescape(u) for u in urls]
    return list(dict.fromkeys(urls))


def check_structure(path, html, rep):
    """必要な部品が揃っているか"""
    kind = page_type(path)
    required = list(CHROME_REQUIRED)
    if kind == "article":
        required += ARTICLE_REQUIRED
    elif kind in ("book", "kenkyu"):
        required += READING_REQUIRED

    for needle, label in required:
        if needle not in html:
            rep.error(rel(path), "構造", f"{label} が見当たりません", f"       探した文字列: {needle}")


def check_tag_balance(path, html, rep):
    """タグの開き閉じが合っているか"""
    body = body_only(html)
    # HTMLコメントの中のタグは、画面には出ないので数えない。
    # new_kiji.py が置く「段落は <p class="commentary">、見出しは <h2>」という
    # 書き置きを数えてしまい、本文が正しいのにエラーが出ていた(2026-08-31)。
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    for tag in ("div", "h2", "strong", "section", "p"):
        opens = len(re.findall(rf"<{tag}\b", body, flags=re.I))
        closes = len(re.findall(rf"</{tag}>", body, flags=re.I))
        if opens != closes:
            rep.error(
                rel(path), "タグ",
                f"<{tag}> の開き{opens}個 と 閉じ{closes}個 が合っていません",
                "       レイアウトが崩れる原因になります",
            )


def check_titles(path, html, registry, rep):
    """タイトルが4か所(title / og:title / JSON-LD / h1)と台帳で一致しているか"""
    if page_type(path) not in ("article", "book", "kenkyu"):
        return

    def grab(pattern, flags=0):
        m = re.search(pattern, html, flags)
        return m.group(1).strip() if m else None

    suffix = "｜ OZU LIFE MEMO"

    def norm(s):
        """比較用にタイトルをそろえる。
        og:title は &quot; 、JSON-LD は \\" のように書き方が違うだけで
        中身は同じことが多いので、エスケープを元に戻してから比べる。"""
        if s is None:
            return None
        s = re.sub(r"<[^>]+>", "", s)
        # 「記事名｜大洲の自由研究｜ OZU LIFE MEMO」のように接尾辞が
        # 二段重ねになっていることがあるので、無くなるまで繰り返し取り除く
        changed = True
        while changed:
            changed = False
            for suffix in SITE_SUFFIXES:
                new = re.sub(rf"\s*[｜|]\s*{re.escape(suffix)}\s*$", "", s)
                if new != s:
                    s, changed = new, True
        # JSONのエスケープを戻す
        s = s.replace('\\"', '"').replace("\\\\", "\\").replace("\\/", "/")
        # HTMLの実体参照を戻す
        for ent, ch in [("&quot;", '"'), ("&#39;", "'"), ("&apos;", "'"),
                        ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "), ("&amp;", "&")]:
            s = s.replace(ent, ch)
        # 見た目が同じで区別しても意味のない記号をそろえる
        s = s.translate(str.maketrans('“”‘’＂＇', '""\'\'"\''))
        return re.sub(r"\s+", "", s).strip()

    t_title = norm(grab(r"<title>(.*?)</title>", re.S | re.I))
    t_og = norm(grab(r'<meta\s+property="og:title"\s+content="(.*?)"', re.S | re.I))
    t_ld = norm(grab(r'"headline"\s*:\s*"((?:[^"\\]|\\.)*)"', re.S))
    t_h1 = norm(grab(r"<h1[^>]*>(.*?)</h1>", re.S | re.I))

    found = {"<title>": t_title, "og:title": t_og, "JSON-LD": t_ld, "<h1>": t_h1}
    present = {k: v for k, v in found.items() if v}
    if len(set(present.values())) > 1:
        detail = "\n".join(f"       {k:10s}: {v}" for k, v in present.items())
        rep.error(rel(path), "タイトル", "ページ内でタイトルが食い違っています", detail)

    # 台帳(news-data.js)との照合は記事ページのみ
    if page_type(path) == "article":
        slug = path.stem
        rec = registry.get(slug)
        if rec is None:
            rep.error(rel(path), "台帳", "news-data.js にこの記事が登録されていません",
                      "       記事一覧・トップページに出てきません")
        else:
            reg_title = norm(rec.get("title"))
            if reg_title and t_h1 and reg_title != t_h1:
                rep.error(
                    rel(path), "タイトル", "記事本文と news-data.js のタイトルが違います",
                    f"       記事(h1) : {grab(r'<h1[^>]*>(.*?)</h1>', re.S | re.I)}\n"
                    f"       台帳     : {rec.get('title')}",
                )


def check_tables(path, html, rep):
    """記事内の<table>がスクロール用の囲いに入っているか。

    囲いが無い表は、スマホ幅で中身が入り切らないときにページ全体を
    横に突き破る(2026-08-20のブラウザ点検で9記事が実際にはみ出していた)。
    記事の表は <div style="overflow-x:auto;"> で包むのがこのサイトの決まり。
    共通クラス .article-table-wrap も同じ役割なので、こちらでもよい。
    """
    if page_type(path) not in ("article", "book", "kenkyu"):
        return
    body = body_only(html)
    for m in re.finditer(r"<table\b", body):
        before = body[max(0, m.start() - 250):m.start()]
        if "overflow-x" not in before and "article-table-wrap" not in before:
            line = html[:html.find(body) + m.start()].count("\n") + 1
            rep.error(rel(path), "表", f"スクロール用の囲いが無い表があります({line}行目付近)",
                      "       スマホで表がページ幅を突き破る原因になります。\n"
                      '       <div class="article-table-wrap"> で表を包んでください')
            break   # 1ファイル1件で十分
    check_table_cells(path, body, rep)


def check_table_cells(path, body, rep):
    """表の各行のセル数が、見出しの行とそろっているか。

    2026-09-03、jiyu-kenkyu/ozu-rosenka-44nen.html の地価の表で、1行だけ
    <td> が1つ足りず、年と価格の対応が1つずつずれて表示されていた。
    見た目には気づけないうえ、**読者は間違った年の地価を読むことになる**。
    正解が1つしかない不具合なので、目安ではなくエラーにする。

    rowspan を使っている表は行ごとのセル数が変わって当然なので見ない。
    """
    for tbl in re.finditer(r"(?s)<table\b.*?</table>", body):
        t = tbl.group(0)
        if "rowspan" in t:
            continue
        widths = []
        for tr in re.finditer(r"(?s)<tr\b.*?</tr>", t):
            w = 0
            for cell in re.finditer(r"<t[dh]\b([^>]*)>", tr.group(0)):
                m = re.search(r'colspan\s*=\s*"?(\d+)', cell.group(1))
                w += int(m.group(1)) if m else 1
            if w:
                widths.append((w, tr.group(0)))
        if not widths:
            continue
        head = widths[0][0]
        for w, tr in widths[1:]:
            if w != head:
                first = re.search(r"(?s)<t[dh]\b[^>]*>(.*?)</t[dh]>", tr)
                label = re.sub(r"<[^>]+>", "", first.group(1)).strip() if first else "?"
                rep.error(rel(path), "表",
                          f"セルの数がそろっていない行があります(見出しは{head}個、"
                          f"この行は{w}個): 「{label[:30]}」",
                          "       年と値の対応が1つずつずれて表示されます。\n"
                          "       足りないセルを補うか、余分なセルを消してください")


def check_anonymity(path, html, rep):
    """本文に個人が特定できる語が入っていないか。

    ALLOW(当たっても見逃してよい文字列)は check_repo_anonymity と同じものを見る。
    2026-09-03、記事の表に1行だけ出てくる県道名が引っかかったときに、
    こちらだけ ALLOW を見ていないことが分かった。本人の線引きは
    「記事の中に普通に出てくる地名は良い。その付近で働いていると
    分からなければ許す」。だから語そのものではなく、その語を含む
    固有名詞の並びのときだけ見逃す。
    """
    text = strip_tags(body_only(html))

    for pattern, why in BANNED:
        for m in re.finditer(pattern, text):
            around = text[max(0, m.start() - 30): m.end() + 30]
            if any(a in around for a in ALLOW):
                continue
            rep.error(rel(path), "匿名性", f"「{m.group(0)}」が本文にあります({why})",
                      f"       …{around}…")
            break   # 1ファイル1件で十分

    for pattern, why in SUSPECT:
        for m in re.finditer(pattern, text):
            around = text[max(0, m.start() - 30): m.end() + 30]
            if any(a in around for a in ALLOW):
                continue
            rep.warn(rel(path), "匿名性", f"「{m.group(0)}」が本文にあります({why})",
                     f"       …{around}…")
            break


def check_mojibake(path, html, rep):
    """文字化けの痕跡がないか"""
    for m in re.finditer(r"[�]", html):
        around = html[max(0, m.start() - 40): m.end() + 40].replace("\n", " ")
        rep.error(rel(path), "文字化け", "文字化け記号が含まれています", f"       …{around}…")
        break
    # 実体参照の書き損じ(&amp;amp; のような二重エスケープ)
    if "&amp;amp;" in html:
        rep.warn(rel(path), "文字化け", "二重エスケープ(&amp;amp;)が含まれています")


def check_style(path, html, rep, show_headings=False):
    """note風スタイルの最低ラインを満たしているか"""
    kind = page_type(path)
    if kind not in ("article", "book", "kenkyu"):
        return

    body = body_only(html)

    # 出典欄の見出しは数えない
    h2_all = re.findall(r"<h2[^>]*>(.*?)</h2>", body, flags=re.S | re.I)
    h2_count = len([h for h in h2_all if "出典" not in h and "参考" not in h])
    strong_count = len(re.findall(r"<strong\b", body, flags=re.I))
    source_count = len(re.findall(r'class="source-link"', body))

    if kind == "kenkyu":
        n = len(source_urls(path, html))
        if n < MIN_SOURCES_KENKYU:
            rep.warn(rel(path), "出典", f"出典が{n}本です(自由研究は{MIN_SOURCES_KENKYU}本以上が方針)",
                     "       自由研究は調べ物の記録なので、記事より厚い裏取りを求めている")

    if kind == "article":
        if source_count < MIN_SOURCES:
            rep.error(rel(path), "出典", f"出典が{source_count}本しかありません(2本以上)",
                      "       1本だけだと、その1本が間違っていたら記事ごと崩れます")
        if h2_count < MIN_H2:
            rep.warn(rel(path), "スタイル", f"見出し(h2)が{h2_count}個しかありません")
        if strong_count < MIN_STRONG:
            rep.warn(rel(path), "スタイル", "太字(strong)が1つも使われていません")

    # 文体の統一。eachnews(大洲ノート)は常体、book(大洲と読書)は敬体が
    # それぞれの作法なので、常体チェックは eachnews だけに掛ける。
    if kind == "article":
        text = strip_tags(body)
        text = strip_quotes(text)   # 引用の中は数えない(人のコメントは敬体のまま)
        hits = sum(len(re.findall(k, text)) for k in KEITAI)
        if hits > MAX_KEITAI:
            rep.warn(rel(path), "文体", f"敬体(ですます調)の語尾が{hits}箇所あります",
                     "       大洲ノートは常体(〜だ/〜である)に統一する方針です")

    # 疑問形の見出しは「そこで答えを書く」という約束なので、答えが
    # 書かれているかを人が見る必要がある。ただし件数が多く毎回出すと
    # うるさいので、--headings を付けたときだけ一覧にする。
    if show_headings:
        for h in h2_all:
            plain = re.sub(r"<[^>]+>", "", h).strip()
            if re.search(r"(のか[?？]?|だろうか|でしょうか|[?？])$", plain):
                rep.warn(rel(path), "見出し", f"疑問形の見出し「{plain}」",
                         "       直後の段落が実際に答えになっているか、目で確認してください")


def check_phrasing(path, html, rep):
    """文章の作法。これまで文章のルールとしてしか無く、守られ方がまちまちだったもの"""
    kind = page_type(path)
    if kind not in ("article", "book"):
        return

    body = body_only(html)
    text = strip_tags(body)
    # 呼びかけの判定は、引用された他人の文章を除いた地の文だけで行う
    jibun = strip_quotes(text)

    # 取ってつけた呼びかけ
    for pattern, why in NG_PHRASES:
        m = re.search(pattern, jibun)
        if m:
            around = jibun[max(0, m.start() - 35): m.end() + 20]
            around = " ".join(around.split())
            rep.warn(rel(path), "表現", f"「{m.group(0)}」があります({why})",
                     f"       …{around}…\n"
                     "       本人が実際に感じたことで締める。呼びかけで締めない")
            break

    # 長すぎる1文
    worst, worst_len = "", 0
    for m in re.finditer(r"<p(?:\s[^>]*)?>(.*?)</p>", body, flags=re.S | re.I):
        para = strip_tags(m.group(1))
        for sent in re.split(r"(?<=。)", para):
            sent = sent.strip()
            # 句点で終わらないものは「文」ではない(時刻表や箇条書きの行)ので数えない
            if not sent.endswith("。"):
                continue
            if len(sent) > worst_len:
                worst, worst_len = sent, len(sent)
    if worst_len > MAX_SENTENCE:
        rep.warn(rel(path), "文章", f"1文が{worst_len}字あります(目安40〜50字)",
                 f"       {worst[:60]}…\n"
                 "       読点でつながず、途中で切って2文に分けてください")

    # 要点ボックスの行数
    m = re.search(r'<div class="article-summary".*?</ul>', body, flags=re.S)
    if m:
        lines = len(re.findall(r"<li", m.group(0)))
        if lines != SUMMARY_LINES:
            rep.warn(rel(path), "要点", f"冒頭の要点が{lines}行あります(3行が基本)",
                     "       核心の事実 / 裏付けの数字 / 読者への意味、の3行")

    # 予讃線は非電化
    if NONDENKA[0] in text and NONDENKA[1] in text:
        rep.warn(rel(path), "事実", "予讃線の記事に「電車」があります",
                 "       大洲を通る予讃線は非電化。「列車」が正しい")

    # タイトルに行政用語が残っていないか
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S)
    if h1 and kind == "article":
        title = strip_tags(h1.group(1)).strip()
        if not any(ok in title for ok in TITLE_JARGON_OK):
            for word in TITLE_JARGON:
                if word in title:
                    rep.warn(rel(path), "タイトル",
                             f"タイトルに行政用語「{word}」があります",
                             f"       {title}\n"
                             "       主語を制度ではなく読者の生活の出来事にする")
                    break


def check_links(path, html, rep):
    """画像とページ内リンクの行き先が実在するか"""
    body = body_only(html)
    # <script>の中はJavaScriptのテンプレート(${...})なので見ない
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)

    def resolve(ref: str):
        ref = ref.split("#")[0].split("?")[0]
        if not ref:
            return None
        if ref.startswith(SITE_BASE):                 # 公開URLと同じ絶対パス
            return REPO / ref[len(SITE_BASE):]
        if ref.startswith("/"):
            return None                               # サイト外の絶対パス。見ない
        return path.parent / ref

    for tag, attr, label in (("img", "src", "画像"), ("a", "href", "リンク")):
        for ref in re.findall(rf'<{tag}[^>]+{attr}="([^"]+)"', body, flags=re.I):
            if ref.startswith(("http", "data:", "mailto:", "tel:", "#", "javascript:")):
                continue
            if "${" in ref or "' +" in ref or '" +' in ref:
                continue                              # 組み立て途中の文字列
            target = resolve(ref)
            if target is None:
                continue
            if not target.exists():
                rep.error(rel(path), label, f"{label}の行き先がありません: {ref}",
                          "       読者にはリンク切れ・画像切れとして見えます")


def check_title_numbers(path, html, rep):
    """タイトルに出した数字が、本文にもあるか

    タイトルだけ直して本文を直し忘れる(またはその逆)と、読者は
    「見出しの数字が本文にない」という一番不信感の出る形で気づく。
    """
    if page_type(path) != "article":
        return
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.S)
    if not m:
        return
    title = strip_tags(m.group(1))
    body = strip_tags(body_only(html)).replace(",", "")
    for num in re.findall(r"\d[\d,]*(?:\.\d+)?", title):
        if num.replace(",", "") not in body:
            rep.error(rel(path), "タイトル",
                      f"タイトルの数字「{num}」が本文にありません",
                      f"       {title}\n"
                      "       タイトルだけ直して本文を直し忘れていないか確認してください")
            break


def check_sources(path, html, rep):
    """出典リンクの質(消えやすいドメインを使っていないか)"""
    for url in source_urls(path, html):
        # ウェブアーカイブ版は元URLを含むが、保存済みなので消えない。除外する。
        if url.startswith("https://web.archive.org/") or url.startswith("http://web.archive.org/"):
            continue
        for dom in FRAGILE_DOMAINS:
            if dom in url:
                rep.error(rel(path), "出典", f"消えやすいURLを出典にしています({dom})",
                          f"       {url}\n       官公庁・大学・企業の公式発表に差し替えてください")


def expected_page_url(path) -> str:
    """このファイルが公開されたときのURL"""
    return BASE_URL + rel(path)


def collect_ids(pages) -> dict:
    """ページ内リンクの照合用に、全ページの id / name を集める"""
    ids = {}
    for p in pages:
        html = read(p)
        ids[rel(p)] = (set(re.findall(r'\bid="([^"]+)"', html))
                       | set(re.findall(r'\bname="([^"]+)"', html)))
    return ids


def check_head_meta(path, html, registry, rep):
    """<head>の中身(canonical・OGP・JSON-LD)が置き場所と食い違っていないか"""
    if page_type(path) not in ("article", "book", "kenkyu"):
        return
    expect = expected_page_url(path)

    m = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    if m and m.group(1) != expect:
        rep.error(rel(path), "メタ", "canonical が実際のURLと違います",
                  f"       いま  : {m.group(1)}\n       正しく: {expect}")
    m = re.search(r'<meta property="og:url" content="([^"]+)"', html)
    if m and m.group(1) != expect:
        rep.error(rel(path), "メタ", "og:url が実際のURLと違います", f"       {m.group(1)}")
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if m:
        if m.group(1).startswith(BASE_URL):
            if not (REPO / m.group(1)[len(BASE_URL):]).exists():
                rep.error(rel(path), "メタ", "og:image の画像ファイルがありません", f"       {m.group(1)}")
        else:
            rep.warn(rel(path), "メタ", "og:image がこのサイト以外のURLです", f"       {m.group(1)}")

    # og:title にだけはサイト名を付けない(LINEで2行に切れる。2026-08-20からの決まり)
    m = re.search(r'<meta property="og:title" content="([^"]*)"', html)
    if m and "OZU LIFE MEMO" in m.group(1):
        rep.error(rel(path), "メタ", "og:title に「｜ OZU LIFE MEMO」が付いています",
                  "       og:title だけはサイト名を付けない決まり(LINEでタイトルが切れるため)")
    m = re.search(r"<title>(.*?)</title>", html, flags=re.S)
    if m and "OZU LIFE MEMO" not in m.group(1):
        rep.error(rel(path), "メタ", "<title> にサイト名が付いていません",
                  "       「記事名 ｜ OZU LIFE MEMO」の形にする")

    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, flags=re.S)
    if m:
        try:
            data = json.loads(m.group(1))
        except Exception as e:
            rep.error(rel(path), "メタ", "JSON-LD が壊れています(JSONとして読めません)", f"       {e}")
            data = {}
        if page_type(path) == "article":
            reg = registry.get(path.stem) or {}
            ld_date = data.get("datePublished")
            if ld_date and reg.get("date") and ld_date != reg["date"]:
                rep.error(rel(path), "日付", "JSON-LD の datePublished が台帳と違います",
                          f"       JSON-LD: {ld_date} / 台帳: {reg['date']}")


def check_link_hygiene(path, html, rep):
    """リンクと画像の書き方(公開範囲・セキュリティ・読み上げ配慮)"""
    if page_type(path) not in ("article", "book", "kenkyu"):
        return
    body = body_only(html)

    for bad in STORAGE_LINKS:
        if bad in html:
            rep.error(rel(path), "リンク", f"個人ストレージへのリンクがあります({bad})",
                      "       読者が開けないうえ、共有範囲の事故につながる。公式の公開URLに差し替える")
            break

    n = sum(1 for m in re.finditer(r'<a\b[^>]*target="_blank"[^>]*>', body)
            if "noopener" not in m.group(0))
    if n:
        rep.error(rel(path), "リンク", f'target="_blank" に rel="noopener" が無いリンクが{n}個あります',
                  '       <a target="_blank" rel="noopener"> の形にする')

    for m in re.finditer(r"<img\b[^>]*>", body):
        if "alt=" not in m.group(0):
            rep.error(rel(path), "画像", "alt属性の無い画像があります",
                      f'       {m.group(0)[:70]}\n       飾りの画像でも alt="" と書く(読み上げ環境への配慮)')
            break


def check_typos(path, html, rep):
    """誤字・記号のねじれ。正解が1つのものはエラー、文脈によるものは警告"""
    text = strip_tags(body_only(html))
    jibun = strip_quotes(text)

    for word, why, is_error in TYPO_WORDS:
        if word in jibun:
            i = jibun.find(word)
            around = " ".join(jibun[max(0, i - 20): i + 25].split())
            f = rep.error if is_error else rep.warn
            f(rel(path), "誤字", f"「{word}」があります({why})", f"       …{around}…")

    for a, b, is_error in (("「", "」", True), ("『", "』", True), ("（", "）", False)):
        ca, cb = text.count(a), text.count(b)
        if ca != cb:
            f = rep.error if is_error else rep.warn
            f(rel(path), "誤字", f"かぎかっこの開き閉じが合いません({a}={ca}個 {b}={cb}個)",
              "       消し忘れ・書きかけの跡であることが多い")

    if "。。" in text.replace("。。。", ""):
        i = text.find("。。")
        rep.error(rel(path), "誤字", "句点が連続しています(。。)",
                  f"       …{text[max(0, i - 20): i + 20]}…")
    if "、、" in text:
        rep.error(rel(path), "誤字", "読点が連続しています(、、)")
    for zw, name in (("​", "ゼロ幅スペース"), ("­", "ソフトハイフン")):
        if zw in body_only(html):
            rep.error(rel(path), "誤字", f"見えない文字({name})が紛れています")
            break

    m = FOREIGN_SCRIPT.search(text)
    if m:
        i = m.start()
        rep.error(rel(path), "誤字", f"日本語の本文に別の文字体系の字があります(「{m.group(0)}」)",
                  f"       …{text[max(0, i - 15): i + 15]}…")
    m = LATIN_ODD.search(text)
    if m:
        i = m.start()
        rep.warn(rel(path), "誤字", f"アクセント付きラテン文字があります(「{m.group(0)}」)",
                 f"       …{text[max(0, i - 15): i + 15]}…\n"
                 "       外国語の綴りの引用として正しいなら、そのままでよい")
    hits = [c for c in MOJI_LOOKALIKE if c in text]
    if hits:
        rep.warn(rel(path), "誤字", "Notion経由で化けやすい字が含まれています(" + "".join(hits) + ")",
                 "       前後を読み、化けなら直す。正しい用字ならそのままでよい")


def check_fragments(path, html, id_map, rep):
    """ページ内リンク(#〜)の行き先IDが実在するか。check_links はファイルの有無しか見ない"""
    body = body_only(html)
    body = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
    for m in re.finditer(r'href="([^"]*#[^"]+)"', body):
        ref = m.group(1)
        if ref.startswith(("http", "mailto:", "javascript:")) or "${" in ref:
            continue
        fpart, frag = ref.split("#", 1)
        if not frag:
            continue
        if fpart == "":
            target = rel(path)
        else:
            fpart = fpart.split("?")[0]
            if fpart.startswith("/"):
                continue
            try:
                target = (path.parent / fpart).resolve().relative_to(REPO.resolve()).as_posix()
            except Exception:
                continue
            if target.endswith("/"):
                target += "index.html"
        ids = id_map.get(target)
        if ids is None:
            continue          # ファイル自体の有無は check_links が見る
        if frag not in ids:
            rep.error(rel(path), "アンカー", f"リンクの行き先ID「#{frag}」がありません",
                      f"       {ref}\n       押しても何も起きないリンクになっています")


def check_article_registry_sync(path, html, registry, rep):
    """記事の表示(掲載日・カテゴリ・読了時間・資料数)が台帳・実体とそろっているか"""
    if page_type(path) != "article":
        return
    body = body_only(html)
    reg = registry.get(path.stem)

    m = re.search(r'class="article-page" data-slug="([^"]+)"', body)
    if not m:
        rep.error(rel(path), "台帳", "data-slug がありません",
                  '       <div class="article-page" data-slug="ファイル名"> が関連記事抽出の目印になる')
    elif m.group(1) != path.stem:
        rep.error(rel(path), "台帳", f"data-slug がファイル名と違います({m.group(1)})",
                  "       「あわせて読みたい」の抽出が狂います")

    # 読了時間: add_readtime.py と同じ計算をして、走らせ忘れを見つける
    m = re.search(r'class="article-readtime">約(\d+)分で読める', body)
    if m:
        b = re.sub(r"<script\b.*?</script>", " ", body, flags=re.S | re.I)
        b = re.sub(r"<style\b.*?</style>", " ", b, flags=re.S | re.I)
        b = re.sub(r'<div class="content-block source-box".*', " ", b, flags=re.S)
        chars = len(re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", b)))
        want = max(1, round(chars / 550))
        if int(m.group(1)) != want:
            rep.error(rel(path), "日付",
                      f"読了時間(約{m.group(1)}分)が本文の長さと合いません(計算では約{want}分)",
                      "       本文を書き換えたら python tools/add_readtime.py を走らせる")

    # 「調べた資料 N本」= 実際の出典リンク数
    m = re.search(r'class="article-summary-sources">調べた資料\s*(\d+)本', body)
    if m:
        actual = len(re.findall(r'class="source-link"', body))
        if int(m.group(1)) != actual:
            rep.error(rel(path), "出典",
                      f"「調べた資料 {m.group(1)}本」が実際の出典数({actual}本)と違います",
                      "       出典を増減させたら、この数字も直す")

    if reg:
        # 掲載日の表記(2026/08/30 と 2026年8月30日 の両形式を許す。後ろの注記も許す)
        m = re.search(r'class="source-box-posted">この記事をサイトに掲載した日:\s*([^<]+)<', body)
        if m:
            shown = m.group(1).strip()
            dm = re.match(r"(\d{4})[/年](\d{1,2})[/月](\d{1,2})日?", shown)
            if dm:
                norm = f"{dm.group(1)}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"
                if reg.get("date") and norm != reg["date"]:
                    rep.error(rel(path), "日付", f"掲載日の表記({shown})が台帳({reg['date']})と違います")
            else:
                rep.error(rel(path), "日付", f"掲載日の表記が読み取れません({shown})")

        m = re.search(r'<span class="article-cat">([^<]+)</span>', body)
        cat_labels = {"ima": "大洲のいま", "kurashi": "大洲の暮らし", "shiten": "大洲の視点"}
        if m and reg.get("category") in cat_labels:
            if m.group(1).strip() != cat_labels[reg["category"]]:
                rep.error(rel(path), "台帳",
                          f"カテゴリ表示({m.group(1).strip()})が台帳({cat_labels[reg['category']]})と違います")


def check_relative_dates(path, html, registry, rep):
    """「今年」「去年」のような相対的な時期の言葉(新しく書く記事だけの目安)"""
    if page_type(path) != "article":
        return
    reg = registry.get(path.stem) or {}
    if not reg.get("date") or reg["date"] < RELATIVE_WORDS_SINCE:
        return
    jibun = strip_quotes(strip_tags(body_only(html)))
    hits = [w for w in RELATIVE_WORDS if w in jibun]
    if hits:
        rep.warn(rel(path), "文章", "相対的な時期の言葉があります(" + "・".join(hits) + ")",
                 "       読まれる頃には意味がずれやすい。「2026年」「令和8年度」のような固定の言い方も検討する")


def check_kenkyu_extra(path, html, rep):
    """自由研究(jiyu-kenkyu)ならではの決まり"""
    if page_type(path) != "kenkyu":
        return
    body = body_only(html)
    refs = set(re.findall(r'href="#(fn\d+)"', body))
    defs = set(re.findall(r'<li id="(fn\d+)"', body))
    for x in sorted(refs - defs):
        rep.error(rel(path), "アンカー", f'脚注の飛び先(id="{x}")がありません',
                  "       本文の脚注番号を押しても出典に飛べない状態です")
    text = strip_tags(body)
    if "<svg" not in body:
        rep.warn(rel(path), "スタイル", "図解(inline SVG)が見当たりません(自由研究は図解ありが方針)")
    if "調べても分からなかった" not in text and "調べてもわからなかった" not in text:
        rep.warn(rel(path), "スタイル", "「調べても分からなかったこと」の章が見当たりません",
                 "       見つからなかったことを正直に書くのが自由研究の方針(2026-08-19確立)")


def check_registry_file(registry, rep):
    """台帳(news-data.js)そのものの整合"""
    arts = registry_articles(registry)
    order = registry.get("__order__", [])
    mentions = registry.get("__slug_mentions__", len(arts))
    if mentions != len(order):
        rep.error("assets/js/news-data.js", "台帳",
                  f"台帳の読み取り数({len(order)})とslugの出現数({mentions})が合いません",
                  "       news-data.js の書式が崩れているか、点検器の読み取りが壊れています")
    if len(set(order)) != len(order):
        dup = sorted({s for s in order if order.count(s) > 1})
        rep.error("assets/js/news-data.js", "台帳", "slugが重複しています: " + ", ".join(dup))
    def valid_date(v: str) -> bool:
        try:
            datetime.strptime(v, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    all_tags = registry.get("__all_tags__", [])
    for slug, r in arts.items():
        if r.get("date") and not valid_date(r["date"]):
            rep.error("assets/js/news-data.js", "台帳", f"「{slug}」の日付の形式が変です({r['date']})",
                      "       YYYY-MM-DD の実在する日付にする")
        if r.get("sourceDate") and not valid_date(r["sourceDate"]):
            rep.error("assets/js/news-data.js", "台帳", f"「{slug}」のsourceDateの形式が変です({r['sourceDate']})",
                      "       YYYY-MM-DD の実在する日付にする")
        if r.get("category") not in ("ima", "kurashi", "shiten"):
            rep.error("assets/js/news-data.js", "台帳", f"「{slug}」のカテゴリが不正です({r.get('category')})",
                      "       ima / kurashi / shiten のどれか。新しい選択肢を勝手に増やさない(kokaiの決まり)")
        tags = r.get("tags", [])
        if not tags:
            rep.error("assets/js/news-data.js", "台帳", f"「{slug}」にタグがありません(1〜2個付ける)")
        else:
            bad = [t for t in tags if all_tags and t not in all_tags]
            if bad:
                rep.error("assets/js/news-data.js", "台帳",
                          f"「{slug}」にOZU_TAGSに無いタグがあります({'、'.join(bad)})")
            if len(tags) > 2:
                rep.warn("assets/js/news-data.js", "台帳", f"「{slug}」のタグが{len(tags)}個あります(1〜2個が決まり)")


def check_feed(registry, rep):
    """feed.xml が最新の記事を含んでいるか(make_feed.py の走らせ忘れを見つける)"""
    feed_p = REPO / "feed.xml"
    if not feed_p.exists():
        return
    feed = read(feed_p)
    links = re.findall(r"<link>\s*(.*?)\s*</link>", feed)
    feed_slugs = {u.rstrip("/").split("/")[-1].replace(".html", "") for u in links if "eachnews" in u}
    newest = registry.get("__order__", [])[:5]
    missing = [s for s in newest if s not in feed_slugs]
    if missing:
        rep.error("feed.xml", "台帳", "最新の記事がRSSに入っていません: " + ", ".join(missing),
                  "       記事を公開したら python tools/make_feed.py を走らせる")
    for u in links:
        if u.startswith(BASE_URL):
            r = u[len(BASE_URL):]
            if r and not r.endswith("/") and not (REPO / r).exists():
                rep.error("feed.xml", "台帳", f"RSSに載っているページが存在しません: {u}")


def check_sitemap_targets(sitemap, rep):
    """sitemap.xml のURLの行き先が実在するか(check_sitemapの逆向き)"""
    for loc in sorted(sitemap):
        if not loc.startswith(BASE_URL):
            rep.warn("sitemap.xml", "sitemap", f"サイト外のURLが載っています: {loc}")
            continue
        r = loc[len(BASE_URL):]
        if r == "" or r.endswith("/"):
            r += "index.html"
        if not (REPO / r).exists():
            rep.error("sitemap.xml", "sitemap", f"行き先の無いURLが載っています: {loc}",
                      "       Googleに「存在しないページ」を案内している状態です")


def list_promises(pages):
    """「分かり次第追記したい」のような約束を一覧にする(--promises)。検査ではなく月次巡視用"""
    print("\n  記事の中の「あとで追記する」系の約束(果たせたら本文を追記して消し込む):\n")
    n = 0
    for p in pages:
        if page_type(p) not in ("article", "book", "kenkyu"):
            continue
        text = strip_tags(body_only(read(p)))
        for sent in re.split(r"(?<=。)", text):
            if any(ph in sent for ph in PROMISE_PHRASES):
                n += 1
                print(f"    {rel(p)}")
                print(f"      {sent.strip()[:90]}")
    print(f"\n  合計 {n} 件。\n")


def git_changed_files() -> set:
    """gitから見て、いま手が入っている全ファイルのパス(フック用)"""
    import subprocess
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=str(REPO),
                             capture_output=True, text=True, encoding="utf-8",
                             timeout=20).stdout
    except Exception:
        return set()
    paths = set()
    for line in out.splitlines():
        if len(line) < 4:
            continue
        name = line[3:].strip().strip('"')
        if " -> " in name:          # リネームは移動先だけ見る
            name = name.split(" -> ")[-1]
        paths.add(name)
    return paths


def git_changed_pages() -> set:
    """gitから見て、いま手を入れているHTMLのパスを集める(フック用)"""
    return {p for p in git_changed_files() if p.endswith(".html")}


def check_repo_anonymity(rep):
    """リポジトリに入っている全テキストファイルに、個人が特定できる語が無いか。

    記事本文の検査(check_anonymity)は本文しか見ない。2026-08-29、道具が
    書き出した台帳(JSON)に名字が入ったままコミット・pushしてしまった。
    公開されるのは記事だけではない。git が追跡している全ファイルを見る。
    """
    import subprocess
    if not BANNED:
        return
    try:
        out = subprocess.run(["git", "ls-files"], cwd=str(REPO), capture_output=True,
                             text=True, encoding="utf-8", timeout=30).stdout
    except Exception:
        return
    skip_ext = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".pdf",
                ".woff", ".woff2", ".ttf", ".xlsx", ".zip")
    for f in out.split("\n"):
        if not f or f.lower().endswith(skip_ext):
            continue
        path = REPO / f
        if page_type(path) in ("article", "book", "kenkyu"):
            continue                      # 記事本文は check_anonymity が見ている
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern, why in BANNED:
            for m in re.finditer(pattern, text):
                around = text[max(0, m.start() - 30): m.end() + 30]
                if any(a in around for a in ALLOW):
                    continue
                rep.error(f, "匿名性", f"「{m.group(0)}」が記事以外のファイルにあります({why})",
                          "       …" + " ".join(around.split()) + "…\n"
                          "       道具が書き出すファイルも公開されます")
                break


def scan_commit_messages(messages, rep):
    """コミットメッセージの文面に、個人が特定できる語が無いか。

    gitと切り離してあるのは、--selftest で本当に反応するか確かめるため。
    messages は (見出し, 本文) の並び。
    """
    if not BANNED:
        return
    for label, msg in messages:
        for pattern, why in BANNED:
            hit = None
            for m in re.finditer(pattern, msg):
                around = msg[max(0, m.start() - 30): m.end() + 30]
                if any(a in around for a in ALLOW):
                    continue
                hit = (m.group(0), around)
                break
            if hit:
                rep.error(label, "匿名性",
                          f"「{hit[0]}」がコミットメッセージにあります({why})",
                          "       …" + " ".join(hit[1].split()) + "…\n"
                          "       GitHubのコミットログは公開されます。"
                          "pushする前なら git commit --amend で書き直せます")


def check_commit_messages(rep):
    """まだpushしていないコミットのメッセージを見る。

    2026-09-03、記事32本を公開したとき「なぜ1本だけ保留にしたか」を
    コミットメッセージに書き、その説明の中に関所の語をそのまま入れて
    pushした。ファイルの中身(check_repo_anonymity)をいくら見ても、
    コミットメッセージは捕まらない。しかも「匿名性の検査に当たる」と
    併記したため、その語が運営者にとって意味を持つことまで示していた。
    表の中に1行あるより悪い。

    pushしてしまうと履歴を書き換えないと消せないので、まだpushして
    いない分だけをエラーにする。ここで止めれば --amend で直せる。
    """
    import subprocess
    if not BANNED:
        return

    def git(*args):
        return subprocess.run(["git"] + list(args), cwd=str(REPO), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=30)

    try:
        up = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        if up.returncode != 0:
            return                      # 上流ブランチが無いなら何もしない
        log = git("log", up.stdout.strip() + "..HEAD", "--format=%H%x1f%B%x1e")
        if log.returncode != 0:
            return
    except Exception:
        return

    messages = []
    for rec in log.stdout.split("\x1e"):
        rec = rec.strip()
        if not rec:
            continue
        sha, _, msg = rec.partition("\x1f")
        messages.append((f"コミット {sha[:8]} (未push)", msg))
    scan_commit_messages(messages, rep)


def check_registry_orphans(registry, pages, rep):
    """台帳にあるのにファイルが無い / ファイルがあるのに台帳に無い"""
    on_disk = {p.stem for p in pages if page_type(p) == "article"}
    for slug in registry_articles(registry):
        if slug not in on_disk:
            rep.error("assets/js/news-data.js", "台帳",
                      f"台帳にある「{slug}」のHTMLファイルがありません",
                      "       記事一覧からリンク切れになります")


def check_sitemap(pages, sitemap, rep):
    """sitemap.xml に載っていない公開ページがないか"""
    if not sitemap:
        return
    base = "https://ozulifememo.github.io/ozu-life-memo/"
    listed = {u.replace(base, "") for u in sitemap}
    for p in pages:
        r = rel(p)
        if page_type(p) not in ("article", "book", "kenkyu"):
            continue
        if r not in listed and r.replace("index.html", "") not in listed:
            rep.warn(r, "sitemap", "sitemap.xml に登録されていません",
                     "       Googleに見つけてもらえない可能性があります")


# ブラウザに近い名乗り方。官公庁サイトの多くは、素っ気ないUAや HEAD を弾く。
# 実在するのに404・405に見える出典が大量に出たため(2026-09-04)、ここを直した。
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


def fetch_status(url):
    """URLの状態を返す。HEADで断られたらGETで確かめ直す。

    戻り値は HTTPステータス(int)か、接続できなかった理由(str)。
    """
    import urllib.request
    import urllib.error

    def once(method):
        req = urllib.request.Request(url, method=method, headers={
            "User-Agent": BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
            "Accept-Language": "ja,en;q=0.8",
        })
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return res.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:
            return f"接続失敗({type(e).__name__})"

    code = once("HEAD")
    # HEADを実装していないサーバーが多い。4xx/5xxならGETで確かめ直す。
    if not isinstance(code, int) or code >= 400:
        code2 = once("GET")
        if isinstance(code2, int) and code2 < 400:
            return code2
        code = code2 if isinstance(code2, int) else code
    return code


def check_urls(pages, rep, limit=None):
    """出典URLが生きているか実際に確認する(--urls のときだけ)"""
    import urllib.request
    import urllib.error

    urls = defaultdict(list)
    for p in pages:
        html = read(p)
        for url in source_urls(p, html):
            urls[url].append(rel(p))

    items = sorted(urls.items())
    if limit:
        items = items[:limit]

    print(f"\n  出典URL {len(items)}件の疎通を確認します(1件ずつ、少し時間がかかります)")
    dead = 0
    for i, (url, where) in enumerate(items, 1):
        if i % 20 == 0:
            print(f"    {i}/{len(items)} 件...")
        code = fetch_status(url)

        # 404/410 だけが「本当に消えた」。403・405・429・202 は
        # 相手がボット避けで返しているだけのことが多く、ブラウザでは開ける。
        # ここでエラーにすると、生きている出典を消す圧力になるので警告に留める。
        if code in (404, 410):
            dead += 1
            for w in where:
                rep.error(w, "リンク", f"出典URLが {code} を返します", f"       {url}")
        elif isinstance(code, int) and code >= 400:
            for w in where:
                rep.warn(w, "リンク", f"出典URLが {code} を返しました(ブラウザでは開けることが多い)",
                         f"       {url}")
        elif not isinstance(code, int):
            for w in where:
                rep.warn(w, "リンク", f"出典URLに接続できませんでした", f"       {url} / {code}")
        time.sleep(0.4)   # レート制限を避ける
    print(f"    完了。生きていないURL: {dead}件")


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------

def print_report(rep, pages, registry, elapsed):
    line = "=" * 68
    print()
    print(line)
    print(" OZU LIFE MEMO サイト点検")
    print(f" {datetime.now():%Y-%m-%d %H:%M}  /  対象 {len(pages)}ページ・記事{len(registry_articles(registry))}本"
          f"  /  {elapsed:.1f}秒")
    print(line)

    # 種類ごとの集計
    by_kind = defaultdict(lambda: [0, 0])
    for e in rep.errors:
        by_kind[e["kind"]][0] += 1
    for w in rep.warns:
        by_kind[w["kind"]][1] += 1

    order = ["構造", "タグ", "表", "タイトル", "メタ", "日付", "台帳", "アンカー", "匿名性",
             "文字化け", "誤字", "出典", "画像", "リンク", "スタイル", "文体", "文章", "見出し", "sitemap"]
    print()
    for kind in order:
        if kind not in by_kind and kind not in ("構造", "タイトル", "匿名性", "文字化け", "出典"):
            continue
        err, warn = by_kind.get(kind, (0, 0))
        if err:
            mark = f"エラー {err}件"
        elif warn:
            mark = f"警告 {warn}件"
        else:
            mark = "OK"
        dots = "." * max(2, 26 - len(kind) * 2)
        print(f"  【{kind}】{dots} {mark}")

    def dump(items, title, mark):
        if not items:
            return
        print()
        print("-" * 68)
        print(f" {mark} {title} ({len(items)}件)")
        print("-" * 68)
        grouped = defaultdict(list)
        for it in items:
            grouped[it["path"]].append(it)
        for path in sorted(grouped):
            print(f"\n{path}")
            for it in grouped[path]:
                print(f"  [{it['kind']}] {it['message']}")
                if it.get("detail"):
                    print(it["detail"])

    dump(rep.errors, "直した方がよいもの", "[NG]")
    dump(rep.warns, "見て判断するもの", "[! ]")

    print()
    print(line)
    if not rep.errors and not rep.warns:
        print(" 結果: 問題なし。きれいな状態です。")
    else:
        print(f" 結果: エラー {len(rep.errors)}件 / 警告 {len(rep.warns)}件")
        if not rep.errors:
            print("       エラーはゼロです。警告は直さなくても壊れません。")
    print(line)
    print()


# ---------------------------------------------------------------------------
# 自己診断(この点検スクリプト自体が壊れていないか確かめる)
# ---------------------------------------------------------------------------

BROKEN_SAMPLE = """<!DOCTYPE html>
<html lang="ja"><head>
<title>基本計画策定のタイトル ｜ OZU LIFE MEMO</title>
<link rel="canonical" href="x">
<meta property="og:title" content="基本計画策定のタイトル ｜ OZU LIFE MEMO">
<script type="application/ld+json">{"headline":"基本計画策定のタイトル","datePublished":"2000-01-01"}</script>
</head><body>
<div data-site-header data-prefix="../"></div>
<h1>基本計画策定のタイトル</h1>
<div class="content-block">
  <a class="source-link" href="https://news.yahoo.co.jp/articles/xxxx" target="_blank">消えやすい出典</a>
</div>
<p>この記事にはダミー禁止語が入っています。文字化けもあります: �</p>
<p>予讃線の電車のことを、大洲に住んでいる人にも知ってほしい。</p>
<p>肘川という誤字と、かぎかっこの開きだけ「ここに置く。ダミーの句点。。</p>
<p><a href="#sonzai-shinai-id">行き先の無いページ内リンク</a></p>
<p><a href="https://drive.google.com/file/d/xxxx" target="_blank">個人ストレージへのリンク</a></p>
<p><img src="../assets/img/この画像はない.jpg" alt="壊れた画像"> <img src="../assets/img/altnashi.png"></p>
<p><a href="../eachnews/このページはない.html">壊れたリンク</a></p>
<p>そしてこの一文は、読点でつなぎ続けることで、どこまでも長くなり、主語も述語も遠く離れ、読んでいる途中で何の話だったのか分からなくなり、それでもまだ終わらず、さらに例を並べ、括弧を挟み、注釈を足し、結局のところ二百字を超えてしまい、読み手はもう一度先頭に戻らなければならず、それでも意味が取れないまま次の段落へ進むことになる、そういう悪い見本として置いてある、とても長い一文である。</p>
<table><tr><td>スクロール用の囲いが無い表</td></tr></table>
<div class="article-table-wrap"><table>
<tr><th>地点</th><th>1996</th><th>2025</th></tr>
<tr><td>セルが1つ足りない行</td><td>100</td></tr>
</table></div>
<div>閉じていないdiv
<p class="source-box-posted">この記事をサイトに掲載した日: 2020/01/01</p>
<div data-site-footer="article"></div><div data-site-modal></div>
<script src="../assets/js/site-chrome.js"></script>
<script src="../assets/js/news-data.js"></script>
<script src="../assets/js/main.js"></script>
</body></html>
"""

BROKEN_REGISTRY = """const OZU_TAGS = ["防災", "観光"];
const OZU_NEWS = [
  { slug: "broken", date: "2026-08-19", title: "台帳側のタイトル", category: "ima" },
  { slug: "yukue-fumei", date: "2026-08-19", title: "HTMLが存在しない記事", category: "ima" },
  { slug: "kowareta-daicho", date: "2026-99-99", title: "壊れた行", category: "nazo" },
];
"""

# わざと壊したページから、必ず見つかってほしい項目
EXPECTED = [
    ("構造", "source-box"),
    ("構造", "要点3行"),
    ("構造", "読了時間"),
    ("構造", "photos-data.js"),
    ("構造", "article-related.js"),
    ("構造", "viewport"),
    ("構造", "description"),
    ("構造", "アクセス解析"),
    ("構造", "RSS発見"),
    ("構造", "メモう"),
    ("構造", "あわせて読みたいの置き場"),
    ("タグ", "div"),
    ("表", "囲い"),
    ("表", "セルの数がそろっていない"),
    ("タイトル", "news-data.js"),
    ("メタ", "canonical"),
    ("メタ", "og:title"),
    ("日付", "datePublished"),
    ("日付", "掲載日"),
    ("台帳", "data-slug"),
    ("台帳", "タグがありません"),
    ("台帳", "カテゴリが不正"),
    ("台帳", "日付の形式"),
    ("アンカー", "行き先ID"),
    ("匿名性", "ダミー禁止語"),
    ("匿名性", "コミットメッセージにあります"),
    ("文字化け", "文字化け"),
    ("誤字", "肘川"),
    ("誤字", "かぎかっこ"),
    ("誤字", "句点"),
    ("出典", "1本"),
    ("出典", "news.yahoo.co.jp"),
    ("表現", "知ってほしい"),
    ("文章", "1文が"),
    ("事実", "電車"),
    ("タイトル", "策定"),
    ("画像", "行き先がありません"),
    ("画像", "alt属性"),
    ("リンク", "行き先がありません"),
    ("リンク", "noopener"),
    ("リンク", "ストレージ"),
    ("台帳", "yukue-fumei"),
]


def run_selftest() -> int:
    """わざと壊したページを作って、ちゃんと検知できるか確かめる。

    「点検してOKだった」が信用できるのは、この自己診断が通るときだけです。
    サイトの作りを変えたあとは、これを走らせて点検器が生きているか確認してください。
    """
    global REPO
    import tempfile

    print("\n  自己診断: わざと壊したページを作って、検知できるか試します...")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "eachnews").mkdir(parents=True)
        (root / "assets" / "js").mkdir(parents=True)
        (root / "eachnews" / "broken.html").write_text(BROKEN_SAMPLE, encoding="utf-8")
        (root / "assets" / "js" / "news-data.js").write_text(BROKEN_REGISTRY, encoding="utf-8")

        real_repo = REPO
        REPO = root
        # ALLOW(見逃してよい文字列)には自己テスト用のダミー語そのものが入っている
        # (check_site.py 自身を check_repo_anonymity が読むため)。そのままだと
        # 匿名性の検査が自己診断で反応せず、「見ているつもりで見ていない」状態に
        # なる。自己診断のあいだだけ外す。
        _allow_backup = ALLOW[:]
        ALLOW.clear()
        try:
            pages = collect_pages()
            registry = load_registry()
            id_map = collect_ids(pages)
            rep = Report()
            for p in pages:
                html = read(p)
                check_structure(p, html, rep)
                check_tag_balance(p, html, rep)
                check_tables(p, html, rep)
                check_titles(p, html, registry, rep)
                check_head_meta(p, html, registry, rep)
                check_link_hygiene(p, html, rep)
                check_typos(p, html, rep)
                check_fragments(p, html, id_map, rep)
                check_article_registry_sync(p, html, registry, rep)
                check_relative_dates(p, html, registry, rep)
                check_kenkyu_extra(p, html, rep)
                check_anonymity(p, html, rep)
                check_mojibake(p, html, rep)
                check_style(p, html, rep)
                check_phrasing(p, html, rep)
                check_links(p, html, rep)
                check_title_numbers(p, html, rep)
                check_sources(p, html, rep)
            check_registry_orphans(registry, pages, rep)
            check_registry_file(registry, rep)
            # コミットメッセージの検査(gitを叩かずに、文面だけ渡して確かめる)
            scan_commit_messages(
                [("コミット selftest", "ダミー禁止語をコミットメッセージに書いてしまった例")], rep)
        finally:
            REPO = real_repo
            ALLOW[:] = _allow_backup

    # ── 部品の自己診断 ────────────────────────────────
    # 「違反を検知するか」とは別に、「正しいものを正しく扱えるか」も見る。
    # 2026-09-04、出典URLの &amp; を & に戻さないまま叩いていたせいで、
    # 生きている出典10本が404に見えていた。検知する側が静かに間違うと、
    # 点検は通っているのに結果が嘘になる。ここで毎回それを潰す。
    parts_ng = []
    probe = ('<main><a class="source-link" '
             'href="https://example.com/x?a=1&amp;b=2" '
             'target="_blank" rel="noopener">出典</a></main>')
    got = source_urls(REPO / "eachnews" / "probe.html", probe)
    if got != ["https://example.com/x?a=1&b=2"]:
        parts_ng.append("出典URLの取り出し: &amp; を & に戻せていない -> %r" % (got,))
    print("    [%s] 部品: 出典URLの &amp; を戻す" % ("OK " if not parts_ng else "NG "))
    if parts_ng:
        print()
        print("  自己診断に失敗しました。部品が正しく動いていません。")
        for why in parts_ng:
            print("    " + why)
        print("  点検スクリプトが壊れている可能性があります。OKという結果を信用しないでください。")
        return 1

    found = rep.errors + rep.warns
    missed = []
    for kind, needle in EXPECTED:
        hit = any(f["kind"] == kind and (needle in f["message"] or needle in (f.get("detail") or ""))
                  for f in found)
        mark = "OK " if hit else "NG "
        print(f"    [{mark}] {kind}: {needle}")
        if not hit:
            missed.append((kind, needle))

    print()
    if missed:
        print(f"  自己診断に失敗しました。{len(missed)}項目が検知できていません。")
        print("  点検スクリプトが壊れている可能性があります。OKという結果を信用しないでください。")
        return 1
    print(f"  自己診断OK。{len(EXPECTED)}項目すべて検知できました。点検結果は信用して大丈夫です。\n")
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="OZU LIFE MEMO サイト点検スクリプト")
    ap.add_argument("--urls", action="store_true", help="出典URLの疎通も確認する(時間がかかる)")
    ap.add_argument("--url-limit", type=int, default=None, help="確認するURLの数を制限する")
    ap.add_argument("--slug", help="この記事だけ点検する(例: --slug ozu-mirai-note)")
    ap.add_argument("--headings", action="store_true",
                    help="疑問形の見出しを一覧にする(答えが書けているか目視するとき用)")
    ap.add_argument("--changed", action="store_true",
                    help="gitで変更のあったページだけ点検する(フックが使う)")
    ap.add_argument("--promises", action="store_true",
                    help="「あとで追記したい」系の約束を一覧にする(月次巡視用)")
    ap.add_argument("--json", metavar="FILE", help="結果をJSONファイルに保存する")
    ap.add_argument("--selftest", action="store_true",
                    help="点検スクリプト自体が正しく動くか自己診断する")
    args = ap.parse_args()

    if args.selftest:
        return run_selftest()

    started = time.time()

    all_pages = collect_pages()
    pages = list(all_pages)
    registry = load_registry()
    sitemap = load_sitemap()

    if args.promises:
        list_promises(pages)
        return 0

    if args.slug:
        pages = [p for p in pages if p.stem == args.slug]
        if not pages:
            print(f"「{args.slug}」というページが見つかりませんでした。")
            return 1

    changed_files = set()
    if args.changed:
        changed_files = git_changed_files()
        changed = {p for p in changed_files if p.endswith(".html")}
        pages = [p for p in pages if rel(p) in changed]
        touched_shared = changed_files & {"assets/js/news-data.js", "sitemap.xml", "feed.xml"}
        if not pages and not touched_shared:
            print("\n  いま手を入れたページはありません。点検をとばします。\n")
            return 0

    # ページ内リンクの行き先は、点検対象外のページにもあるので全ページから集める
    id_map = collect_ids(all_pages)

    rep = Report()

    for p in pages:
        html = read(p)
        check_structure(p, html, rep)
        check_tag_balance(p, html, rep)
        check_tables(p, html, rep)
        check_titles(p, html, registry, rep)
        check_head_meta(p, html, registry, rep)
        check_link_hygiene(p, html, rep)
        check_typos(p, html, rep)
        check_fragments(p, html, id_map, rep)
        check_article_registry_sync(p, html, registry, rep)
        check_relative_dates(p, html, registry, rep)
        check_kenkyu_extra(p, html, rep)
        check_anonymity(p, html, rep)
        check_mojibake(p, html, rep)
        check_style(p, html, rep, show_headings=args.headings)
        check_phrasing(p, html, rep)
        check_links(p, html, rep)
        check_title_numbers(p, html, rep)
        check_sources(p, html, rep)

    if not args.slug and not args.changed:
        check_registry_orphans(registry, all_pages, rep)
        check_repo_anonymity(rep)
        check_commit_messages(rep)
        check_registry_file(registry, rep)
        check_feed(registry, rep)
        check_sitemap_targets(sitemap, rep)
    if args.changed:
        # 台帳・sitemap・RSSに手が入っているときは、その整合も見る(公開作業の消し忘れ対策)
        if "assets/js/news-data.js" in changed_files:
            check_registry_orphans(registry, all_pages, rep)
            check_registry_file(registry, rep)
            check_feed(registry, rep)
        if "sitemap.xml" in changed_files:
            check_sitemap_targets(sitemap, rep)
        if "feed.xml" in changed_files:
            check_feed(registry, rep)
    if not args.slug:
        check_sitemap(pages, sitemap, rep)

    if args.urls:
        check_urls(pages, rep, args.url_limit)

    elapsed = time.time() - started
    print_report(rep, pages, registry, elapsed)

    if args.json:
        # Notionとの突き合わせに使えるように、記事の中身の要約も一緒に出す
        articles = {}
        for p in pages:
            if page_type(p) != "article":
                continue
            html = read(p)
            body = body_only(html)
            articles[p.stem] = {
                "path": rel(p),
                "title": (re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S) or [None, ""])[1].strip(),
                "h2": [re.sub(r"<[^>]+>", "", h).strip()
                       for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)],
                "strong_count": len(re.findall(r"<strong\b", body)),
                "sources": re.findall(r'class="source-link"\s+href="([^"]+)"', body),
            }
        out = {
            "generated": datetime.now().isoformat(timespec="seconds"),
            "pages_checked": len(pages),
            "errors": rep.errors,
            "warnings": rep.warns,
            "articles": articles,
        }
        Path(args.json).write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSONを保存しました: {args.json}\n")

    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
