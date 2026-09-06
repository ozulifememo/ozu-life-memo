# -*- coding: utf-8 -*-
"""pr/ の発信素材(note原稿・インスタ投稿・大洲検定の問題)を点検する。

check_site.py がサイト本体を見るのに対して、こちらは「外に出す前の原稿」を見る。
pr/ は .gitignore 済みで公開されないが、**中身はこれから外に出る**ので、
匿名性と事実の裏取りはサイト本体と同じ厳しさで見る必要がある。

check_site.py と同じ考え方で、2種類に分けている。

  関所(エラー) … 正解が1つしかないもの。匿名性・文字化け・出典の不在・形式の崩れ
  目安(警告)   … 好みの話。字数・語尾・長さのばらつき

エラーが1件でもあれば終了コード1を返す。警告では止めない。

使い方:
    python tools/check_pr.py            # 全部見る
    python tools/check_pr.py note       # note原稿だけ
    python tools/check_pr.py insta      # インスタ投稿だけ
    python tools/check_pr.py quiz       # 大洲検定の問題だけ
"""
import html as html_lib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent

# 個人を特定しうる語の一覧はリポジトリに置かない(check_site.py と同じ作法)。
BANNED, SUSPECT, ALLOW = [], [], []
_words = ROOT / "private-notes" / "banned-words.py"
if _words.exists():
    _ns = {}
    exec(compile(_words.read_text(encoding="utf-8"), str(_words), "exec"), _ns)
    BANNED = _ns.get("BANNED", [])
    SUSPECT = _ns.get("SUSPECT", [])
    ALLOW = _ns.get("ALLOW", [])

# 「数当てゲーム」になっている選択肢を見つけるための印。
# 本人の判断(2026-09-03):「数字とか時期を選ぶのは面白くない。由来、理由、どこ、
# みたいに考える余白があるもの」。文章でお願いすると必ず戻るので、機械に置く。
#
# ただし1つの選択肢に数字があるだけでは違反にしない。「1円も払っていない」
# 「平成30年の豪雨」「国道56号」のように、数字が事柄の名前や慣用句として
# 入っているだけのことがあるため。**複数の選択肢に数字が並んだとき**にだけ
# 止める。そこで初めて「どの数字が正しいか」を当てさせる形になる。
NUMERIC = re.compile(r"[0-9０-９]|[一二三四五六七八九十百千万]\s*(年|人|円|割|%|％|件|戸|校|社|本|台|か所|箇所)")

# note原稿は「です・ます調」で通す。常体で終わる文を拾う(引用と出典欄は除く)。
JOTAI_END = re.compile(r"(?<![でま])(だ|である|だった|であった|ない|なかった|いる|いた|"
                       r"した|する|なる|なった|れる|られる|ある|あった|ろう)[。！]")


def norm_urls(s):
    """URLの書き方の違いをならす(&amp;→&、%E3%81%82→あ、末尾の/を無視)。"""
    s = html_lib.unescape(s)
    try:
        s = unquote(s)
    except Exception:
        pass
    return s


class Report:
    def __init__(self):
        self.errors = []
        self.warns = []

    def error(self, where, kind, msg):
        self.errors.append((where, kind, msg))

    def warn(self, where, kind, msg):
        self.warns.append((where, kind, msg))

    def dump(self):
        for label, rows in (("エラー", self.errors), ("警告", self.warns)):
            if not rows:
                continue
            print(f"\n── {label} {len(rows)}件 " + "─" * 40)
            for where, kind, msg in rows:
                print(f"  [{kind}] {where}\n      {msg}")
        print()
        print(f"エラー {len(self.errors)}件 / 警告 {len(self.warns)}件")
        return 1 if self.errors else 0


def scan_anonymity(rep, where, text):
    """匿名性。ここだけは note でもインスタでもサイト本体と同じ厳しさで見る。"""
    for word, why in BANNED:
        if word in ALLOW:
            continue
        for m in re.finditer(re.escape(word), text):
            around = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ")
            rep.error(where, "匿名性", f"「{word}」があります({why}) …{around}…")
    for word, why in SUSPECT:
        for m in re.finditer(re.escape(word), text):
            around = text[max(0, m.start() - 20):m.end() + 20].replace("\n", " ")
            rep.warn(where, "匿名性", f"「{word}」があります({why}) …{around}…")


def scan_mojibake(rep, where, text):
    if "�" in text:
        rep.error(where, "文字化け", "置換文字(U+FFFD)があります")
    # CJK互換漢字。Notion経由やエスケープの手組みで紛れ込むことがある
    for m in re.finditer(r"[豈-﫿]", text):
        rep.error(where, "文字化け", f"互換漢字 U+{ord(m.group()):04X} があります")


