# -*- coding: utf-8 -*-
"""記事の数字が、その記事自身の出典に本当に載っているかを機械で照合する。

過去に「出典PDFに存在しない数字を書いていた」事故があった。
人が目で確かめるには数字が多すぎるので、機械で候補を絞る。

やっていること:
  1. 記事本文から数字を抜く(図・出典欄・日付は除く)
  2. その記事の出典URL/PDFを実際に取ってきて、文章にする
  3. その数字が出典の文章の中に現れるかを照合する
  4. どの出典にも見つからなかった数字だけを出す

**見つからない=間違い、ではない。** 自分で計算して出した数字(割合・増減率)や、
表を読んで言い換えた数字は当然ヒットしない。これは「人が見るべき数字」を
数百個から数個に絞るための道具であって、正誤の判定器ではない。

**この道具を「出典に無い数字を消す」ために使ってはいけない。**
2026-08-29の実測では、記事が自分で計算して出した数字が150個あった。
「補助金を引くと実質910万円」「V < 1.875B まで広がる」「住民基本台帳から
独自に集計した数と1人の狂いもなく一致」——こういう数字がこのサイトの
価値そのものであって、出典の要約なら誰でも書ける。照合できないことを
理由にそれを削れば、残るのは一般的なことしか言わない当たり障りのない
記事になる。検査は下限であって、目標ではない。

逆に「数字はあるが意味が違う」(人口の28%減を世帯数の28%と取り違える等)は
この道具では絶対に見抜けない。そこは人が読むしかない。

使い方:
  python tools/check_numbers.py --limit 12        # まず少数で試す
  python tools/check_numbers.py --slug ozu-shakyo-kessan
  python tools/check_numbers.py                   # 全記事(時間がかかる)
  python tools/check_numbers.py --json out.json
"""
import argparse
import hashlib
from datetime import date
import html as html_mod
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_site as cs                                    # noqa: E402

CACHE = Path(__file__).resolve().parent / "_source_cache"
# 出典1本ごとの「取ってきたときの中身」を控えておく台帳。
# 中身そのものはキャッシュ(非公開)、ここに残すのはハッシュと文字数だけ
INDEX = Path(__file__).resolve().parent / "source-index.json"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*",
    "Accept-Language": "ja,en;q=0.8",
}
DELAY = 1.0          # 同じサーバーを叩き続けないための間隔(秒)
# 取ってきた本文がこの文字数に満たない出典は「薄い」とみなす。
# JavaScriptで中身を描くページは、取ってもメニューしか手に入らない。
# そういう出典しか無い記事は「照合できなかった」であって「疑わしい」ではない。
THIN = 3000
TIMEOUT = 30

# 本文から数字を拾うときに、単位が付いていれば2桁でも拾う
UNITS = "％%割円人件戸棟世帯歳年月日回台校館所km㎞ｍm㎡億万千百年度倍点位"

# 中身の無いページ(動画・地図など)。取りに行っても文章が無いので数えない
NO_TEXT_HOSTS = ("youtube.com", "youtu.be", "google.com/maps", "twitter.com", "x.com")


# ---------------------------------------------------------------------------
# 文字の正規化
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """全角を半角にし、桁区切りと空白を落として、数字を比べられる形にする"""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(",", "").replace("，", "")
    # 縦書きの資料は「一、五九四、二七六」と読点を桁区切りに使う。
    # 数字にはさまれた読点だけを落とす(文の区切りの読点は残す)。
    # 2026-09-06、大洲城天守復元事業報告書で見つけた。
    text = re.sub(r"(?<=[0-9])、(?=[0-9])", "", text)
    text = re.sub(r"[\s　]+", "", text)
    return text


# 記事の中で計算した数字だと分かる印。この印が near にあれば、出典に
# 同じ字面が無くて当たり前(検算の途中式など)
CALC_MARKS = ("÷", "×", "=", "≈", "≒", "検算", "割ると", "掛ける", "合わせて",
              "足すと", "増は", "合計", "あたり", "1人", "内訳", "差額", "引くと",
              "換算", "計算", "ずつ")


# ---------------------------------------------------------------------------
# 漢数字
# ---------------------------------------------------------------------------

