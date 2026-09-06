// 記事カードの共通描画。トップページとニュース一覧で同じ見た目を使う。
//
// 読み込み順: photos-data.js → article-images.js → news-data.js → このファイル
//
// prefix … そのページから見たサイトルートまでの相対パス("" か "../")

(function (global) {
  "use strict";

  var MONTHS = "年";

  // ── 写真 ──────────────────────────────────────────
  // 記事にひもづいた写真を返す。無ければ null(ランダムな写真は絶対に出さない)。
  function articlePhoto(slug, prefix) {
    if (typeof OZU_ARTICLE_IMAGES === "undefined") return null;
    var entry = OZU_ARTICLE_IMAGES[slug];
    if (!entry) return null;
    var meta = typeof OZU_PHOTO_BY_FILE !== "undefined" ? OZU_PHOTO_BY_FILE[entry.file] : null;
    return {
      src: (prefix || "") + "assets/img/" + entry.file,
      // 一覧カード・サムネイル用の軽量版(横720px、元の1/4程度の重さ)。
      // assets/img/thumbs/ 以下に元と同じ相対パスで置いてある。
      // スマホ回線で一覧を開いたときに、元サイズ(200〜600KB)を
      // 何十枚も読ませないための仕組み。
      thumbSrc: (prefix || "") + "assets/img/thumbs/" + entry.file,
      alt: entry.caption || (meta ? meta.alt : "大洲市内で撮影した写真"),
      caption: entry.caption || (meta ? meta.alt : "")
    };
  }

  // ── 日付 ──────────────────────────────────────────
  // 掲載日(date)は129記事のうち78件が同じ日に集まっていて、並べても意味がない。
  // 表に出すのは「出典そのものの日付」にする。出典に日付が無い記事は日付を出さない。
  function sourceDateLabel(item) {
    if (!item.sourceDate) return "";
    var p = item.sourceDate.split("-");
    var kind = item.sourceDateKind || "";
    return p[0] + MONTHS + Number(p[1]) + "月" + Number(p[2]) + "日" + (kind ? "  " + kind : "");
  }

  // 一覧の「いつの話か」を短く出す用(年月まで)
  function sourceYearMonth(item) {
    if (!item.sourceDate) return "";
    var p = item.sourceDate.split("-");
    return p[0] + "." + p[1];
  }

  // 一覧に縦に並べる用。年月だけだと同じ表示が続いてしまうので日まで出す。
  function sourceYmd(item) {
    if (!item.sourceDate) return "";
    return item.sourceDate.replace(/-/g, ".");
  }

  function categoryLabel(item) {
    return typeof OZU_CATEGORY_LABELS !== "undefined" ? OZU_CATEGORY_LABELS[item.category] || "" : "";
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // ── 並び順 ─────────────────────────────────────────
  // 出典の日付が新しい順。日付が無い記事は後ろへ。
  function bySourceDateDesc(list) {
    var withDate = list.filter(function (i) { return i.sourceDate; });
    var without = list.filter(function (i) { return !i.sourceDate; });
    withDate.sort(function (a, b) { return a.sourceDate < b.sourceDate ? 1 : -1; });
    return withDate.concat(without);
  }

  // ── カード ─────────────────────────────────────────
  // 写真のある記事は写真つき、無い記事は文字だけ。
  // 文字だけのカードも「そういうデザイン」に見えるよう、別クラスで作り分ける。
  function storyCard(item, prefix, opts) {
    opts = opts || {};
    var photo = articlePhoto(item.slug, prefix);
    var href = (prefix || "") + "eachnews/" + item.slug + ".html";
    var note = opts.showNote && item.pickNote ? item.pickNote : "";
    var ym = sourceYearMonth(item);

    // 写真のあるカードと無いカードが混ざると、写真の高さの分だけ
    // 文字の開始位置がずれて一覧がガタガタになる。
    // 写真が無いときは同じ大きさの色面を置き、カテゴリ名を大きく入れて
    // 「そういうカード」として成立させる(欠けた枠には見せない)。
    var media = photo
      ? '<div class="story-media"><img src="' + photo.thumbSrc + '" alt="' + escapeHtml(photo.alt) +
        '" loading="lazy" decoding="async"></div>'
      : '<div class="story-media story-media--none"><span>' + escapeHtml(categoryLabel(item)) + "</span></div>";

    return (
      '<a class="story-card' + (photo ? "" : " story-card--textonly") + '" href="' + href + '"' +
      ' data-category="' + item.category + '">' +
      media +
      '<div class="story-body">' +
      '<span class="story-cat">' + escapeHtml(categoryLabel(item)) + "</span>" +
      '<h3 class="story-title">' + escapeHtml(item.title) + "</h3>" +
      (note ? '<p class="story-note">' + escapeHtml(note) + "</p>" : "") +
      '<span class="story-meta">' + escapeHtml(item.source) + (ym ? '<span class="story-ym">' + ym + "</span>" : "") + "</span>" +
      "</div></a>"
    );
  }

  // 主役記事のカード1枚。variant は "main"(1面トップ・大) か "sub"(サブ・中)。
  function leadCard(item, prefix, variant) {
    var photo = articlePhoto(item.slug, prefix);
    var href = (prefix || "") + "eachnews/" + item.slug + ".html";
    var isMain = variant === "main";
    // トップの大写真は画質優先で元サイズ+先読み。サブ2本は軽量サムネイルで十分。
    var img = photo
      ? '<div class="lead-media"><img src="' + (isMain ? photo.src : photo.thumbSrc) +
        '" alt="' + escapeHtml(photo.alt) +
        (isMain
          ? '" width="1200" height="675" fetchpriority="high" decoding="async">'
          : '" loading="lazy" decoding="async">') +
        "</div>"
      : "";
    return (
      '<a class="lead-story lead-story--' + variant + (photo ? "" : " lead-story--textonly") +
      '" href="' + href + '" data-category="' + item.category + '">' +
      img +
      '<div class="lead-body">' +
      '<span class="story-cat">' + escapeHtml(categoryLabel(item)) + "</span>" +
      (isMain ? '<h2 class="lead-story-title">' : '<h3 class="lead-story-title lead-story-title--sub">') +
      escapeHtml(item.title) +
      (isMain ? "</h2>" : "</h3>") +
      (isMain && item.pickNote ? '<p class="lead-note">' + escapeHtml(item.pickNote) + "</p>" : "") +
      '<span class="story-meta">' + escapeHtml(item.source) +
      (sourceYearMonth(item) ? '<span class="story-ym">' + sourceYearMonth(item) + "</span>" : "") +
      "</span>" +
      "</div></a>"
    );
  }

  // 主役ブロック(新聞の1面のイメージ)。
  // 1本目を大きく、2〜3本目を右の列(スマホでは下)に並べる。
  // 「主役が1本だけだとトップの顔が毎回同じに見える」という本人の指摘で
  // 3本構成にした(2026-08-20)。
  function leadGrid(items, prefix) {
    if (!items || !items.length) return "";
    var main = leadCard(items[0], prefix, "main");
    var subs = items.slice(1).map(function (i) { return leadCard(i, prefix, "sub"); }).join("");
    return (
      '<div class="lead-grid">' +
      '<div class="lead-main">' + main + "</div>" +
      (subs ? '<div class="lead-side">' + subs + "</div>" : "") +
      "</div>"
    );
  }

  global.OzuCard = {
    articlePhoto: articlePhoto,
    sourceDateLabel: sourceDateLabel,
    sourceYearMonth: sourceYearMonth,
    sourceYmd: sourceYmd,
    bySourceDateDesc: bySourceDateDesc,
    storyCard: storyCard,
    leadGrid: leadGrid,
    escapeHtml: escapeHtml
  };
})(window);