# ── note原稿 ────────────────────────────────────
NOTE_MARKS = ["【タイトル】", "【見出し画像】", "【本文ここから】", "【本文ここまで】", "【ハッシュタグ】"]


def check_note(rep):
    dirs = sorted(d for d in (ROOT / "pr" / "note").iterdir() if d.is_dir())
    n = 0
    for d in dirs:
        f = d / "原稿.txt"
        if not f.exists():
            rep.error(f"pr/note/{d.name}", "構造", "原稿.txt がありません")
            continue
        n += 1
        where = f"pr/note/{d.name}/原稿.txt"
        text = f.read_text(encoding="utf-8")
        scan_anonymity(rep, where, text)
        scan_mojibake(rep, where, text)

        for mark in NOTE_MARKS:
            if mark not in text:
                rep.error(where, "構造", f"{mark} の行がありません")

        m = re.search(r"【見出し画像】\s*(\S+)", text)
        if m and not (d / m.group(1)).exists():
            rep.error(where, "画像", f"見出し画像 {m.group(1)} がフォルダにありません")

        title = re.search(r"【タイトル】\s*\n(.+)", text)
        if not title or not title.group(1).strip():
            rep.error(where, "構造", "【タイトル】の次の行が空です")

        # 元記事URL。ここから元記事を割り出して出典を照合する。
        # サイトの記事の転載ではない回(運営の裏話など)には元記事が無いので、
        # 「転載です」と名乗っている原稿にだけこの検査をかける。
        src = re.search(r"元記事はこちら[^\n]*:\s*\n(https://\S+)", text)
        if not src:
            if "からの転載です" in text:
                rep.error(where, "構造", "転載と書いてあるのに「元記事はこちら:」がありません")
        else:
            rel = src.group(1).split("ozu-life-memo/")[-1]
            page = ROOT / rel
            if not page.exists():
                rep.error(where, "元記事", f"元記事 {rel} がこのリポジトリにありません")
            else:
                # 元記事のHTMLは &amp; と %E3%81%82 の形で書かれていることがあり、
                # 原稿では生の & と日本語に開いてある。同じURLを別物と誤判定しないよう、
                # 両方を「実体参照を戻し、パーセント符号化を解いた形」にそろえて比べる。
                html = norm_urls(page.read_text(encoding="utf-8"))
                body = text.split("【出典】")[-1].split("この記事は、大洲の生活情報")[0]
                urls = re.findall(r"https?://[^\s)」』]+", body)
                if len(urls) < 2:
                    rep.error(where, "出典", f"出典欄のURLが{len(urls)}本しかありません(2本以上)")
                for u in urls:
                    if norm_urls(u).rstrip("/") not in html:
                        rep.error(where, "出典",
                                  f"元記事に無いURLです(組み立てた可能性): {u}")

        for line in ("https://ozulifememo.github.io/ozu-life-memo/",
                     "間違いを見つけたら"):
            if line not in text:
                rep.warn(where, "定型", f"締めの定型文「{line}」がありません")

        # ── ここから目安 ──
        body = text.split("【本文ここから】")[-1].split("【出典】")[0]
        lines = [l.strip() for l in body.split("\n")]
        jotai = []
        for l in lines:
            if not l or l.startswith(("#", "http", "---", "【")):
                continue
            if l.count("「") != l.count("」"):   # 引用のまたぎ行は見ない
                continue
            for s in re.split(r"(?<=[。！])", l):
                s = s.strip()
                if not s or "「" in s:          # 引用を含む文は常体でよい
                    continue
                if JOTAI_END.search(s):
                    jotai.append(s)
        if len(jotai) > 5:
            rep.warn(where, "語尾", f"常体で終わる文が{len(jotai)}文あります(1例: {jotai[0][:40]})")

        for l in lines:
            if len(l) > 150 and not l.startswith("http"):
                rep.warn(where, "1文の長さ", f"{len(l)}字の段落があります: {l[:30]}…")

        strong = body.count("**") // 2
        if strong > 14:
            rep.warn(where, "太字", f"太字が{strong}か所あります(多すぎると効きません)")

        tags = re.search(r"【ハッシュタグ】\s*\n(.+)", text)
        if tags:
            k = len(re.findall(r"#\S+", tags.group(1)))
            if not 6 <= k <= 14:
                rep.warn(where, "タグ", f"ハッシュタグが{k}個です(8〜11個が目安)")
    print(f"note原稿 {n}本を見ました")


# ── インスタ投稿 ─────────────────────────────────
LIMITS = {"cover_lines": 13, "choices": 22, "answer_head": 14, "why_head": 14,
          "answer_body": 24, "why_body": 24}
