// 記事ページ(eachnews/*.html)の体裁をそろえる。何度実行してもよい。
//
//  1. メイン写真を article-images.js の割り当てに合わせる
//     (割り当てが無い記事は写真を出さない。ランダム写真は廃止)
//  2. 記事末尾のランダム写真を削除する
//  3. 出典ボックスを本文の先頭から末尾へ移す
//  4. 冒頭の日付行を「カテゴリ ・ 出典 ・ 出典の日付」に統一する
//     (掲載日は129本中78本が同じ日で意味を持たないため、末尾の出典欄に小さく出す)
//
// 使い方:  node tools/fix-articles.js          … 全記事に適用
//          node tools/fix-articles.js --dry    … 変更内容だけ表示
//          node tools/fix-articles.js <slug>   … 1本だけ

const fs = require("fs");
const path = require("path");

function load(p) { eval(fs.readFileSync(p, "utf8").replace(/^const /gm, "globalThis.")); }
load("assets/js/photos-data.js");
load("assets/js/article-images.js");
load("assets/js/news-data.js");

const NEWS_BY_SLUG = {};
OZU_NEWS.forEach(function (a) { NEWS_BY_SLUG[a.slug] = a; });

const args = process.argv.slice(2);
const dry = args.includes("--dry");
const only = args.filter(function (a) { return !a.startsWith("--"); })[0];

function esc(s) {
  return String(s).replace(/[&<>"]/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
  });
}

function jpDate(iso) {
  const p = iso.split("-");
  return p[0] + "年" + Number(p[1]) + "月" + Number(p[2]) + "日";
}

// ── 1. メイン写真 ──────────────────────────────────
function fixHero(html, slug) {
  const entry = OZU_ARTICLE_IMAGES[slug];
  const heroRe = /[ \t]*<figure class="article-hero-img">[\s\S]*?<\/figure>\r?\n?/;

  if (!entry) {
    // 割り当てが無い記事は、内容と関係ない写真を残さない
    return html.replace(heroRe, "");
  }

  const meta = OZU_PHOTO_BY_FILE[entry.file];
  const alt = entry.caption || (meta ? meta.alt : "大洲市内で撮影した写真");
  const figure =
    '    <figure class="article-hero-img">\n' +
    '      <img src="../assets/img/' + entry.file + '" alt="' + esc(alt) +
    '" width="1200" height="750" fetchpriority="high" decoding="async">\n' +
    "      <figcaption>" + esc(alt) + "（撮影: OZU LIFE MEMO）</figcaption>\n" +
    "    </figure>\n";

  if (heroRe.test(html)) return html.replace(heroRe, figure);

  // まだ写真が無い記事は h1 の直後に入れる
  return html.replace(/(<h1[^>]*>[\s\S]*?<\/h1>\r?\n)/, "$1\n" + figure);
}

// ── 2. ランダム写真を消す ───────────────────────────
function removeRandomPhoto(html) {
  return html
    .replace(/[ \t]*<figure class="article-random-photo">[\s\S]*?<\/figure>\r?\n?/g, "")
    .replace(/[ \t]*<script src="\.\.\/assets\/js\/random-photo\.js"><\/script>\r?\n?/g, "");
}

// ── 3. 出典ボックスを末尾へ ─────────────────────────
function moveSourceBox(html, slug) {
  const m = html.match(/[ \t]*<div class="content-block source-box">[\s\S]*?<\/div>\r?\n?/);
  if (!m) return html;
  let box = m[0];
  html = html.replace(box, "");

  // 見出しを「出典・参考にした資料」に統一し、掲載日を1行添える
  box = box.replace(/<h2[^>]*>[\s\S]*?<\/h2>/, '<h2 class="source-box-title">出典・参考にした資料</h2>');
  const item = NEWS_BY_SLUG[slug];
  if (item && !/source-box-posted/.test(box)) {
    box = box.replace(
      /(\r?\n[ \t]*)<\/div>\r?\n?$/,
      '$1  <p class="source-box-posted">この記事をサイトに掲載した日: ' +
        item.date.replace(/-/g, "/") + "</p>$1</div>\n"
    );
  }

  // 「あわせて読みたい」の直前に置く。無ければ本文の最後に置く。
  if (/<div class="related-list">/.test(html)) {
    return html.replace(/([ \t]*)<div class="related-list">/, box + "$1<div class=\"related-list\">");
  }
  return html.replace(/([ \t]*)<\/div>\r?\n([ \t]*)<aside class="article-sidebar">/, box + "$1</div>\n$2<aside class=\"article-sidebar\">");
}