_KAN_D = {"〇": "0", "零": "0", "一": "1", "二": "2", "三": "3", "四": "4",
          "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
_KAN_UNIT = {"十": 10, "百": 100, "千": 1000}
_KAN_BIG = {"万": 10 ** 4, "億": 10 ** 8, "兆": 10 ** 12}

# 「三十日」のように、後ろに来ると数だと分かる字。
# これを付けないと「十分(=じゅうぶん)」まで 10分 に化けてしまう
_KAN_TAIL = ("億", "万", "円", "人", "名", "件", "戸", "棟", "世帯", "台", "校",
             "所", "年", "月", "日", "回", "倍", "割", "点", "位", "歳", "%",
             "匹", "頭", "本", "冊", "社", "席", "室", "館", "店", "番",
             "パーセント", "ヘクタール", "メートル", "キロ", "ha", "km", "分の")


def _kan_value(s: str) -> int:
    """「三百八十三」「一億二千万」を数に直す"""
    total, section, digit = 0, 0, 0
    for ch in s:
        if ch in _KAN_D:
            digit = digit * 10 + int(_KAN_D[ch])
        elif ch in _KAN_UNIT:
            section += (digit or 1) * _KAN_UNIT[ch]
            digit = 0
        elif ch in _KAN_BIG:
            total += (section + digit) * _KAN_BIG[ch]
            section = digit = 0
    return total + section + digit


def kansuji_to_arabic(text: str) -> str:
    """出典の中の漢数字を算用数字にした写しを作る。

    愛媛県史のような資料は「八四五名」「三〇九億円」と縦書き用の漢数字で
    書かれている。記事は算用数字で書くので、字面が合わず「出典に無い」と
    出てしまう(2026-09-05、松下寿の記事で実際に3個そう出た。目で見ると
    ちゃんと載っていた)。人が毎回確かめ直すのは無駄なので機械に持たせる。

    安全側に倒してある。裸の「一」「三」は数に直さない(「一部」「三つ」を
    壊さないため)。位取りのある形と1文字の形は、後ろに単位が来ている
    ときだけ直す(「十分」を 10分 にしないため)。
    """
    tail = "|".join(re.escape(t) for t in _KAN_TAIL)
    D = "〇零一二三四五六七八九"

    # 0. 「一、五九四、二七六、四九六円」のように、漢数字を読点で3桁ずつ
    #    区切った縦書きの書き方。先に読点を外して1つの塊にする。
    #    3桁ずつの区切りに限っているので、「一、二の順に」のような
    #    ただの並列は壊れない。2026-09-06に足した。
    text = re.sub(
        r"(?<![" + D + r"])([" + D + r"]{1,3})((?:、[" + D + r"]{3})+)"
        r"(?=" + tail + ")",
        lambda m: m.group(1) + m.group(2).replace("、", ""),
        text)

    # 1. 小数「九五・四%」。中黒が小数点として使われている形
    def _dec(m):
        a = "".join(_KAN_D[c] for c in m.group(1))
        b = "".join(_KAN_D[c] for c in m.group(2))
        return a + "." + b

    text = re.sub(r"([" + D + r"]{2,})・([" + D + r"]+)", _dec, text)
    text = re.sub(r"([" + D + r"])・([" + D + r"]+)(?=" + tail + ")", _dec, text)

    # 2. 「八四五」のように漢数字が2つ以上並んだもの(位取りなし)
    text = re.sub(r"[" + D + r"]{2,}",
                  lambda m: "".join(_KAN_D[c] for c in m.group()), text)

    # 3. 「三百八十三匹」「七月」のように、後ろの単位で数だと分かる形
    pat = re.compile(r"[" + D + r"十百千万億兆]+(?=" + tail + ")")

    def _mix(m):
        w = m.group()
        v = _kan_value(w)
        return str(v) if v or w in ("〇", "零") else w

    return pat.sub(_mix, text)


def variants(digits: str) -> set:
    """同じ量の別の書き方を作る。

    出典が「1,372ヘクタール」、記事が「13.72平方キロメートル」のように、
    数字は合っているのに単位が違って字面が一致しないことがある。
    桁をずらした形と、丸めた形を候補に加える。
    """
    out = {digits}
    try:
        v = float(digits)
    except ValueError:
        return out

    # 末尾の .0 を落とす / 整数なら小数点付きも試す
    if digits.endswith(".0"):
        out.add(digits[:-2])
    if "." not in digits:
        out.add(digits + ".0")

    # 桁をずらす(ヘクタール↔平方キロ、万円↔円、億↔万 など)
    for k in (100, 10000, 1000000, 100000000, 0.01, 0.0001, 0.000001, 0.00000001):
        w = v * k
        if w >= 1 and abs(w - round(w)) < 1e-6:
            out.add(str(int(round(w))))

    # 丸めた形(出典が小数1桁、記事が2桁など)
    if "." in digits:
        for nd in (0, 1, 2):
            out.add(f"{v:.{nd}f}".rstrip(".") if nd == 0 else f"{v:.{nd}f}")

    # 「4万5585」のような漢字混じりの書き方
    if v >= 10000 and float(int(v)) == v:
        n = int(v)
        if n < 100000000:
            man, rest = divmod(n, 10000)
            if rest:
                out.add(f"{man}万{rest}")
            else:
                out.add(f"{man}万")

    return {x for x in out if x and len(x.lstrip("0.")) >= 2}


# ---------------------------------------------------------------------------
# 記事から数字を抜く
# ---------------------------------------------------------------------------

def article_numbers(html: str) -> list:
    """記事本文の数字を、前後の文脈つきで返す"""
    body = cs.body_only(html)

    # 図(SVG)の中は座標だらけなので丸ごと落とす
    body = re.sub(r"<svg\b.*?</svg>", " ", body, flags=re.S | re.I)
    # 出典欄そのものは照合の対象外(出典タイトルに年号が入る)
    body = re.sub(r'<div class="content-block source-box".*?</div>\s*</div>', " ",
                  body, flags=re.S)
    body = re.sub(r"<time\b.*?</time>", " ", body, flags=re.S | re.I)
    # 掲載日の行は照合の対象外。2026-09-06、book(大洲と読書)の19本で
    # 「2026」が毎回ひっかかっていた
    body = re.sub(r'<p class="article-date".*?</p>', " ", body, flags=re.S)
    # 要点ボックスは本文の要約なので、本文側で照合すれば足りる
    body = re.sub(r'<div class="article-summary".*?</div>', " ", body, flags=re.S)

    text = cs.strip_tags(body)
    text = unicodedata.normalize("NFKC", text)

    found = []
    seen = set()
    for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", text):
        raw = m.group(0)
        digits = raw.replace(",", "")
        after = text[m.end(): m.end() + 3]
        before = text[max(0, m.start() - 6): m.start()]

        # 西暦・和暦の年は、ほぼ必ず出典に出るので照合しても意味が薄い
        if re.match(r"^(19|20)\d\d$", digits) and after.startswith("年"):
            continue
        if re.search(r"(昭和|平成|令和|第)$", before):
            continue
        # 「約1,930万円」のように丸めた数字は、出典に同じ字面では出ない。
        # 一致しなくて当然なので照合しない(これを入れる前は誤検知の大半がこれだった)
        if re.search(r"(約|およそ|おおよそ|ほぼ|前後|超|弱|強)$", before):
            continue

        # アカウント名や資料番号の一部(@AyuDokka49543、D1-No.920、総参―786)は
        # 数量ではないので照合しない
        if re.search(r"[A-Za-z@_―—\-]$", before) and not before.endswith(" "):
            continue
        if re.search(r"(No\.?|第|番号|規則|条|項)\s*$", before):
            continue
        # 住所の番地
        if text[m.end(): m.end() + 2] in ("番地", "丁目") or \
           text[m.end(): m.end() + 1] == "番":
            continue

        # 電話番号(24-0530)・郵便番号・ページ範囲など、ハイフンで数字が
        # つながっているものは出典に同じ字面で出ないことが多い。照合しない
        prev_ch = text[m.start() - 1] if m.start() else ""
        next_ch = text[m.end()] if m.end() < len(text) else ""
        if (prev_ch == "-" and text[max(0, m.start() - 2): m.start() - 1].isdigit()) or \
           (next_ch == "-" and text[m.end() + 1: m.end() + 2].isdigit()):
            continue

        # 「▲8.3%」「+40.6%」のような増減率は、記事側で計算して出した数字。
        # 出典の表には元の実数しか載っていないので照合しても意味がない
        if prev_ch in "▲△+＋-−±" and next_ch in "%％":
            continue

        # 3桁以上、小数、または単位つきのものだけを見る
        has_unit = bool(after) and after[0] in UNITS
        if len(digits.lstrip("0")) < 3 and "." not in digits and not has_unit:
            continue

        key = digits + (after[0] if has_unit else "")
        if key in seen:
            continue
        seen.add(key)

        found.append({
            "raw": raw + (after[0] if has_unit else ""),
            "digits": digits,
            "context": " ".join(text[max(0, m.start() - 30): m.end() + 20].split()),
        })
    return found


# ---------------------------------------------------------------------------
# 出典を取ってきて文章にする
# ---------------------------------------------------------------------------

def cache_path(url: str) -> Path:
    return CACHE / (hashlib.sha1(url.encode("utf-8")).hexdigest() + ".txt")


def fetch_source(url: str, session) -> tuple:
    """出典1本を文章にして返す。(本文, 取得できたか, 理由)

    HTMLの href では & を &amp; と書くのが正しいので、取りに行く前に戻す。
    これを忘れて気象庁のデータページを取り損ね、実際に1記事で77個の
    数字が「見つからない」と誤判定された(2026-08-29に修正)。
    """
    url = html_mod.unescape(url)
    if any(h in url for h in NO_TEXT_HOSTS):
        return "", False, "文章のないページ(動画・地図など)"

    cached = cache_path(url)
    if cached.exists():
        return cached.read_text(encoding="utf-8"), True, "キャッシュ"

    CACHE.mkdir(exist_ok=True)
    try:
        time.sleep(DELAY)
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code != 200:
            return "", False, f"HTTP {r.status_code}"
        body = r.content
        ctype = r.headers.get("Content-Type", "")
    except Exception as e:
        return "", False, f"取得できず({e.__class__.__name__})"

    if url.lower().endswith(".pdf") or "pdf" in ctype.lower():
        try:
            import fitz
            with fitz.open(stream=body, filetype="pdf") as doc:
                text = "\n".join(page.get_text() for page in doc)
        except Exception as e:
            return "", False, f"PDFを読めず({e.__class__.__name__})"
    else:
        # 大洲市サイトは Content-Type に charset を付けないので、requests は
        # ISO-8859-1 と決めつける。そのまま decode すると日本語が全部化けて、
        # 全角数字や「億・万」の桁区切りが照合できなくなる(2026-08-30に発見。
        # 会議録に載っている 14,948人 が「出典に無い」と誤判定されていた)。
        # meta charset を優先し、無ければ中身から推定する。
        enc = r.encoding
        m = re.search(rb"charset=[\"']?([\w-]+)", body[:4096], re.I)
        if m:
            enc = m.group(1).decode("ascii", "ignore")
        elif not enc or enc.lower() in ("iso-8859-1", "latin-1", "ascii"):
            enc = r.apparent_encoding or "utf-8"
        try:
            html = body.decode(enc, errors="replace")
        except Exception:
            html = body.decode("utf-8", errors="replace")
        html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
        text = cs.strip_tags(html)

    text = normalize(text)
    cached.write_text(text, encoding="utf-8")
    return text, True, "取得"


def all_source_urls() -> dict:
    """サイト全体の出典URLと、それを引いている記事の一覧"""
    used = {}
    for p in cs.collect_pages():
        if cs.page_type(p) not in ("article", "kenkyu", "book"):
            continue
        html = cs.read(p)
        for u in cs.source_urls(p, html):
            used.setdefault(html_mod.unescape(u), []).append(cs.rel(p))
    return used


def build_index() -> int:
    """いまキャッシュにある出典の中身を、台帳に控える"""
    used = all_source_urls()
    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    n = 0
    for url in used:
        c = cache_path(url)
        if not c.exists():
            continue
        text = c.read_text(encoding="utf-8")
        index[url] = {
            "hash": hashlib.sha1(text.encode("utf-8")).hexdigest()[:12],
            "chars": len(text),
            "checked": date.today().isoformat(),
        }
        n += 1
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8")
    print(f"\n  出典 {n}本の中身を tools/source-index.json に控えました\n")
    return 0


def watch_sources(limit=None) -> int:
    """出典を取り直して、前と中身が変わっていないかを見る"""
    import requests
    if not INDEX.exists():
        print("  先に --index で出典の中身を控えてください")
        return 1
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    used = all_source_urls()
    targets = [u for u in used if u in index]
    if limit:
        targets = targets[:limit]

    print(f"\n  出典 {len(targets)}本を取り直して、中身が変わっていないか見ます\n")
    session = requests.Session()
    changed, gone, same = [], [], 0
    for i, url in enumerate(targets, 1):
        cache_path(url).unlink(missing_ok=True)      # 取り直すのでキャッシュを外す
        text, ok, why = fetch_source(url, session)
        if not ok:
            gone.append((url, why))
            continue
        h = hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]
        before = index[url]
        if h != before["hash"]:
            changed.append((url, before, len(text)))
        else:
            same += 1
        index[url] = {"hash": h, "chars": len(text), "checked": date.today().isoformat()}
        if i % 25 == 0:
            print(f"    {i}/{len(targets)} 本...")

    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                     encoding="utf-8")

    print(f"\n  変わっていない {same}本 / 変わった {len(changed)}本 / 取れなかった {len(gone)}本\n")
    for url, before, now in changed:
        print(f"  ● 中身が変わった出典 ({before['chars']}字 → {now}字、前回 {before['checked']})")
        print(f"    {url}")
        for a in used[url]:
            print(f"      引いている記事: {a}")
        print()
    for url, why in gone[:20]:
        print(f"  × 取れなくなった出典 ({why}) {url}")
        for a in used[url]:
            print(f"      引いている記事: {a}")
    print()
    print("  中身が変わっていても、記事が引いた数字が変わったとは限りません。")
    print("  更新日の追記だけのこともあります。記事の数字を確かめ直してください。")
    print("  そのうえで python tools/check_numbers.py を走らせると答え合わせになります。\n")
    return 0


