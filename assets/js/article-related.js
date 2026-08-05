// 個別記事ページ共通:「あわせて読みたい最新ニュース」を自動描画する
document.addEventListener("DOMContentLoaded", () => {
  const list = document.getElementById("related-list-items");
  if (!list || typeof OZU_NEWS === "undefined") return;

  const currentSlug = document.querySelector("[data-slug]")?.dataset.slug;

  const related = OZU_NEWS.filter((item) => item.slug !== currentSlug)
    .sort((a, b) => (a.date < b.date ? 1 : -1))
    .slice(0, 5);

  list.innerHTML = related
    .map(
      (item) => `
    <li>
      <span class="rdate">${item.date.replace(/-/g, "/")}</span>
      <a href="${item.slug}.html">${item.title}</a>
    </li>`
    )
    .join("");
});