// ── 4. 冒頭の日付行 ───────────────────────────────
// 元の行は「掲載日 ・ カテゴリ ・ 出典: …」という並び。
// 掲載日は129本中78本が同じ日で、先頭に置く意味が無い(むしろ
// 「全部同じ日に量産した」ようにしか見えない)ので先頭から外す。
// ただし出典の書き方は記事ごとに手で書き分けられている(号数など)ので、
// 作り直さずに、並べ替えと目印付けだけを行う。
function fixDateLine(html, slug) {
  const item = NEWS_BY_SLUG[slug];
  return html.replace(/<p class="article-date">([\s\S]*?)<\/p>/, function (whole, inner) {
    let text = inner.trim();
    if (/article-cat/.test(text)) return whole; // 変換済み

    // 先頭の掲載日を落とす
    text = text.replace(/^\s*\d{4}\/\d{2}\/\d{2}\s*[・･]\s*/, "");

    // カテゴリ名に目印を付ける
    const cat = item ? OZU_CATEGORY_LABELS[item.category] : null;
    if (cat && text.indexOf(cat) === 0) {
      text = '<span class="article-cat">' + cat + "</span>" + text.slice(cat.length);
    }

    // 「（情報源日付: 2005/01）」を、読みやすい表記の小さな部品にする
    text = text.replace(/（情報源日付:\s*([0-9]{4})\/([0-9]{2})(?:\/([0-9]{2}))?）/, function (m, y, mo, d) {
      const label = y + "年" + Number(mo) + "月" + (d ? Number(d) + "日" : "");
      return ' <span class="article-srcdate">' + label + "の資料</span>";
    });

    return '<p class="article-date">' + text + "</p>";
  });
}

// ── 実行 ─────────────────────────────────────────
const files = fs.readdirSync("eachnews")
  .filter(function (f) { return f.endsWith(".html"); })
  .filter(function (f) { return !only || f === only + ".html"; });

let changed = 0, heroSet = 0, heroRemoved = 0, randomRemoved = 0, boxMoved = 0;

files.forEach(function (f) {
  const slug = f.replace(/\.html$/, "");
  const file = path.join("eachnews", f);
  const before = fs.readFileSync(file, "utf8");
  let html = before;

  const hadRandom = /article-random-photo/.test(html);
  const boxAtTop = /source-box[\s\S]*?class="commentary"/.test(html);

  html = removeRandomPhoto(html);
  html = fixHero(html, slug);
  html = moveSourceBox(html, slug);
  html = fixDateLine(html, slug);

  if (hadRandom) randomRemoved++;
  if (boxAtTop) boxMoved++;
  if (OZU_ARTICLE_IMAGES[slug]) heroSet++; else if (/article-hero-img/.test(before)) heroRemoved++;

  if (html !== before) {
    changed++;
    if (!dry) fs.writeFileSync(file, html, "utf8");
  }
});

console.log(
  (dry ? "[確認のみ] " : "") +
  "対象 " + files.length + "本 / 変更 " + changed + "本 / 写真を設定 " + heroSet +
  " / 内容と合わない写真を削除 " + heroRemoved +
  " / ランダム写真を削除 " + randomRemoved +
  " / 出典を末尾へ " + boxMoved
);
