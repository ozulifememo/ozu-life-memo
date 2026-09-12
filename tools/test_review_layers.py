# -*- coding: utf-8 -*-
"""レビュー卓の「層」と「向き」を、本物のブラウザで確かめる。

2026-09-12、本人の指摘で作った。

> まだ僕が見ていない記事、1回評価したけどまだクロコは見ていない記事
> (もしくは△にしたけど、メモがないから、クロコが改善できない記事)、
> やり取り、完了した記事。
> あと、できたら、完了の記事にもコメントと三角に戻すようにしてほしい。

見たいのは4つの状態で、それが画面の上で見分けられるか。
とくに「△だけどメモが無い＝クロコが動けない」が、
それまで「クロコ待ち」に混ざって外から見えなかった。
"""
import sys
import pathlib
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SITE = pathlib.Path(__file__).resolve().parent.parent
URL = (SITE / "_review.html").as_uri()
ok = fail = 0
errs = []


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print("  OK  ", name, extra)
    else:
        fail += 1
        print("  NG  ", name, extra)


with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append("console:" + m.text)
          if (m.type == "error" and "ERR_FILE_NOT_FOUND" not in m.text) else None)
    pg.goto(URL, wait_until="load", timeout=180000)
    pg.wait_for_timeout(2500)

    # 4つの状態を、判定とメモと返事の組み合わせで作る
    pg.evaluate("""() => {
      localStorage.clear(); S = {}; R = {};
      const s = i => A.filter(a => a.kind !== 'idea')[i].slug;
      window.__T = {mi: s(0), memo: s(1), kuroko: s(2), harada: s(3), kan: s(4)};
      const now = Date.now();
      // ① 未読 … 何も付けない(s(0)はそのまま)
      // ② メモ待ち … △だけ。メモ無し
      S[__T.memo]   = {v:'fix', m:'', ms:[], mt:0, t:now};
      // ③ クロコ待ち … △＋メモあり、返事なし
      S[__T.kuroko] = {v:'fix', m:'ここを直して', ms:[{text:'ここを直して', t:now}], mt:now, t:now};
      // ④ 見てほしい … △＋メモ、そのあとクロコの返事
      S[__T.harada] = {v:'fix', m:'ここを直して', ms:[{text:'ここを直して', t:now-1000}],
                       mt:now-1000, t:now-1000};
      R[__T.harada] = {items:[{kind:'naosita', text:'直しました', t:now}]};
      // ⑤ 完了 … ◯
      S[__T.kan]    = {v:'ok', m:'', ms:[], mt:0, t:now};
      saveLocal(); build(); paint();
    }""")
    pg.wait_for_timeout(400)

    print("\n=== 層の振り分け ===")
    lay = pg.evaluate("(() => { const o = {}; for (const k in __T) o[k] = layerOf(__T[k]); return o; })()")
    check("未読は未読の層", lay["mi"] == "mi", lay["mi"])
    check("メモ待ちはやり取りの層", lay["memo"] == "yari", lay["memo"])
    check("クロコ待ちはやり取りの層", lay["kuroko"] == "yari", lay["kuroko"])
    check("見てほしいはやり取りの層", lay["harada"] == "yari", lay["harada"])
    check("◯は完了の層", lay["kan"] == "kan", lay["kan"])

    print("\n=== やり取りの中の向き ===")
    tn = pg.evaluate("(() => { const o = {}; for (const k in __T) o[k] = turnOf(__T[k]); return o; })()")
    check("△でメモが無いと「メモ待ち」", tn["memo"] == "memo", tn["memo"])
    check("メモを送ると「クロコ待ち」", tn["kuroko"] == "kuroko", tn["kuroko"])
    check("クロコが返すと「見てほしい」", tn["harada"] == "harada", tn["harada"])

    print("\n=== 札(チップ)に数が出るか ===")
    pg.evaluate("setLayer('yari')")
    pg.wait_for_timeout(400)
    chips = pg.eval_on_selector_all("#fState .chip",
                                    "els=>els.map(e=>e.textContent.trim())")
    print("   ", chips)
    check("「メモ待ち」の札がある", any("メモ待ち" in c for c in chips))
    check("札に数が付いている", all(any(ch.isdigit() for ch in c) for c in chips), chips)
    check("メモ待ちは1本", any(c.replace("メモ待ち", "") == "1" for c in chips),
          [c for c in chips if "メモ待ち" in c])

    print("\n=== メモ待ちの記事を開いたときの案内 ===")
    pg.evaluate("F.turn='memo'; sync('#fState','s','memo'); refresh()")
    pg.wait_for_timeout(400)
    check("メモ待ちだけに絞れる",
          pg.evaluate("ORDER.length") == 1, pg.evaluate("ORDER.length"))
    pg.evaluate("show(ORDER[0])")
    pg.wait_for_timeout(400)
    talk = pg.inner_text("#talk")
    check("メモが無いことを知らせる", "メモがまだありません" in talk)
    check("何をすればよいか書いてある", "メモ" in talk and "押し間違い" in talk)

    print("\n=== 完了の層で、直すに戻せるか ===")
    pg.evaluate("setLayer('kan')")
    pg.wait_for_timeout(400)
    check("◯の釦は隠れている",
          not pg.is_visible("#bot .v[data-v=ok]"))
    check("✕の釦も隠れている",
          not pg.is_visible("#bot .v[data-v=drop]"))
    check("△の釦は出ている", pg.is_visible("#bot .v[data-v=fix]"))
    check("札の字が「直すに戻す」になる",
          pg.inner_text("#bot .v[data-v=fix]").strip().endswith("直すに戻す"),
          pg.inner_text("#bot .v[data-v=fix]").strip())
    check("メモの釦も押せる", pg.is_visible("#memobtn"))
    # 実際に押して、やり取りへ戻るか
    pg.evaluate("show(IDX[__T.kan])")
    pg.wait_for_timeout(300)
    pg.click("#bot .v[data-v=fix]")
    pg.wait_for_timeout(600)
    check("押すと判定が△になる",
          pg.evaluate("(S[__T.kan]||{}).v") == "fix", pg.evaluate("(S[__T.kan]||{}).v"))
    check("やり取りの層へ移る",
          pg.evaluate("layerOf(__T.kan)") == "yari", pg.evaluate("layerOf(__T.kan)"))
    check("メモが無いので「メモ待ち」になる",
          pg.evaluate("turnOf(__T.kan)") == "memo", pg.evaluate("turnOf(__T.kan)"))

    print("\n=== 狭い画面でも釦が見えるか ===")
    sp = br.new_page(viewport={"width": 390, "height": 844})
    sp.goto(URL, wait_until="load", timeout=180000)
    sp.wait_for_timeout(2500)
    sp.evaluate("setLayer('kan')")
    sp.wait_for_timeout(400)
    check("スマホ幅でも△が見える", sp.is_visible("#bot .v[data-v=fix]"))
    check("スマホ幅で横スクロールしない",
          sp.evaluate("document.documentElement.scrollWidth<=document.documentElement.clientWidth+1"))

    br.close()

print()
if errs:
    print("ページのエラー:")
    for e in errs[:8]:
        print("  ", e[:200])
print("OK %d / NG %d / エラー %d" % (ok, fail, len(errs)))
sys.exit(1 if (fail or errs) else 0)
