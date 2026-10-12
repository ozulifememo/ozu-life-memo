// タグ・カテゴリの色分け(大洲にちなんだ8色)。assets/css/style.cssの --color-tag-* と対応。
// 新しいタグ/カテゴリを追加したら、ここにも1行足す。
const OZU_TAG_COLOR_KEY = {
  "観光": "mikan",
  "まちづくり": "moss",
  "産業・農業": "gold",
  "財政・税金": "slate",
  "議会・行政": "indigo",
  "交通・インフラ": "teal",
  "人口減少": "slate",
  "防災": "kakishibu",
  "子育て・教育": "rose",
  "合併・地域": "gold",
  "空き家・住宅": "moss",
  "医療・福祉": "rose",
};

const OZU_CATEGORY_COLOR_KEY = { ima: "mikan", kurashi: "teal", shiten: "indigo" };

function ozuTagColorVar(tag) {
  const key = OZU_TAG_COLOR_KEY[tag];
  return key ? `var(--color-tag-${key})` : "var(--color-text-muted)";
}

function ozuCategoryColorVar(category) {
  const key = OZU_CATEGORY_COLOR_KEY[category];
  return key ? `var(--color-tag-${key})` : "var(--color-border-strong)";
}