def render_thin_sources(limit=None, slug=None):
    """本文が薄い出典を、ブラウザで開き直して取り込む

    JavaScriptで中身を描くページは、ふつうに取ると器だけが返ってくる。
    その出典で裏付けている数字が全部「出典に見つからない」と出てしまう。
    --slug を付けると、その記事の出典だけを取り直す(全部やると729本あって
    時間もかかるし、よそのサーバーに負担をかけるため)。
    """
    from playwright.sync_api import sync_playwright

    targets = []
    for p in cs.collect_pages():
        if cs.page_type(p) not in ("article", "kenkyu", "book"):
            continue
        if slug and p.stem != slug:
            continue
        html = cs.read(p)
        for u in cs.source_urls(p, html):
            if any(h in u for h in NO_TEXT_HOSTS) or u.lower().endswith(".pdf"):
                continue
            c = cache_path(html_mod.unescape(u))
            n = len(c.read_text(encoding="utf-8")) if c.exists() else 0
            if n < THIN:
                targets.append((html_mod.unescape(u), n))
    targets = sorted(dict(targets).items(), key=lambda kv: kv[1])
    if limit:
        targets = targets[:limit]

    print(f"\n  本文が薄い出典 {len(targets)}本を、ブラウザで開き直します")
    print("  (JavaScriptで中身を描くページを取るため。1本ずつなので時間がかかります)\n")

    better = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(user_agent=HEADERS["User-Agent"],
                                locale="ja-JP", viewport={"width": 1280, "height": 900})
        for i, (url, before) in enumerate(targets, 1):
            try:
                page.goto(url, timeout=40000, wait_until="networkidle")
                text = normalize(page.inner_text("body"))
            except Exception as e:
                print(f"    [{i}/{len(targets)}] 開けず({e.__class__.__name__}) {url[:70]}")
                continue
            if len(text) > before:
                cache_path(url).write_text(text, encoding="utf-8")
                better += 1
                mark = "◎" if len(text) >= THIN else "△"
                print(f"    [{i}/{len(targets)}] {mark} {before}字 → {len(text)}字  {url[:66]}")
            else:
                print(f"    [{i}/{len(targets)}] - 変わらず({before}字) {url[:66]}")
            time.sleep(DELAY)
        browser.close()
    print(f"\n  {better}本の出典で、本文が取れるようになりました\n")
    return 0