BANDS = {"大洲の雑学", "知って得する", "保存版", "数字で見る大洲", "大洲の記憶"}


def check_insta(rep):
    f = ROOT / "pr" / "instagram" / "quiz-posts.json"
    if not f.exists():
        print("pr/instagram/quiz-posts.json がありません(飛ばします)")
        return
    try:
        posts = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        rep.error("pr/instagram/quiz-posts.json", "構造", f"JSONとして読めません: {e}")
        return
    scan_anonymity(rep, "pr/instagram/quiz-posts.json", f.read_text(encoding="utf-8"))
    scan_mojibake(rep, "pr/instagram/quiz-posts.json", f.read_text(encoding="utf-8"))

    seen_no, seen_slug = set(), set()
    ans = {"A": 0, "B": 0, "C": 0}
    for p in posts:
        where = f"投稿{p.get('no', '?')}({p.get('slug', '?')})"
        for key in ("no", "slug", "band", "photo", "cover_lines", "choices",
                    "answer_head", "answer_body", "why_head", "why_body"):
            if not p.get(key):
                rep.error(where, "構造", f"{key} がありません")
        if p.get("no") in seen_no:
            rep.error(where, "重複", f"投稿番号{p['no']}が2回出てきます")
        seen_no.add(p.get("no"))
        if p.get("slug") in seen_slug:
            rep.error(where, "重複", f"記事 {p['slug']} を2回使っています")
        seen_slug.add(p.get("slug"))

        if p.get("band") not in BANDS:
            rep.error(where, "構造", f"帯が一覧にありません: {p.get('band')}")
        ph = ROOT / "assets" / "img" / str(p.get("photo", ""))
        if not ph.exists():
            rep.error(where, "画像", f"写真がありません: {p.get('photo')}")

        ch = p.get("choices", [])
        if len(ch) != 3:
            rep.error(where, "クイズ", f"選択肢が{len(ch)}個です(3個)")
        for c in ch:
            if not re.match(r"^[ABC] ", c):
                rep.error(where, "クイズ", f"選択肢が「A 」「B 」「C 」で始まっていません: {c}")
        n_num = sum(1 for c in ch if NUMERIC.search(c))
        if n_num >= 2:
            rep.error(where, "クイズ",
                      f"3択のうち{n_num}つに数字があります。数当てゲームになっています: "
                      + " / ".join(c for c in ch if NUMERIC.search(c)))
        elif n_num == 1:
            rep.warn(where, "クイズ",
                     "1つだけ数字を含む選択肢があります。数を当てさせる問いになっていないか: "
                     + next(c for c in ch if NUMERIC.search(c)))
        if ch:
            ln = [len(c) for c in ch]
            if max(ln) - min(ln) >= 7:
                rep.warn(where, "クイズ",
                         f"選択肢の長さがそろっていません({ln})。長いほうが正解に見えます")

        a = p.get("answer")
        if a not in ("A", "B", "C"):
            rep.error(where, "クイズ", f"正解(answer)がA/B/Cで書かれていません: {a}")
        else:
            ans[a] += 1
            # 「正解はBです」と書いてあるのに、2枚目がAの話をしている取り違えを拾う。
            # よい答えの面は選択肢を言い換えるので、言葉が重ならないのは普通のこと。
            # だから「重なりが少ない」では止めず、**外れのほうが正解より
            # はっきりよく重なっているとき**だけ疑う。そこが本当の取り違え。
            slide = "".join(p.get("answer_head", []) + p.get("answer_body", [])).replace("**", "")

            def overlap(c):
                t = re.sub(r"[はがをにでとのやも、。！？「」]", "", c[2:])
                g = {t[i:i + 2] for i in range(len(t) - 1)}
                return sum(1 for x in g if x in slide) / max(1, len(g))

            hits = {c[0]: overlap(c) for c in ch if re.match(r"^[ABC] ", c)}
            if a in hits:
                best = max(hits, key=hits.get)
                if best != a and hits[best] - hits[a] > 0.25:
                    rep.warn(where, "クイズ",
                             f"答えの面は{best}の話に見えるのに、正解が{a}になっています"
                             f"(重なり {best}={hits[best]:.2f} / {a}={hits[a]:.2f})")

        for key, lim in LIMITS.items():
            for line in p.get(key, []):
                if len(line.replace("**", "")) > lim:
                    rep.warn(where, "字数",
                             f"{key} が{len(line.replace('**', ''))}字です(上限{lim}): {line}")
        for key in ("answer_body", "why_body"):
            rows = p.get(key, [])
            if len(rows) > 9:
                rep.warn(where, "字数", f"{key} が{len(rows)}行あります(9行まで)")
        for key in ("cover_lines", "answer_head", "why_head"):
            if len(p.get(key, [])) > 3:
                rep.warn(where, "字数", f"{key} が{len(p[key])}行あります(3行まで)")

        cap = p.get("caption", "")
        if not 150 <= len(cap) <= 700:
            rep.warn(where, "キャプション", f"{len(cap)}字です(250〜450字が目安)")
        tags = p.get("hashtags", [])
        if not 8 <= len(tags) <= 16:
            rep.warn(where, "タグ", f"ハッシュタグが{len(tags)}個です(10〜14個が目安)")

    total = sum(ans.values())
    if total:
        for k, v in ans.items():
            if v > total * 0.5:
                rep.warn("全体", "クイズ",
                         f"正解が{k}に偏っています({v}/{total})。勘で当たるようになります")
    print(f"インスタ投稿 {len(posts)}本を見ました(正解の分布 A{ans['A']} B{ans['B']} C{ans['C']})")


