// サイト内検索(2026-09-20)
// 索引は tools/make_search_index.py が作る assets/js/search-index.js。
// このファイルは「探し方」だけを持つ。検索ページ(search/)からだけ読み込む。
(function () {
  "use strict";

  // 人が打つ言葉と、記事が使う言葉のズレを埋める表。
  // ここに1行足すだけで、記事を1本も触らずに当たるようになる。
  // (2026-09-20 に索引を数えて、0本になっていた言葉から作った。
  //  例: 「ゴミ」はカタカナで書いた記事が1本も無く、それまで0本だった)
  var SYNONYMS = [
    ["ごみ", "ゴミ", "塵", "廃棄物", "分別"],
    ["マイナンバー", "マイナカード", "マイナンバーカード", "マイナ"],
    ["ワクチン", "予防接種", "接種"],
    ["高齢者", "お年寄り", "年寄り", "シニア", "老人"],
    ["保育園", "こども園", "幼稚園", "保育所", "認定こども園"],
    ["転入", "引っ越し", "引越し", "ひっこし", "転出", "住所変更"],
    ["医療", "病院", "診療所", "クリニック", "お医者", "通院"],
    ["バス", "路線バス", "コミュニティバス", "公共交通", "ぐるりんおおず"],
    ["子ども", "こども", "子供", "児童"],
    ["税金", "市税", "住民税", "固定資産税", "課税"],
    ["空き家", "空家", "あきや", "空き店舗"],
    ["補助金", "助成金", "支援金", "給付金", "補助"],
    ["移住", "定住", "田舎暮らし", "Iターン", "Uターン"],
    ["宿泊", "泊まる", "宿", "ホテル", "旅館", "民泊"],
    ["ふるさと納税", "ふるさと寄附", "返礼品"],
    ["介護", "要介護", "ケアマネ", "デイサービス", "特養"],
    ["防災", "災害", "避難", "ハザードマップ", "水害", "地震"],
    ["人口", "人口減少", "少子化", "過疎"],
    ["水道", "上水道", "下水道", "水道料金"],
    ["図書館", "蔵書"],
    ["学校", "小学校", "中学校", "高校", "統廃合"],
    ["市役所", "大洲市役所", "役所", "窓口"],
    ["議会", "市議会", "議員", "市議"],
    ["肱川", "ひじかわ"],
    ["大洲城", "おおずじょう", "お城"],
  ];

  // 1つの言葉から、探すべき言葉の一覧を作る
  var SYN_MAP = {};
  SYNONYMS.forEach(function (group) {
    group.forEach(function (w) {
      SYN_MAP[w] = (SYN_MAP[w] || []).concat(group);
    });
  });

  // 「が」「の」だけで探されると全部の記事に当たって役に立たないので、条件から外す。
  // 本物の検索は辞書で単語に切ってこれを捨てているが、辞書は数MBあって静的サイトには重い。
  // ここでは「助詞と、意味の薄い1文字のかな」を並べるだけで、ほぼ同じ効果を出す。
  var STOP = ("が の に を は で と も や へ か ね よ な ん だ です ます した する して いる ある" +
              " こと もの ため これ それ あれ どれ そして しかし また など ほか について において" +
              " a an the of in on at to for and or is are").split(" ");

  // フレーズで打たれたとき、切れ目になりやすいところ(助詞・記号)。
  // 2文字以上のものを先に並べないと、1文字のほうが先に当たってしまうので順番が大事。
  var SPLIT_RE = /について|における|から|まで|より|[はがのにをでとやへも]|[\s、。，．･・,.!?！？「」『』（）()【】]/g;

  function norm(s) {
    // 全角の英数字を半角に、大文字を小文字にそろえる
    s = (s || "").normalize("NFKC").toLowerCase();
    return s.replace(/\s+/g, " ").trim();
  }

  function isUseful(t) {
    if (!t) return false;
    if (STOP.indexOf(t) !== -1) return false;
    // ひらがな・カタカナ1文字は、ほぼ全部の記事に当たるので条件にしない(漢字1文字は残す)
    if (t.length === 1 && /[ぁ-んァ-ヶー]/.test(t)) return false;
    return true;
  }

  function terms(q) {
    // 空白(全角も)で区切る。それぞれが「全部入っていること」の条件になる
    return norm(q).split(" ")
      .filter(function (x) { return x.length > 0; })
      .filter(isUseful);
  }

  // 「が」「の」だけのように、どの記事にも当たってしまう探し方かどうか。
  // 0本と同じ扱いにせず、画面で別のことを言うために分けている。
  function isTooVague(q) {
    var raw = norm(q).split(" ").filter(function (x) { return x.length > 0; });
    return raw.length > 0 && terms(q).length === 0;
  }

  // フレーズで0本だったときに、助詞のところで切り直す。
  // 例:「大洲城に泊まる」→ ["大洲城","泊まる"] にして、両方入っている記事を探す
  function splitPhrase(q) {
    return norm(q).split(SPLIT_RE).filter(isUseful);
  }

  function variantsOf(t) {
    var v = SYN_MAP[t];
    if (!v) return [t];
    var out = [t];
    v.forEach(function (w) { if (out.indexOf(w) === -1) out.push(w); });
    return out.map(norm);
  }

  // ---- 探す ----
  // 1回目は打たれたまま探す。0本なら、助詞のところで切り直してもう一度探す。
  function search(query, index) {
    var r = searchOnce(terms(query), index);
    if (r.length) return r;
    var parts = splitPhrase(query);
    if (parts.length > 1) {
      r = searchOnce(parts, index);
      r.forEach(function (x) { x.split = true; });   // 切り直したことを画面に出すため
    }
    return r;
  }

  function searchOnce(ts, index) {
    if (!ts || !ts.length) return [];
    var groups = ts.map(variantsOf);

    var results = [];
    for (var i = 0; i < index.length; i++) {
      var it = index[i];
      var title = norm(it.t);
      var tags = norm((it.g || []).join(" "));
      var body = norm(it.b || "");
      var score = 0;
      var ok = true;
      var firstPos = -1;

      for (var g = 0; g < groups.length; g++) {
        var best = 0;
        for (var k = 0; k < groups[g].length; k++) {
          var w = groups[g][k];
          if (!w) continue;
          var mul = k === 0 ? 1 : 0.6;   // もとの言葉は、言い換えより強く数える
          var p = title.indexOf(w);
          if (p !== -1) best = Math.max(best, (p === 0 ? 14 : 10) * mul);
          if (tags.indexOf(w) !== -1) best = Math.max(best, 7 * mul);
          var bp = body.indexOf(w);
          if (bp !== -1) {
            // 本文の前のほうに出てくるほど、その記事の主題に近い
            best = Math.max(best, (4 - Math.min(3, bp / 250)) * mul);
            if (firstPos === -1 || bp < firstPos) firstPos = bp;
          }
        }
        if (best === 0) { ok = false; break; }   // 1つでも入っていない言葉があれば外す
        score += best;
      }
      if (!ok) continue;
      if ((it.d || "") >= "2026-01-01") score += 0.4;   // 新しいものを少しだけ上に
      results.push({ it: it, score: score, pos: firstPos, used: ts });
    }

    results.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return (b.it.d || "").localeCompare(a.it.d || "");
    });
    return results;
  }

  // ---- 見つかったところの前後を切り出して、当たった字を目立たせる ----
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function snippet(r, query) {
    var body = r.it.b || "";
    if (!body) return "";
    var start = r.pos > 0 ? Math.max(0, r.pos - 30) : 0;
    var text = body.slice(start, start + 150);
    if (start > 0) text = "…" + text;
    if (start + 150 < body.length) text = text + "…";

    var words = [];
    // 切り直して見つけた場合は、切り直したあとの言葉を目立たせる
    (r.used || terms(query)).forEach(function (t) {
      variantsOf(t).forEach(function (w) { if (w && words.indexOf(w) === -1) words.push(w); });
    });
    words = words.filter(Boolean).sort(function (a, b) { return b.length - a.length; });
    if (!words.length) return esc(text);

    // 当たったところで切り分けて、当たった側だけ <mark> で包む。
    // 先にHTMLの記号を置き換えてから探すと &amp; のような字に引っかかるので、この順にしている。
    var re = new RegExp("(" + words.map(function (w) {
      return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }).join("|") + ")", "gi");
    var parts = text.split(re);
    var out = "";
    for (var i = 0; i < parts.length; i++) {
      out += (i % 2 === 1) ? "<mark>" + esc(parts[i]) + "</mark>" : esc(parts[i]);
    }
    return out;
  }

  window.OzuSearch = {
    search: search,
    snippet: snippet,
    terms: terms,
    isTooVague: isTooVague,
    SYNONYMS: SYNONYMS,
  };
})();