# ---------------------------------------------------------------------------
# 本体
# ---------------------------------------------------------------------------

def check_article(path, session, verbose=True):
    html = cs.read(path)
    # 出典の取り出し方はページ種別で違う(自由研究は source-link を使わない)。
    # check_site.py に寄せて、片方だけ直る事故を防ぐ
    urls = cs.source_urls(path, html)
    numbers = article_numbers(html)

    pool, fetched, failed, thin = [], 0, [], []
    for u in urls:
        text, ok, why = fetch_source(u, session)
        if ok:
            pool.append(text)
            fetched += 1
            if len(text) < THIN:
                thin.append((u, len(text)))
        else:
            failed.append((u, why))
    haystack = "".join(pool)
    # 中身のある出典が1本も無ければ、この記事の照合結果は信用できない
    substantial = fetched - len(thin)

    missing, calculated, other_form = [], [], []
    kan = None   # 漢数字を直した写し。使う記事だけで作る(全部作ると遅い)
    for n in numbers:
        if not haystack:
            break
        if n["digits"] in haystack:
            continue
        # 記事の中で計算して出した数字か
        if any(mk in n["context"] for mk in CALC_MARKS):
            calculated.append(n)
            continue
        # 単位違い・丸め違いで、同じ量が別の字面で載っていないか
        hit = next((v for v in variants(n["digits"]) if v in haystack), None)
        if hit:
            n["as"] = hit
            other_form.append(n)
            continue
        # 出典が漢数字で書いている場合(愛媛県史など)。要るときだけ作る
        if kan is None:
            kan = kansuji_to_arabic(haystack)
        hit = next((v for v in variants(n["digits"]) | {n["digits"]}
                    if v in kan), None)
        if hit:
            n["as"] = hit + "(出典は漢数字)"
            other_form.append(n)
            continue
        missing.append(n)

    return {
        "path": cs.rel(path),
        "sources": len(urls),
        "fetched": fetched,
        "failed": failed,
        "thin": thin,
        "numbers": len(numbers),
        "missing": missing,
        "calculated": calculated,      # 記事の中で計算した数字
        "other_form": other_form,      # 単位違いなど別の字面で出典にあった
        "no_source_text": not haystack,
        # 中身のある出典が無い = 判定できない(疑わしい、ではない)
        "inconclusive": substantial == 0,
    }


