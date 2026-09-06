const fs = require("fs"), path = require("path");
function load(p) { eval(fs.readFileSync(p, "utf8").replace(/^const /gm, "globalThis.")); }
load("assets/js/photos-data.js");
load("assets/js/article-images.js");

const files = fs.readdirSync("eachnews").filter(f => f.endsWith(".html"));
let heroOnly = [], both = [], mapOnly = [], neither = [];
files.forEach(f => {
  const slug = f.replace(/\.html$/, "");
  const html = fs.readFileSync(path.join("eachnews", f), "utf8");
  const m = html.match(/<figure class="article-hero-img">[\s\S]*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"/);
  const mapped = OZU_ARTICLE_IMAGES[slug];
  if (m && mapped) both.push([slug, m[1].replace("../assets/img/", ""), m[2], mapped.file]);
  else if (m) heroOnly.push([slug, m[1].replace("../assets/img/", ""), m[2]]);
  else if (mapped) mapOnly.push(slug);
  else neither.push(slug);
});
console.log("既存ヒーロー画像あり & 割り当てあり:", both.length);
both.forEach(r => {
  const same = r[1] === r[3];
  console.log(" ", same ? "同じ" : "差替", r[0], "|", r[1], "「" + r[2] + "」", same ? "" : "→ " + r[3]);
});
console.log("\n既存ヒーローのみ(割り当て無し):", heroOnly.length);
heroOnly.forEach(r => console.log("  ", r[0], "|", r[1], "「" + r[2] + "」"));
console.log("\n割り当てのみ(ヒーロー無し):", mapOnly.length);
console.log("どちらも無し:", neither.length);
