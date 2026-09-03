# -*- coding: utf-8 -*-
"""_review.html を実際にブラウザで開いて動くか確かめる。"""
import sys, io
from playwright.sync_api import sync_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import tempfile, os
SITE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")).replace("\\","/")
URL = "file:///" + SITE + "/_review.html"
SHOT = os.path.join(tempfile.gettempdir(), "ozu-review-shots")
os.makedirs(SHOT, exist_ok=True)
ng = []

def check(name, cond, extra=""):
    print(("  OK   " if cond else "  NG   ") + name + ("  " + str(extra) if extra else ""))
    if not cond:
        ng.append(name)

def vis(pg, sel):
    """本当に画面に出ているか(hidden属性ではなく描画で見る)"""
    return pg.evaluate("""(s)=>{const e=document.querySelector(s);if(!e)return false;
        const r=e.getBoundingClientRect();
        return r.width>0 && r.height>0 && getComputedStyle(e).display!=='none';}""", sel)

with sync_playwright() as pw:
    br = pw.chromium.launch()
    errs = []

    # ===================== デスクトップ =====================
    pg = br.new_page(viewport={"width": 1440, "height": 900})
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errs.append("console.error: " + m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="load", timeout=180000)
    pg.wait_for_timeout(2500)

    print("\n=== 読み込み ===")
    check("JSエラーなし", not errs, errs[:3])
    check("記事217本", pg.evaluate("A.length") == 217, pg.evaluate("A.length"))
    check("本文ブロック217個", pg.evaluate("document.querySelectorAll('script[type=\"text/plain\"]').length") == 217)
    check("画像62枚", pg.evaluate("Object.keys(IMGS).length") == 62)

    print("\n=== ここが前回のバグ: 開いた直後の見え方 ===")
    check("一覧は閉じている", not vis(pg, "#drawer"))
    check("ヘルプは閉じている", not vis(pg, "#help"))
    check("メモ欄は閉じている", not vis(pg, "#memo"))
    check("記事は見えている", vis(pg, "#paper"))
    check("上のバーが見えている", vis(pg, "#top"))
    check("判定バーが見えている", vis(pg, "#bot"))
    pg.screenshot(path=SHOT + "/shot-desktop.png")

    print("\n=== 開け閉め ===")
    pg.keyboard.press("l"); pg.wait_for_timeout(300)
    check("Lで一覧が開く", vis(pg, "#drawer"))
    pg.screenshot(path=SHOT + "/shot-drawer.png")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    check("Escで一覧が閉じる", not vis(pg, "#drawer"))
    pg.click("#btn-help"); pg.wait_for_timeout(300)
    check("?ボタンでヘルプが開く", vis(pg, "#help"))
    pg.screenshot(path=SHOT + "/shot-help.png")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
    check("Escでヘルプが閉じる", not vis(pg, "#help"))

    print("\n=== 記事の中身 ===")
    check("サイトCSSが効いている",
          pg.evaluate("getComputedStyle(document.querySelector('#paper')).backgroundColor") == "rgb(246, 245, 242)")
    check("シェルは暗いまま",
          pg.evaluate("getComputedStyle(document.body).backgroundColor") == "rgb(23, 27, 32)")
    pg.evaluate("""(()=>{for(var i=0;i<A.length;i++){if(bodyOf(i).indexOf('data-im')>=0){show(i);return;}}})()""")
    pg.wait_for_timeout(900)
    img = pg.evaluate("""(()=>{const im=document.querySelector('#paper img[data-im]');
        return im?{w:im.naturalWidth,h:im.naturalHeight}:null})()""")
    check("メモう・写真が出ている", bool(img) and img["w"] > 0, img)
    svg_i = pg.evaluate("""(()=>{for(var i=0;i<A.length;i++){if(bodyOf(i).indexOf('<svg')>=0)return i;}return -1})()""")
    pg.evaluate("show(%d)" % svg_i); pg.wait_for_timeout(600)
    box = pg.evaluate("""(()=>{const s=document.querySelector('#paper svg');if(!s)return null;
        const r=s.getBoundingClientRect();return{w:Math.round(r.width),h:Math.round(r.height)}})()""")
    check("図解SVGが実寸で出る", bool(box) and box["w"] > 100 and box["h"] > 60, box)
    pg.screenshot(path=SHOT + "/shot-zukai.png")

    print("\n=== 217本ぜんぶ描く ===")
    bad = pg.evaluate("""(()=>{const b=[];for(let i=0;i<A.length;i++){show(i,false);
      const t=document.querySelector('#paper').innerText.trim();
      const h=document.querySelectorAll('#paper h1').length;
      if(t.length<120||h!==1)b.push({i:i,slug:A[i].slug,len:t.length,h1:h});}return b})()""")
    check("全217本で本文とh1が出る", len(bad) == 0, bad[:4])
    check("巡回してもJSエラーなし", not errs, errs[:3])

    print("\n=== 判定したら「並び順の次」へ行くか ===")
    pg.evaluate("localStorage.clear();S={};F.state='todo';F.kind='';F.sort='old';build();show(ORDER[0])")
    pg.wait_for_timeout(400)
    a0 = pg.evaluate("A[cur].slug")
    nxt = pg.evaluate("A[ORDER[1]].slug")          # いまの並びで「次」に来るはずの記事
    print("    いま:", pg.evaluate("A[cur].date"), pg.evaluate("A[cur].title")[:34])
    print("    次は:", pg.evaluate("A[ORDER[1]].date"), pg.evaluate("A[ORDER[1]].title")[:34])
    pg.keyboard.press("1"); pg.wait_for_timeout(600)
    check("◯が保存される", pg.evaluate("(S['%s']||{}).v" % a0) == "ok")
    check("並び順どおり次の記事へ送られる", pg.evaluate("A[cur].slug") == nxt,
          pg.evaluate("A[cur].date") + " " + pg.evaluate("A[cur].title")[:24])
    check("進みが1になる", pg.evaluate("document.querySelector('#progtxt').textContent") == "1")
    pg.keyboard.press("2"); pg.wait_for_timeout(600)
    check("△も保存される", pg.evaluate("(S['%s']||{}).v" % nxt) == "fix")
    check("進みが2になる", pg.evaluate("document.querySelector('#progtxt').textContent") == "2")

    print("\n=== 絞り込み ===")
    pg.keyboard.press("l"); pg.wait_for_timeout(300)
    check("「まだ」だと215本", pg.evaluate("document.querySelectorAll('#rows .row').length") == 215,
          pg.evaluate("document.querySelectorAll('#rows .row').length"))
    pg.evaluate("F.state='';sync('#fState','s','');refresh()"); pg.wait_for_timeout(300)
    check("「ぜんぶ」だと217本", pg.evaluate("document.querySelectorAll('#rows .row').length") == 217)
    check("◯の行に印1つ", pg.evaluate("document.querySelectorAll('#rows .row.ok').length") == 1)
    check("△の行に印1つ", pg.evaluate("document.querySelectorAll('#rows .row.fix').length") == 1)
    pg.evaluate("F.kind='draft';sync('#fKind','k','draft');refresh()"); pg.wait_for_timeout(250)
    check("下書きだけ33本", pg.evaluate("document.querySelectorAll('#rows .row').length") == 33)
    pg.evaluate("F.kind='jk';sync('#fKind','k','jk');refresh()"); pg.wait_for_timeout(250)
    check("自由研究21本", pg.evaluate("document.querySelectorAll('#rows .row').length") == 21)
    pg.evaluate("F.kind='';F.q='肱川';refresh()"); pg.wait_for_timeout(500)
    check("本文検索が当たる", pg.evaluate("document.querySelectorAll('#rows .row').length") > 3,
          pg.evaluate("document.querySelectorAll('#rows .row').length"))
    pg.evaluate("F.q='';F.state='todo';sync('#fState','s','todo');refresh()")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)

    print("\n=== メモ ===")
    pg.evaluate("show(5)"); pg.wait_for_timeout(200)
    pg.keyboard.press("m"); pg.wait_for_timeout(300)
    check("メモ欄が開く", vis(pg, "#memo"))
    pg.locator("#memoT").type("導入の言い方が今の方向とずれている", delay=6)
    pg.wait_for_timeout(700)
    slug5 = pg.evaluate("A[5].slug")
    check("メモが保存される", "ずれている" in (pg.evaluate("(S['%s']||{}).m" % slug5) or ""))
    check("メモ有りの印が付く", pg.evaluate("document.querySelector('#memobtn').classList.contains('has')"))
    pg.keyboard.press("Escape"); pg.wait_for_timeout(250)
    check("Escでメモ欄が閉じる", not vis(pg, "#memo"))

    print("\n=== リンク ===")
    pg.evaluate("""(()=>{for(var i=0;i<A.length;i++){if(bodyOf(i).indexOf('data-go=')>=0){show(i);return;}}})()""")
    pg.wait_for_timeout(400)
    check("サイト内リンクは卓の中で飛ぶ", pg.locator("#paper a[data-go]").count() > 0)
    before = pg.evaluate("cur")
    pg.locator("#paper a[data-go]").first.click(); pg.wait_for_timeout(500)
    check("押すと実際に別の記事へ移る", pg.evaluate("cur") != before,
          pg.evaluate("A[cur].title")[:30])
    ext = pg.evaluate("""(()=>{const a=document.querySelector('#paper a[href^="http"]');
        return a?a.target:null})()""")
    check("出典は別タブ", ext == "_blank", ext)
    check("相対リンクが残っていない", pg.evaluate("document.querySelectorAll('#paper a[href^=\"../\"]').length") == 0)

    print("\n=== 開き直しても残るか ===")
    slug_ok = a0
    pg.reload(wait_until="load", timeout=180000); pg.wait_for_timeout(2500)
    check("◯が残る", pg.evaluate("(S['%s']||{}).v" % slug_ok) == "ok")
    check("メモが残る", "ずれている" in (pg.evaluate("(S['%s']||{}).m" % slug5) or ""))
    check("進みの数が残る", pg.evaluate("document.querySelector('#progtxt').textContent") == "2")

    # ===================== iPad =====================
    print("\n=== iPad 縦 (834x1112) ===")
    ip = br.new_page(viewport={"width": 834, "height": 1112}, device_scale_factor=2,
                     is_mobile=True, has_touch=True)
    ip.on("pageerror", lambda e: errs.append("ipad: " + str(e)))
    ip.goto(URL, wait_until="load", timeout=180000); ip.wait_for_timeout(2500)
    check("画面幅どおりに組まれる（viewport meta）",
          ip.evaluate("document.documentElement.clientWidth") == 834,
          ip.evaluate("document.documentElement.clientWidth"))
    ip.evaluate("show(0)"); ip.wait_for_timeout(600)
    check("横スクロールしない",
          not ip.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth+2"),
          ip.evaluate("document.documentElement.scrollWidth"))
    check("一覧は閉じている", not vis(ip, "#drawer"))
    bot = ip.evaluate("""(()=>{const b=document.querySelector('#bot').getBoundingClientRect();
        return{top:Math.round(b.top),h:Math.round(b.height)}})()""")
    check("判定バーが画面の下端にある", 1030 < bot["top"] < 1060, bot)
    ip.screenshot(path=SHOT + "/shot-ipad.png")
    ip.evaluate("show(%d)" % svg_i); ip.wait_for_timeout(700)
    check("図解の記事でも横に溢れない",
          not ip.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth+2"),
          ip.evaluate("document.documentElement.scrollWidth"))
    ip.screenshot(path=SHOT + "/shot-ipad-zukai.png")
    ip.keyboard.press("l"); ip.wait_for_timeout(400)
    ip.screenshot(path=SHOT + "/shot-ipad-drawer.png")

    # ===================== 狭い画面 =====================
    print("\n=== 狭い画面 (390x844) ===")
    sm = br.new_page(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
    sm.goto(URL, wait_until="load", timeout=180000); sm.wait_for_timeout(2200)
    sm.evaluate("show(0)"); sm.wait_for_timeout(400)
    check("横スクロールしない",
          not sm.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth+2"),
          sm.evaluate("document.documentElement.scrollWidth"))
    check("判定の3ボタンが全部見える",
          sm.evaluate("""[...document.querySelectorAll('#bot .v')].every(b=>b.getBoundingClientRect().width>40)"""))
    sm.screenshot(path=SHOT + "/shot-small.png")

    br.close()

print("\n" + "=" * 48)
print("落ちた項目:", "なし" if not ng else ng)
print("=" * 48)
sys.exit(1 if ng else 0)