# ---------------------------------------------------------------------------
# 自己診断
# ---------------------------------------------------------------------------

# 左が出典に書かれている形、右が直ったあとに含まれていてほしい字面。
# 右が None のものは「直してはいけない」= そのまま残っていてほしいもの。
# 直しすぎると、出典に無い数字まで「載っている」ことになってしまう。
# それは見落としを生むので、直さない側のほうが大事。
EXPECTED_KAN = [
    ("八四五名が働いていた",        "845名"),
    ("三〇九億円のうち三〇四億円",  "309億円"),
    ("九五・四%",                   "95.4%"),
    ("三百八十三匹が幼齢個体",      "383匹"),
    ("約二万三千人",                "23000"),
    ("平成三十年七月豪雨",          "30年7月"),
    ("千人あたり二七・六人",        "27.6人"),
    # 読点を桁区切りに使う縦書きの書き方(2026-09-06、大洲城の報告書で見つけた)
    ("合計一、五九四、二七六、四九六円", "1594276496円"),
    ("寄付金四四六、五〇〇、〇一五円",   "446500015円"),
    # ここから下は直してはいけないもの
    ("十分に注意してほしい",        None),
    ("一部の地域では",              None),
    ("三つの案が出た",              None),
    ("四国の中で",                  None),
    ("大洲・内子・長浜",            None),
    ("一方で",                      None),
    ("一、二の順に並べる",           None),
]


