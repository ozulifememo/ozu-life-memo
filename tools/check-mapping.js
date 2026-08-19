const fs = require("fs");
function load(p) { eval(fs.readFileSync(p, "utf8").replace(/^const /gm, "globalThis.")); }
load("assets/js/photos-data.js");
load("assets/js/article-images.js");
load("assets/js/news-data.js");

const slugs = new Set(OZU_NEWS.map(function (a) { return a.slug; }));
const mapped = Object.keys(OZU_ARTICLE_IMAGES);
let bad = 0;

console.log("記事総数:", OZU_NEWS.length);
console.log("写真あり:", mapped.length);

mapped.forEach(function (s) {
  if (!slugs.has(s)) { console.log("!! 存在しない記事slug:", s); bad++; }
  const f = OZU_ARTICLE_IMAGES[s].file;
  if (!OZU_PHOTO_BY_FILE[f]) { console.log("!! 台帳に無い写真:", s, f); bad++; }
  else if (OZU_PHOTO_BY_FILE[f].board) { console.log("!! 掲示物写真を使っている:", s, f); bad++; }
  if (!fs.existsSync("assets/img/" + f)) { console.log("!! 画像ファイル無し:", s, f); bad++; }
});

// 撮影待ちリストの slug 検証
const wantedSlugs = [];
OZU_ARTICLE_PHOTO_WANTED.forEach(function (w) {
  w.slugs.forEach(function (s) {
    wantedSlugs.push(s);
    if (!slugs.has(s)) { console.log("!! 撮影リストに存在しない記事slug:", w.theme, s); bad++; }
    if (OZU_ARTICLE_IMAGES[s]) { console.log("!! 写真ありなのに撮影リストにも載っている:", s); bad++; }
  });
});
const dupW = wantedSlugs.filter(function (s, i) { return wantedSlugs.indexOf(s) !== i; });
if (dupW.length) console.log("!! 撮影リスト内で重複:", [...new Set(dupW)].join(", "));

// どこにも載っていない記事
const orphan = OZU_NEWS.filter(function (a) {
  return !OZU_ARTICLE_IMAGES[a.slug] && wantedSlugs.indexOf(a.slug) === -1;
});
console.log("撮影待ち記事:", new Set(wantedSlugs).size);
console.log("未分類(写真もなく撮影リストにも無い):", orphan.length);
orphan.forEach(function (a) { console.log("   -", a.slug, "|", a.title); });

// 同じ写真の使い回し回数
const count = {};
mapped.forEach(function (s) { const f = OZU_ARTICLE_IMAGES[s].file; count[f] = (count[f] || 0) + 1; });
const heavy = Object.entries(count).filter(function (e) { return e[1] >= 4; }).sort(function (a, b) { return b[1] - a[1]; });
console.log("\n4回以上使い回している写真:");
heavy.forEach(function (e) { console.log("   ", e[1] + "回", e[0], "-", OZU_PHOTO_BY_FILE[e[0]].alt); });

console.log("\n使っていない写真:", OZU_PHOTO_USABLE.filter(function (p) { return !count[p.file]; }).length, "枚");
console.log(bad === 0 ? "\n=> 整合性チェック OK" : "\n=> 問題 " + bad + " 件");