# ── 大洲検定の問題 ───────────────────────────────
NEW_MARK = "考える型"


def check_quiz(rep):
    f = ROOT / "assets" / "js" / "quiz-data.js"
    text = f.read_text(encoding="utf-8")
    where = "assets/js/quiz-data.js"
    scan_anonymity(rep, where, text)
    scan_mojibake(rep, where, text)

    # quiz-data.js は const 宣言なので require では読めない。node で評価して中身を出す。
    # encoding を指定しないと、Windows では cp932 で読もうとして日本語で落ちる。
    r = subprocess.run(
        ["node", "-e",
         "const fs=require('fs');const s=fs.readFileSync(process.argv[1],'utf8');"
         "const OZU_QUIZ=eval(s+';OZU_QUIZ');"
         "console.log(JSON.stringify(OZU_QUIZ.map(q=>({q:q.q,c:q.choices,a:q.answer,u:q.url||null}))));",
         str(f)],
        capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0 or not r.stdout:
        rep.error(where, "構造", f"JavaScriptとして読めません: {r.stderr.strip()[:200]}")
        return
    qs = json.loads(r.stdout)

    seen = {}
    for i, q in enumerate(qs):
        if q["q"] in seen:
            rep.error(where, "重複", f"同じ問題が2回あります: {q['q'][:40]}")
        seen[q["q"]] = i
        if not isinstance(q["c"], list) or len(q["c"]) != 4:
            rep.error(where, "構造", f"選択肢が4つではありません: {q['q'][:40]}")
        if not isinstance(q["a"], int) or not 0 <= q["a"] < len(q["c"] or []):
            rep.error(where, "構造", f"answerが選択肢の範囲外です: {q['q'][:40]}")

    # 数字選択肢の検査は、あとから作った目安なので**新しく足した問題にだけ**効かせる。
    # 公開済みの問題を新しい目安で書き直さない(CLAUDE.md の方針)。
    head = text.split(NEW_MARK)[0] if NEW_MARK in text else text
    n_old = head.count('\n    q: "')
    dist = [0, 0, 0, 0]
    n_new = 0
    for q in qs[n_old:]:
        n_new += 1
        dist[q["a"]] += 1
        n_num = sum(1 for c in q["c"] if NUMERIC.search(c))
        if n_num >= 2:
            rep.error(where, "クイズ",
                      f"新しい問題が数当てゲームになっています({n_num}/4に数字): {q['q'][:36]}")
        elif n_num == 1:
            rep.warn(where, "クイズ",
                     f"数字を含む選択肢が1つあります: {q['q'][:30]} / "
                     + next(c for c in q["c"] if NUMERIC.search(c)))
        ln = [len(c) for c in q["c"]]
        if max(ln) - min(ln) >= 12:
            rep.warn(where, "クイズ",
                     f"選択肢の長さがそろっていません{ln}: {q['q'][:36]}")
    if n_new:
        for i, v in enumerate(dist):
            if v > n_new * 0.4:
                rep.warn(where, "クイズ",
                         f"新しい問題の正解が{i}番目に偏っています({v}/{n_new})")
    print(f"大洲検定 {len(qs)}問を見ました(うち新しく足したのは{n_new}問"
          f" / 正解の分布 {dist})")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    rep = Report()
    if not BANNED:
        print("!! private-notes/banned-words.py が無いので匿名性の検査を飛ばしています")
    if what in ("all", "note"):
        check_note(rep)
    if what in ("all", "insta"):
        check_insta(rep)
    if what in ("all", "quiz"):
        check_quiz(rep)
    sys.exit(rep.dump())


if __name__ == "__main__":
    main()
