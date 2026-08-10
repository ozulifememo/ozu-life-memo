// 個別記事ページ共通:「あわせて読みたい最新ニュース」「サイドバーの最新記事」を自動描画する
document.addEventListener("DOMContentLoaded", () => {
  if (typeof OZU_NEWS === "undefined") return;

  const currentSlug = document.querySelector("[data-slug]")?.dataset.slug;
  const sorted = OZU_NEWS.filter((item) => item.slug !== currentSlug).sort((a, b) =>
    a.date < b.date ? 1 : -1
  );

  const list = document.getElementById("related-list-items");
  if (list) {
    list.innerHTML = sorted
      .slice(0, 5)
      .map(
        (item) => `
    <li>
      <span class="rdate">${item.date.replace(/-/g, "/")}</span>
      <a href="${item.slug}.html">${item.title}</a>
    </li>`
      )
      .join("");
  }

  const sidebarList = document.getElementById("sidebar-latest-list");
  if (sidebarList) {
    sidebarList.innerHTML = sorted
      .slice(0, 6)
      .map(
        (item) => `
    <li>
      <a href="${item.slug}.html">${item.title}</a>
      <span class="rdate">${item.date.replace(/-/g, "/")}</span>
    </li>`
      )
      .join("");
  }
});
