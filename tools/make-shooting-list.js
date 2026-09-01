// 「この記事に合う写真がまだ無い」一覧を撮影リストとして書き出す。
//   node tools/make-shooting-list.js
// → 撮影リスト.md を更新する。
//
// 写真を撮って photos-data.js と article-images.js を更新したあと、
// もう一度実行すれば、済んだテーマは自動で消える。

const fs = require("fs");
function load(p) { eval(fs.readFileSync(p, "utf8").replace(/^const /gm, "globalThis.")); }
load("assets/js/photos-data.js");
load("assets/js/article-images.js");
load("assets/js/news-data.js");

const BY_SLUG = {};
OZU_NEWS.forEach(function (a) { BY_SLUG[a.slug] = a; });

const total = OZU_NEWS.length;
const withPhoto = Object.keys(OZU_ARTICLE_IMAGES).filter(function (s) { return BY_SLUG[s]; }).length;

const themes = OZU_ARTICLE_PHOTO_WANTED
  .map(function (w) {
    // すでに写真が割り当てられた記事は落とす
    const waiting = w.slugs.filter(function (s) { return BY_SLUG[s] && !OZU_ARTICLE_IMAGES[s]; });
    return { theme: w.theme, subjects: w.subjects, waiting: waiting };
  })
  .filter(function (w) { return w.waiting.length > 0 || w.subjects.indexOf("急がない") >= 0 || w.waiting.length === 0; })
  .sort(function (a, b) { return b.waiting.length - a.waiting.length; });

const waitingTotal = new Set([].concat.apply([], themes.map(function (t) { return t.waiting; }))).size;

// どのテーマにも入っていない、写真なしの記事。
// テーマに登録しないかぎり撮影リストに一度も出てこないので、
// 新しく書いた記事が黙って写真待ちのまま埋もれる。ここで見えるようにする。
const IN_THEME = new Set([].concat.apply([], OZU_ARTICLE_PHOTO_WANTED.map(function (w) { return w.slugs; })));
const orphans = OZU_NEWS.filter(function (a) {
  return !OZU_ARTICLE_IMAGES[a.slug] && !IN_THEME.has(a.slug);
});

let out = [];
out.push("# 撮影リスト ｜ OZU LIFE MEMO");
out.push("");
out.push("記事の中身に合う写真がまだ無いものを、撮影テーマごとにまとめたものです。");
out.push("");
out.push("- 記事の総数: **" + total + "本**");
out.push("- 写真が付いている記事: **" + withPhoto + "本**");
out.push("- 写真待ちの記事: **" + waitingTotal + "本**");
out.push("- どのテーマにも入っていない記事: **" + orphans.length + "本**（下に一覧）");
out.push("- 手持ちの写真: **" + OZU_PHOTO_LIBRARY.length + "枚**（うち記事に使えるもの " + OZU_PHOTO_USABLE.length + "枚）");
out.push("");
out.push("写真待ちの記事は、いまサイト上では写真を出していません。");
out.push("内容と関係のない写真でごまかすより、空けておくほうがサイトの信用が保てるためです。");
out.push("");
out.push("---");
out.push("");
out.push("## 撮ってくるもの（待っている記事が多い順）");
out.push("");

themes.forEach(function (t, i) {
  out.push("### " + (i + 1) + ". " + t.theme + "　" + (t.waiting.length ? "（" + t.waiting.length + "本の記事が待っています）" : "（記事の指定なし・あると全体が良くなるもの）"));
  out.push("");
  out.push("**撮ってくるもの**: " + t.subjects);
  out.push("");
  if (t.waiting.length) {
    out.push("待っている記事:");
    out.push("");
    t.waiting.forEach(function (s) {
      out.push("- " + BY_SLUG[s].title);
    });
    out.push("");
  }
});

if (orphans.length) {
  out.push("---");
  out.push("");
  out.push("## どのテーマにも入っていない記事（" + orphans.length + "本）");
  out.push("");
  out.push("写真がなく、上のどのテーマにも入っていない記事です。");
  out.push("**このままだと撮影リストに出てこないので、いつまでも写真待ちのまま気づかれません。**");
  out.push("");
  out.push("`assets/js/article-images.js` の `OZU_ARTICLE_PHOTO_WANTED` で、合うテーマの `slugs` に足すか、");
  out.push("新しいテーマを作ってください。数字や制度の話だけで写真がいらない記事なら、放っておいて構いません。");
  out.push("");
  orphans.forEach(function (a) {
    out.push("- " + a.date + "　" + a.title + "　`" + a.slug + "`");
  });
  out.push("");
}

out.push("---");
out.push("");
out.push("## 撮ったあとの反映のしかた");
out.push("");
out.push("1. 写真を `assets/img/photos/` に入れる（ファイル名は `ozu-photo-83.jpg` のように続き番号で）");
out.push("2. `assets/js/photos-data.js` の台帳に1行足す");
out.push("");
out.push("   ```js");
out.push('   { file: "photos/ozu-photo-83.jpg", alt: "写っているものの説明", topics: ["空き家"] },');
out.push("   ```");
out.push("");
out.push("3. `assets/js/article-images.js` に、記事と写真のひもづけを足す");
out.push("");
out.push("   ```js");
out.push('   "akiya-taisaku-keikaku": { file: "photos/ozu-photo-83.jpg" },');
out.push("   ```");
out.push("");
out.push("4. その記事を `OZU_ARTICLE_PHOTO_WANTED` の `slugs` から外す");
out.push("5. 反映と確認");
out.push("");
out.push("   ```");
out.push("   node tools/check-mapping.js        # 整合性チェック");
out.push("   node tools/fix-articles.js         # 記事ページに写真を入れる");
out.push("   node tools/make-shooting-list.js   # このリストを更新");
out.push("   ```");
out.push("");
out.push("一覧ページ（トップ・大洲ノート）のサムネイルは、2の台帳と3のひもづけだけで自動的に出ます。");
out.push("");
out.push("## 撮るときの注意");
out.push("");
out.push("- 人の顔、表札、車のナンバーが写らない角度で撮る");
out.push("- 施設名の看板が一緒に写っていると、あとで何の写真か分からなくならずに済む");
out.push("- 横位置（3:2 か 16:9）で撮る。一覧のサムネイルは横長に切り抜かれる");
out.push("- 案内板や説明板そのものを主役にした写真は、掲示物の文章が第三者の著作物になるため、");
out.push("  記事のメイン写真には使わない運用にしている（台帳の `board: true`）");
out.push("");

fs.writeFileSync("撮影リスト.md", out.join("\n"), "utf8");
console.log("撮影リスト.md を書き出しました（テーマ " + themes.length + "件 / 写真待ちの記事 " + waitingTotal + "本）");
if (orphans.length) {
  console.log("どのテーマにも入っていない記事が " + orphans.length + "本あります。撮影リストの最後を見てください。");
}
