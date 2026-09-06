# -*- coding: utf-8 -*-
"""大洲検定250問を、1枚で読み返すページを作る。

本人の指示(2026-09-06):
「クイズは1問1問ごとではなく、ぼくがみやすいようにしたい。
　問題文と正解、誤答、補足・説明をみたい。」

だから、めくる作りにはしない。ぜんぶ縦に並べて、上から読める形にする。
"""
import html
import io
import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

def load_quiz():
    """assets/js/quiz-data.js を node に読ませて JSON にする。
    正規表現で拾うと選択肢の中のかっこや引用符で崩れるので、
    JavaScript として評価させる。"""
    import subprocess
    import tempfile
    import os
    nl = chr(10)
    js = nl.join([
        "const fs = require('fs');",
        "const s = fs.readFileSync(process.argv[2], 'utf8');",
        "const q = new Function(s + ';' + 'return OZU_QUIZ;')();",
        "process.stdout.write(JSON.stringify(q));",
    ])
    fd, p = tempfile.mkstemp(suffix=".js")
    os.close(fd)
    io.open(p, "w", encoding="utf-8").write(js)
    try:
        r = subprocess.run(["node", p, "assets/js/quiz-data.js"],
                           capture_output=True, encoding="utf-8")
        out = r.stdout
        if r.returncode:
            print(r.stderr[:400])
    finally:
        os.unlink(p)
    if not out:
        sys.exit("エラー: quiz-data.js を読めませんでした(node は要ります)")
    return json.loads(out)


Q = [{"q": x.get("q", ""),
      "choices": x.get("choices", []),
      "answer": x.get("answer", 0),
      "explain": x.get("explain", ""),
      "url": x.get("url", "")}
     for x in load_quiz()]


def dom(u):
    m = re.match(r"https?://([^/]+)", u or "")
    return m.group(1) if m else ""


ans = Counter(x["answer"] for x in Q)
doms = Counter(dom(x["url"]) for x in Q if x["url"])
no_src = sum(1 for x in Q if not x["url"])
yahoo = sum(1 for x in Q if "news.yahoo.co.jp" in (x["url"] or ""))

rows = []
for i, x in enumerate(Q):
    rows.append({
        "n": i + 1,
        "q": x["q"],
        "c": x["choices"],
        "a": x["answer"],
        "e": x["explain"],
        "u": x["url"],
        "d": dom(x["url"]),
    })

DATA = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
LB = "ABCD"

