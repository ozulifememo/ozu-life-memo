// 個別記事ページ共通:「あわせて読みたい記事」「サイドバーの最新記事」を自動描画する
//
// 並び順・日付表示について:
//   掲載日(date)は129記事のうち78件が同じ日に集まっているため、
//   これで並べても順序に意味がなく、日付を出すと同じ数字が縦に並ぶだけになる。
//   参照した資料そのものの日付(sourceDate)で並べ、その日付を出す。
//   資料に日付が無い記事は、日付を出さずに後ろへ回す。
//
// 関連記事は「同じタグを持つ記事」を優先する。
// これまでは全記事から日付順に5本取っていたので、どの記事を開いても
// ほぼ同じ5本が並んでいた。

document.addEventListener("DOMContentLoaded", function () {
  if (typeof OZU_NEWS === "undefined") return;

  var currentSlug = document.querySelector("[data-slug]") ? document.querySelector("[data-slug]").dataset.slug : null;
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

  // ── あわせて読みたい: 同じタグの記事を優先する ──────────
  var related = sorted;
  if (current && current.tags && current.tags.length) {
    var tagged = sorted.filter(function (i) {
      return (i.tags || []).some(function (t) { return current.tags.indexOf(t) >= 0; });
    });
    var untagged = sorted.filter(function (i) { return tagged.indexOf(i) < 0; });
    related = tagged.concat(untagged);
  }

  function row(item, dateFirst) {
    var d = dateLabel(item);
    var date = d ? '<span class="rdate">' + d + "</span>" : "";
    var link = '<a href="' + item.slug + '.html">' + item.title + "</a>";
    return "<li>" + (dateFirst ? date + link : link + date) + "</li>";
  }

  var list = document.getElementById("related-list-items");
  if (list) {
    list.innerHTML = related.slice(0, 5).map(function (i) { return row(i, true); }).join("");
  }

  var sidebarList = document.getElementById("sidebar-latest-list");
  if (sidebarList) {
    sidebarList.innerHTML = sorted.slice(0, 6).map(function (i) { return row(i, false); }).join("");
  }
});
