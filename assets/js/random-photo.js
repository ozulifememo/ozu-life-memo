document.addEventListener("DOMContentLoaded", () => {
  if (typeof OZU_PHOTOS === "undefined" || OZU_PHOTOS.length === 0) return;

  document.querySelectorAll("[data-random-photo]").forEach((el) => {
    const base = el.dataset.photoBase || "";
    const file = OZU_PHOTOS[Math.floor(Math.random() * OZU_PHOTOS.length)];
    el.src = base + file;
  });
});
