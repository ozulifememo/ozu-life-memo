const fs = require("fs");
function load(p) { eval(fs.readFileSync(p, "utf8").replace(/^const /gm, "globalThis.")); }
load("assets/js/photos-data.js");
load("assets/js/article-images.js");
load("assets/js/news-data.js");
const picks = OZU_NEWS.filter(function (a) { return a.pick; });
console.log("pick記事:", picks.length, "本");
picks.forEach(function (a, i) {
  const im = OZU_ARTICLE_IMAGES[a.slug];
  console.log((i + 1) + ". [" + (im ? "写真:" + im.file.replace("photos/", "") : "写真なし") + "] " + a.title);
  if (a.pickNote) console.log("     note: " + a.pickNote);
});
const withImg = picks.filter(function (a) { return OZU_ARTICLE_IMAGES[a.slug]; }).length;
console.log("\npickのうち写真あり:", withImg, "/", picks.length);
// sourceDate の保有率
const sd = OZU_NEWS.filter(function (a) { return a.sourceDate; }).length;
console.log("sourceDateあり:", sd, "/", OZU_NEWS.length);
const kinds = {};
OZU_NEWS.forEach(function (a) { if (a.sourceDateKind) kinds[a.sourceDateKind] = (kinds[a.sourceDateKind] || 0) + 1; });
console.log("sourceDateKind:", JSON.stringify(kinds));
