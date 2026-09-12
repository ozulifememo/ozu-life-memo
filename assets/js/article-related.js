// 個別記事ページ共通:「同じテーマの記事」「サイドバーの最新記事」を自動描画する
//
// 関連記事の選び方(2026-09-12に作り直した)
//   もとは「同じタグを持つ記事」を新しい順に5本並べていた。
//   ところがタグは12種類しかなく、「まちづくり」だけで62本ある。
//   だから、どの記事を開いても、下に並ぶ5本がほぼ同じだった。
//   いまは tools/make_related.py が本文の言葉から近さを測った地図
//   (assets/js/related-map.js)を使い、共通する言葉も横に出す。
//   なぜ関連なのかが見えるので、並びが行き当たりばったりに見えない。
//   地図が読めなかったときだけ、昔のタグ方式に戻る。
//
// 並び順・日付表示について:
//   掲載日(date)は記事の多くが同じ日に集まっているため、
//   これで並べても順序に意味がなく、日付を出すと同じ数字が縦に並ぶだけになる。
//   参照した資料そのものの日付(sourceDate)で並べ、その日付を出す。
//   資料に日付が無い記事は、日付を出さずに後ろへ回す。

(function () {
  var mapReady = false, domReady = false;

  // 関連の地図を読みに行く。記事HTML 259本すべてに script タグを足して回らずに
  // 済ませるため、この中から読み込む。読めなくても記事は壊れない。
  var me = document.currentScript;
  if (typeof OZU_RELATED !== "undefined") {
    mapReady = true;
  } else if (me && me.src) {
    var s = document.createElement("script");
    s.src = me.src.replace(/article-related\.js(\?.*)?$/, "related-map.js");
    s.onload = s.onerror = function () { mapReady = true; boot(); };
    document.head.appendChild(s);
  } else {
    mapReady = true;
  }

  document.addEventListener("DOMContentLoaded", function () {
    domReady = true;
    boot();
  });

  function boot() {
    if (!mapReady || !domReady) return;
    if (typeof OZU_NEWS === "undefined") return;

    var slugEl = document.querySelector("[data-slug]");
    var currentSlug = slugEl ? slugEl.dataset.slug : null;
    var current = OZU_NEWS.filter(function (i) { return i.slug === currentSlug; })[0];
    var others = OZU_NEWS.filter(function (i) { return i.slug !== currentSlug; });

    function bySourceDate(list) {
      var withDate = list.filter(function (i) { return i.sourceDate; });
      var without = list.filter(function (i) { return !i.sourceDate; });
      withDate.sort(function (a, b) { return a.sourceDate < b.sourceDate ? 1 : -1; });
      return withDate.concat(without);
    }

    function dateLabel(item) {
      if (!item.sourceDate) return "";
      var p = item.sourceDate.split("-");
      // 資料の日付は「月まで」しか分からないものが多く、その場合は1日を入れてある。
      // 1日のものは年月までの表示にして、無い精度を装わない。
      return p[2] === "01" ? p[0] + "." + p[1] : p[0] + "." + p[1] + "." + p[2];
    }

    var sorted = bySourceDate(others);

    function row(item, dateFirst) {
      var d = dateLabel(item);
      var date = d ? '<span class="rdate">' + d + "</span>" : "";
      var link = '<a href="' + item.slug + '.html">' + item.title + "</a>";
      return "<li>" + (dateFirst ? date + link : link + date) + "</li>";
    }

    // ── 同じテーマの記事 ──────────────────────────────
    var list = document.getElementById("related-list-items");
    if (list) {
      var map = (typeof OZU_RELATED !== "undefined" && currentSlug)
        ? OZU_RELATED[currentSlug] : null;

      if (map && map.length) {
        // 地図の1件は [行き先のパス, 共通する言葉] か
        // [行き先のパス, 共通する言葉, 題](自由研究・読書のときだけ題が入る)
        var titleOf = {};
        OZU_NEWS.forEach(function (i) { titleOf[i.slug] = i.title; });
        list.innerHTML = map.map(function (r) {
          var path = r[0], why = r[1], title = r[2];
          if (!title) {
            title = titleOf[path.replace(/^.*\//, "").replace(/\.html$/, "")];
          }
          if (!title) return "";
          // 記事ページはサイトの1つ下の階層にあるので、上へ戻ってから降りる
          var why_html = why
            ? '<span class="rwhy">' + why.slice(0, 7) + "</span>" : "";
          return "<li>" + why_html + '<a href="../' + path + '">' + title + "</a></li>";
        }).join("");
      } else {
        // 地図が無いときの逃げ道。同じタグの記事を優先して日付順に並べる
        var related = sorted;
        if (current && current.tags && current.tags.length) {
          var tagged = sorted.filter(function (i) {
            return (i.tags || []).some(function (t) { return current.tags.indexOf(t) >= 0; });
          });
          var untagged = sorted.filter(function (i) { return tagged.indexOf(i) < 0; });
          related = tagged.concat(untagged);
        }
        list.innerHTML = related.slice(0, 5).map(function (i) { return row(i, true); }).join("");
      }
    }

    var sidebarList = document.getElementById("sidebar-latest-list");
    if (sidebarList) {
      sidebarList.innerHTML = sorted.slice(0, 6).map(function (i) { return row(i, false); }).join("");
    }
  }
})();
