# -*- coding: utf-8 -*-
"""卓の中の記事が、本物のHTMLを直接開いたときと同じ中身になっているか照合する。"""
import sys, io, os, random, tempfile
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SITE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")).replace("\\","/")

VIEW = "file:///" + SITE + "/_review.html"
SHOT = os.path.join(tempfile.gettempdir(), "ozu-review-shots")
os.makedirs(SHOT, exist_ok=True)

COUNT_JS = """(sel)=>{
  const r=document.querySelector(sel);
  if(!r) return null;
  const n=(q)=>r.querySelectorAll(q).length;
  return {
    h1: (r.querySelector('h1')||{}).textContent || '',
    text: r.innerText.replace(/\\s+/g,'').length,
    p:n('p'), h2:n('h2'), h3:n('h3'), img:n('img'), svg:n('svg'),
    table:n('table'), li:n('li'), strong:n('strong'),
    ext:n('a[href^="http"]:not([href*="ozulifememo.github.io"])'),
    width: Math.round((r.getBoundingClientRect().width)),
  };
}"""

# 実物側は .article-page(記事/読書) か、自由研究はページ全体
SEL_REAL = {"news": ".article-page", "book": ".article-page", "jk": "body"}
SEL_VIEW = {"news": "#paper .article-page", "book": "#paper .article-page", "jk": "#paper"}

ng = []
with sync_playwright() as pw:
    br = pw.chromium.launch()
    v = br.new_page(viewport={"width": 1440, "height": 900})
    v.goto(VIEW, wait_until="load", timeout=180000)
    v.wait_for_timeout(2500)
    meta = v.evaluate("A")

    random.seed(7)
    # 種類ごとに満遍なく + 図解の重い記事も入れる
    pick = []
    for kind in ("news", "jk", "book"):
        idxs = [i for i, a in enumerate(meta) if a["kind"] == kind]
        pick += random.sample(idxs, min(6, len(idxs)))
    for i, a in enumerate(meta):
        if a["slug"] in ("ozu-kieta-bus", "hijikawa-474-shisen", "die-with-zero") and i not in pick:
            pick.append(i)

    r = br.new_page(viewport={"width": 1440, "height": 900})
    print("照合する記事:", len(pick), "本\n")
    print("%-30s %-6s %s" % ("slug", "種類", "ちがい"))
    print("-" * 78)
    for i in pick:
        a = meta[i]
        folder = {"news": "eachnews", "jk": "jiyu-kenkyu", "book": "book"}[a["kind"]]
        fn = ("_" if a["draft"] else "") + a["slug"] + ".html"
        r.goto("file:///" + SITE + "/" + folder + "/" + fn, wait_until="load", timeout=60000)
        r.wait_for_timeout(700)
        # 実物側は共通ヘッダ・フッタ・サイドバーを外してから数える(卓と同じ条件にする)
        r.evaluate("""()=>{
          document.querySelectorAll('.site-header,.site-footer,.article-sidebar,.related-list,.modal-overlay,[data-site-header],[data-site-footer],[data-site-modal]')
            .forEach(e=>e.remove());
        }""")
        R = r.evaluate(COUNT_JS, SEL_REAL[a["kind"]])

        v.evaluate("show(%d)" % i)
        v.wait_for_timeout(450)
        V = v.evaluate(COUNT_JS, SEL_VIEW[a["kind"]])

        diff = []
        if R is None or V is None:
            diff.append("要素が見つからない")
        else:
            if R["h1"].strip() != V["h1"].strip():
                diff.append("見出しがちがう")
            for k in ("p", "h2", "h3", "img", "svg", "table", "li", "strong", "ext"):
                if R[k] != V[k]:
                    diff.append("%s %d→%d" % (k, R[k], V[k]))
            if abs(R["text"] - V["text"]) > max(30, R["text"] * 0.02):
                diff.append("本文の長さ %d→%d" % (R["text"], V["text"]))
        mark = "同じ" if not diff else "  ".join(diff)
        print("%-30s %-6s %s" % (a["slug"][:30], a["kind"], mark))
        if diff:
            ng.append(a["slug"] + ": " + " ".join(diff))

    # 中央に来ているかも見る
    print("\n=== 本文の置かれ方 ===")
    ni = next(i for i, a in enumerate(meta) if a["kind"] == "news" and not a["draft"])
    v.evaluate("show(%d)" % ni); v.wait_for_timeout(500)
    b = v.evaluate("""()=>{const e=document.querySelector('#paper .article-page');
        const r=e.getBoundingClientRect();
        return {left:Math.round(r.left),right:Math.round(window.innerWidth-r.right),w:Math.round(r.width)}}""")
    print("   幅 %dpx / 左の余白 %d / 右の余白 %d" % (b["w"], b["left"], b["right"]))
    ok = b["w"] == 720 and abs(b["left"] - b["right"]) < 12
    print(("   OK   " if ok else "   NG   ") + "1行720pxのまま、左右の余白がそろっている")
    if not ok:
        ng.append("本文が中央に来ていない")
    v.screenshot(path=SHOT + "/shot-desktop.png")
    bi = next(i for i, a in enumerate(meta) if a["kind"] == "book")
    v.evaluate("show(%d)" % bi); v.wait_for_timeout(400)
    v.screenshot(path=SHOT + "/shot-book.png")
    br.close()

print("\n" + "=" * 60)
print("ずれ:", "なし" if not ng else ng)
print("=" * 60)
sys.exit(1 if ng else 0)