HEAD = """<title>大洲検定 全問一覧</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@600;700&family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root{
  --paper:#f6f4ef; --card:#fffefb; --ink:#1b2026; --slate:#63707c; --faint:#8d98a3;
  --rule:#ded9d0; --hair:#eae6de;
  --mark:#0f5f5a; --markbg:#e4efec; --flag:#9a5a20; --flagbg:#f7eee1;
  --mincho:"Shippori Mincho B1",serif;
  --sans:"Noto Sans JP",system-ui,-apple-system,"Hiragino Kaku Gothic ProN",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
:root:not([data-theme="light"]){}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#15191d; --card:#1b2026; --ink:#e4e8eb; --slate:#93a2ae; --faint:#6e7b87;
    --rule:#29313a; --hair:#222932;
    --mark:#57b8ab; --markbg:#16302e; --flag:#cf9a55; --flagbg:#33281a;
  }
}
:root[data-theme="dark"]{
  --paper:#15191d; --card:#1b2026; --ink:#e4e8eb; --slate:#93a2ae; --faint:#6e7b87;
  --rule:#29313a; --hair:#222932;
  --mark:#57b8ab; --markbg:#16302e; --flag:#cf9a55; --flagbg:#33281a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.85;-webkit-text-size-adjust:100%}
a{color:var(--mark)}
:focus-visible{outline:2px solid var(--mark);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}

/* ---- 見出し ---- */
header{max-width:820px;margin:0 auto;padding:38px 22px 0}
h1{font-family:var(--mincho);font-size:30px;font-weight:700;margin:0 0 6px;
  letter-spacing:.04em;line-height:1.4;text-wrap:balance}
.lede{color:var(--slate);font-size:13.5px;margin:0 0 22px;line-height:1.9}

/* ---- 検算の帯 ---- */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:1px;background:var(--rule);border:1px solid var(--rule);margin-bottom:8px}
.stat{background:var(--card);padding:11px 13px}
.stat .k{font-size:10.5px;letter-spacing:.09em;color:var(--faint);
  text-transform:uppercase;font-family:var(--mono)}
.stat .v{font-family:var(--mono);font-size:21px;font-weight:600;
  font-variant-numeric:tabular-nums;line-height:1.4}
.stat .v.warn{color:var(--flag)}
.stat .s{font-size:11.5px;color:var(--slate);line-height:1.6}

/* 答えの偏り */
.bias{background:var(--card);border:1px solid var(--rule);border-top:none;
  padding:12px 13px;margin-bottom:26px}
.bias .k{font-size:10.5px;letter-spacing:.09em;color:var(--faint);
  text-transform:uppercase;font-family:var(--mono);margin-bottom:8px}
.bar{display:flex;height:26px;border:1px solid var(--rule);overflow:hidden}
.bar span{display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-size:11.5px;font-weight:600;color:var(--paper);
  background:var(--slate)}
.bar span:nth-child(2),.bar span:nth-child(3){background:var(--flag)}
.bias .s{font-size:11.5px;color:var(--slate);margin-top:8px;line-height:1.7}

/* ---- 道具の帯 ---- */
.tools{position:sticky;top:0;z-index:5;background:var(--paper);
  border-bottom:1px solid var(--rule);padding:10px 0 11px;margin-bottom:4px}
.tools .in{max-width:820px;margin:0 auto;padding:0 22px;
  display:flex;gap:9px;align-items:center;flex-wrap:wrap}
#q{flex:1 1 210px;min-width:150px;padding:7px 11px;border:1px solid var(--rule);
  background:var(--card);color:var(--ink);font-family:var(--sans);font-size:14px;border-radius:3px}
.chip{padding:6px 12px;border:1px solid var(--rule);background:var(--card);
  color:var(--slate);font-size:12.5px;cursor:pointer;border-radius:3px;
  font-family:var(--sans);white-space:nowrap}
.chip:hover{border-color:var(--slate)}
.chip.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.chip.flag.on{background:var(--flag);border-color:var(--flag);color:#fff}
.count{font-family:var(--mono);font-size:12.5px;color:var(--faint);
  font-variant-numeric:tabular-nums;margin-left:auto}

/* ---- 問題 ---- */
main{max-width:820px;margin:0 auto;padding:6px 22px 90px}
.item{display:grid;grid-template-columns:46px 1fr;gap:0 14px;
  padding:26px 0;border-bottom:1px solid var(--hair)}
.no{font-family:var(--mono);font-size:12.5px;color:var(--faint);
  font-variant-numeric:tabular-nums;padding-top:3px}
.qt{font-size:16.5px;font-weight:500;line-height:1.75;margin:0 0 13px;
  text-wrap:pretty}
.ch{list-style:none;margin:0 0 13px;padding:0;display:flex;
  flex-direction:column;gap:3px}
.ch li{display:grid;grid-template-columns:20px 1fr;gap:9px;
  font-size:14px;color:var(--slate);line-height:1.7;align-items:baseline}
.ch li .m{font-family:var(--mono);font-size:11.5px;color:var(--faint);
  text-align:center;border:1px solid var(--rule);border-radius:2px;
  line-height:1.55;align-self:start;margin-top:3px}
.ch li.ok{color:var(--ink);font-weight:500}
.ch li.ok .m{background:var(--mark);border-color:var(--mark);color:var(--paper);font-weight:600}
.ex{font-size:13.5px;color:var(--slate);line-height:1.85;
  border-left:2px solid var(--flag);padding:1px 0 1px 13px;margin:0 0 11px}
.src{font-family:var(--mono);font-size:11.5px;color:var(--faint);
  word-break:break-all;line-height:1.65}
.src a{color:var(--faint);text-decoration:none;border-bottom:1px solid var(--hair)}
.src a:hover{color:var(--mark);border-color:var(--mark)}
.tag{display:inline-block;font-family:var(--mono);font-size:10.5px;
  padding:1px 7px;border-radius:2px;background:var(--flagbg);color:var(--flag);
  border:1px solid var(--flag);margin-right:7px;line-height:1.7}
.none{padding:70px 0;text-align:center;color:var(--faint);font-size:14px}
footer{max-width:820px;margin:0 auto;padding:0 22px 60px;color:var(--faint);
  font-size:11.5px;line-height:1.9;border-top:1px solid var(--hair);padding-top:18px}
@media(max-width:560px){
  header{padding-top:26px}
  h1{font-size:24px}
  .item{grid-template-columns:1fr;gap:0}
  .no{padding-bottom:6px}
}
</style>"""


def esc(s):
    return html.escape(s or "", quote=False)


bias_total = sum(ans.values())
bars = "".join(
    '<span style="flex:%d">%s %d</span>' % (ans.get(i, 0), LB[i], ans.get(i, 0))
    for i in range(4))

top_doms = "".join(
    "<div>%s <b style='font-family:var(--mono)'>%d</b></div>" % (esc(d), n)
    for d, n in doms.most_common(6))

