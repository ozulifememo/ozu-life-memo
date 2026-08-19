const fs = require("fs");
eval(fs.readFileSync("assets/js/photos-data.js", "utf8").replace(/^const /gm, "globalThis."));
console.log("台帳件数:", OZU_PHOTO_LIBRARY.length);
console.log("記事に使える:", OZU_PHOTO_USABLE.length, "/ 掲示物のみ:", OZU_PHOTO_LIBRARY.length - OZU_PHOTO_USABLE.length);
let miss = 0;
OZU_PHOTO_LIBRARY.forEach(function (p) {
  if (!fs.existsSync("assets/img/" + p.file)) { console.log("ファイル無し:", p.file); miss++; }
});
console.log("存在しないファイル:", miss);
const known = new Set(OZU_PHOTO_LIBRARY.map(function (p) { return p.file; }));
const disk = fs.readdirSync("assets/img").filter(function (f) { return /^real-photo-\d+\.jpg$/.test(f); })
  .concat(fs.readdirSync("assets/img/photos").filter(function (f) { return /\.jpg$/.test(f); })
    .map(function (f) { return "photos/" + f; }));
disk.forEach(function (f) { if (!known.has(f)) console.log("台帳もれ:", f); });
console.log("ディスク上の写真:", disk.length);
console.log("日本語チェック:", OZU_PHOTO_BY_FILE["photos/ozu-photo-78.jpg"].alt, "/", OZU_PHOTO_BY_FILE["photos/ozu-photo-17.jpg"].alt);