def selftest() -> int:
    print("\n  自己診断: 漢数字の直し方が壊れていないか試します...\n")
    ok = True
    for src, want in EXPECTED_KAN:
        got = kansuji_to_arabic(src)
        if want is None:
            good = got == src
            what = "そのまま残す"
        else:
            good = want in got
            what = "→ " + want
        print("    [%s] %-22s %-14s %s" % ("OK " if good else "NG ", src, what,
                                           "" if good else "実際: " + got))
        ok = ok and good
    print()
    if ok:
        print("  自己診断OK。%d件すべて期待どおりです。\n" % len(EXPECTED_KAN))
        return 0
    print("  自己診断に失敗しました。照合結果を信用しないでください。\n")
    return 1


def main():
    ap = argparse.ArgumentParser(description="記事の数字が出典に載っているか照合する")
    ap.add_argument("--slug", help="この記事だけ照合する")
    ap.add_argument("--limit", type=int, help="先頭から何本だけ照合するか(試すとき用)")
    ap.add_argument("--json", metavar="FILE", help="結果をJSONで保存する")
    ap.add_argument("--render", action="store_true",
                    help="本文が薄い出典を、ブラウザで開き直して取り込む(時間がかかる)")
    ap.add_argument("--index", action="store_true",
                    help="いまの出典の中身を控える(あとで書き換わりを見るため)")
    ap.add_argument("--selftest", action="store_true",
                    help="この道具自体が壊れていないか試す")
    ap.add_argument("--watch", action="store_true",
                    help="出典を取り直して、中身が変わっていないか見る(月次点検用)")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if args.selftest:
        return selftest()
    if args.render:
        return render_thin_sources(args.limit, args.slug)
    if args.index:
        return build_index()
    if args.watch:
        return watch_sources(args.limit)

    import requests
    session = requests.Session()

    # 2026-09-06、book(大洲と読書)が抜けていた。出典を集める側は book を含むのに
    # 本体の照合だけ外れていて、19本が一度も照合されていなかった
    pages = [p for p in cs.collect_pages() if cs.page_type(p) in ("article", "kenkyu", "book")]
    if args.slug:
        pages = [p for p in pages if p.stem == args.slug]
        if not pages:
            print(f"「{args.slug}」が見つかりませんでした")
            return 1
    if args.limit:
        pages = pages[:args.limit]

    print(f"\n  {len(pages)}本の記事を、出典と照合します")
    print("  (出典は初回だけ取りに行き、tools/_source_cache/ に貯めます)\n")

    results = []
    t0 = time.time()
    for i, p in enumerate(pages, 1):
        r = check_article(p, session)
        results.append(r)
        mark = "?" if r["inconclusive"] else ("!" if r["missing"] else " ")
        print(f"  [{mark}] {i:3d}/{len(pages)}  {r['path']:52s} "
              f"数字{r['numbers']:3d} 出典{r['fetched']}/{r['sources']} "
              f"見つからず{len(r['missing'])}")

    total_n = sum(r["numbers"] for r in results)
    total_m = sum(len(r["missing"]) for r in results)
    total_c = sum(len(r["calculated"]) for r in results)
    total_o = sum(len(r["other_form"]) for r in results)
    print(f"\n  この{len(results)}本が自分で計算して出した数字 {total_c}個。これは弱点ではなく、このサイトの価値そのもの。")
    print("  出典の要約なら誰でも書ける。自分で計算した数字があるから読む値打ちがある。")
    print("  照合できないことを理由に、こういう数字を消したり丸めたりしないこと。")
    print(f"  (単位違いなど、別の字面で出典にあった数字 {total_o}個 も照合済みとして数えています)")
    dead = sum(len(r["failed"]) for r in results)

    print("\n" + "=" * 68)
    print(f" 記事{len(results)}本 / 数字{total_n}個 / "
          f"出典に見つからなかった数字 {total_m}個 "
          f"({total_m / total_n * 100:.1f}%)" if total_n else " 数字なし")
    print(f" 取れなかった出典 {dead}本 / 経過 {time.time() - t0:.0f}秒")
    print("=" * 68 + "\n")

    incon = [r for r in results if r["inconclusive"] and r["missing"]]
    if incon:
        print(f" うち、中身のある出典が取れず判定できない記事: {len(incon)}本")
        print(" (JavaScriptで中身を描くページなど。疑わしいのではなく、確かめられない)\n")

    for r in results:
        if not r["missing"] and not r["failed"]:
            continue
        print(f"--- {r['path']} ---")
        if r["inconclusive"]:
            print("    中身のある出典が取れていないため、この記事の照合結果は当てになりません")
        if r["no_source_text"]:
            print("    出典の文章が1本も取れていないため、照合できていません")
        for n in r["missing"][:8]:
            print(f"    [{n['raw']}]  …{n['context']}…")
        if len(r["missing"]) > 8:
            print(f"    ほか{len(r['missing']) - 8}個")
        for u, why in r["failed"][:4]:
            print(f"    (出典が取れず: {why}) {u}")
        print()

    if args.json:
        Path(args.json).write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSONを保存しました: {args.json}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