BODY = """
<header>
  <h1>大洲検定 全問一覧</h1>
  <p class="lede">
    サイトに載っている %d問を、まとめて読み返すための紙。1問ずつめくらずに、上から流し読みできる。<br>
    正解には <b style="color:var(--mark)">■</b> が付く。その下が補足、いちばん下が出典。
  </p>

  <div class="stats">
    <div class="stat"><div class="k">問題</div><div class="v">%d</div><div class="s">assets/js/quiz-data.js</div></div>
    <div class="stat"><div class="k">出典あり</div><div class="v">%d</div><div class="s">%d のサイトから</div></div>
    <div class="stat"><div class="k">出典なし</div><div class="v%s">%d</div><div class="s">裏が取れていない</div></div>
    <div class="stat"><div class="k">yahoo 出典</div><div class="v%s">%d</div><div class="s">数か月で消えるので使わない約束</div></div>
  </div>

  <div class="bias">
    <div class="k">正解の位置の偏り</div>
    <div class="bar">%s</div>
    <div class="s">
      いつも B か C を選ぶ人が、それだけで <b>%.0f%%</b> 取れてしまう。
      A と D が薄いので、作るときに寄っている。気になるなら選択肢の並びを入れ替える。
    </div>
  </div>
</header>

<div class="tools"><div class="in">
  <input id="q" type="search" placeholder="問題・選択肢・補足・出典から探す" autocomplete="off">
  <button class="chip on" data-f="">ぜんぶ</button>
  <button class="chip flag" data-f="nosrc">出典なし</button>
  <button class="chip flag" data-f="yahoo">yahoo</button>
  <button class="chip" data-f="ozu">大洲市サイト</button>
  <span class="count" id="cnt"></span>
</div></div>

<main id="list"></main>

<footer>
  もとのデータは <span style="font-family:var(--mono)">assets/js/quiz-data.js</span>。
  この紙は読むだけで、直すのは元のファイルのほう。<br>
  出典がいちばん多いのは %s
</footer>

<script>
var Q = %s;
var LB = "ABCD";
var F = { q: "", f: "" };
var list = document.getElementById('list');
var cnt = document.getElementById('cnt');

function esc(s){
  return String(s == null ? "" : s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function hay(x){
  return (x.q + " " + x.c.join(" ") + " " + x.e + " " + x.u).toLowerCase();
}
function pass(x){
  if(F.f === "nosrc" && x.u) return false;
  if(F.f === "yahoo" && x.u.indexOf("news.yahoo.co.jp") < 0) return false;
  if(F.f === "ozu" && x.u.indexOf("city.ozu.ehime.jp") < 0) return false;
  if(F.q && hay(x).indexOf(F.q) < 0) return false;
  return true;
}
function render(){
  var out = [], n = 0;
  for(var i = 0; i < Q.length; i++){
    var x = Q[i];
    if(!pass(x)) continue;
    n++;
    var ch = x.c.map(function(c, j){
      return '<li class="' + (j === x.a ? 'ok' : '') + '">'
           + '<span class="m">' + LB[j] + '</span><span>' + esc(c) + '</span></li>';
    }).join('');
    var tags = "";
    if(!x.u) tags += '<span class="tag">出典なし</span>';
    else if(x.u.indexOf("news.yahoo.co.jp") >= 0) tags += '<span class="tag">yahoo</span>';
    var src = x.u
      ? '<a href="' + esc(x.u) + '" target="_blank" rel="noopener">' + esc(x.u) + '</a>'
      : '<span style="color:var(--flag)">出典が書かれていない</span>';
    out.push('<div class="item"><div class="no">' + x.n + '</div><div>'
      + '<p class="qt">' + esc(x.q) + '</p>'
      + '<ul class="ch">' + ch + '</ul>'
      + (x.e ? '<p class="ex">' + esc(x.e) + '</p>' : '')
      + '<p class="src">' + tags + src + '</p>'
      + '</div></div>');
  }
  list.innerHTML = out.length ? out.join('')
    : '<div class="none">この条件に合う問題はありません。</div>';
  cnt.textContent = n + " / " + Q.length + " 問";
}
document.getElementById('q').addEventListener('input', function(e){
  F.q = e.target.value.trim().toLowerCase(); render();
});
document.querySelectorAll('.chip').forEach(function(b){
  b.onclick = function(){
    document.querySelectorAll('.chip').forEach(function(o){ o.classList.remove('on'); });
    b.classList.add('on');
    F.f = b.dataset.f;
    render();
  };
});
render();
</script>
""" % (
    len(Q), len(Q),
    len(Q) - no_src, len(doms),
    " warn" if no_src else "", no_src,
    " warn" if yahoo else "", yahoo,
    bars,
    100.0 * (ans.get(1, 0) + ans.get(2, 0)) / bias_total,
    "、".join("%s(%d問)" % (d, n) for d, n in doms.most_common(3)),
    DATA,
)

out = HEAD + BODY
io.open("_quiz-src.html", "w", encoding="utf-8", newline="").write(out)
print("書き出した: _quiz-src.html  %.1f KB" % (len(out.encode()) / 1024))
print("  問題 %d / 出典なし %d / yahoo %d" % (len(Q), no_src, yahoo))
print("  正解の位置: " + " ".join("%s=%d" % (LB[i], ans.get(i, 0)) for i in range(4)))
