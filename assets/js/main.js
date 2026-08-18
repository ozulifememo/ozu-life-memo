document.addEventListener("DOMContentLoaded", () => {
  // Mobile nav toggle
  const navToggle = document.querySelector(".nav-toggle");
  const mainNav = document.querySelector(".main-nav");
  if (navToggle && mainNav) {
    navToggle.addEventListener("click", () => {
      mainNav.classList.toggle("open");
    });
  }

  // Contact modal
  const modal = document.querySelector("[data-modal]");
  const openers = document.querySelectorAll("[data-modal-open]");
  const closers = document.querySelectorAll("[data-modal-close]");

  openers.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      modal?.classList.add("open");
    });
  });

  closers.forEach((btn) => {
    btn.addEventListener("click", () => modal?.classList.remove("open"));
  });

  modal?.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("open");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") modal?.classList.remove("open");
  });

  // Carousel
  const track = document.querySelector(".carousel-track");
  const prevBtn = document.querySelector("[data-carousel-prev]");
  const nextBtn = document.querySelector("[data-carousel-next]");
  const pauseBtn = document.querySelector("[data-carousel-pause]");

  if (track) {
    const scrollStep = () => track.clientWidth * 0.6;
    let autoplayId = null;
    let isPaused = false;

    const startAutoplay = () => {
      if (autoplayId) return;
      autoplayId = setInterval(() => {
        if (track.scrollLeft + track.clientWidth >= track.scrollWidth - 4) {
          track.scrollTo({ left: 0, behavior: "smooth" });
        } else {
          track.scrollBy({ left: scrollStep(), behavior: "smooth" });
        }
      }, 3500);
    };

    const stopAutoplay = () => {
      clearInterval(autoplayId);
      autoplayId = null;
    };

    startAutoplay();

    prevBtn?.addEventListener("click", () => {
      track.scrollBy({ left: -scrollStep(), behavior: "smooth" });
    });

    nextBtn?.addEventListener("click", () => {
      track.scrollBy({ left: scrollStep(), behavior: "smooth" });
    });

    pauseBtn?.addEventListener("click", () => {
      isPaused = !isPaused;
      pauseBtn.textContent = isPaused ? "▶" : "❚❚";
      if (isPaused) stopAutoplay();
      else startAutoplay();
    });
  }

  // News/Monthly category tab + tag chip + source-type chip filter
  const tabs = document.querySelectorAll(".news-tab");
  const tagChips = document.querySelectorAll("#tag-filter .tag-chip");
  const sourceChips = document.querySelectorAll("#source-filter .tag-chip");
  const rows = document.querySelectorAll(
    ".news-cards .news-card[data-category], .news-table .news-row[data-category], .monthly-list li[data-category]"
  );
  const monthlyCards = document.querySelectorAll(".monthly-card");

  let activeCategory = "all";
  let activeTag = "all";
  let activeSourceType = "all";

  // ?tag=観光 のようなURLで来たとき、該当のタグチップを自動選択する
  const presetTag = new URLSearchParams(location.search).get("tag");

  function applyNewsFilter() {
    rows.forEach((row) => {
      const categoryOk = activeCategory === "all" || row.dataset.category === activeCategory;
      const rowTags = (row.dataset.tags || "").split(",").filter(Boolean);
      const tagOk = activeTag === "all" || rowTags.includes(activeTag);
      const sourceOk = activeSourceType === "all" || row.dataset.sourceType === activeSourceType;
      row.style.display = categoryOk && tagOk && sourceOk ? "" : "none";
    });

    monthlyCards.forEach((card) => {
      const items = card.querySelectorAll("li[data-category]");
      if (items.length === 0) return;
      const hasVisible = [...items].some((li) => li.style.display !== "none");
      card.style.display = hasVisible ? "" : "none";
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activeCategory = tab.dataset.category;
      applyNewsFilter();
    });
  });

  tagChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      tagChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeTag = chip.dataset.tag;
      applyNewsFilter();
    });
  });

  if (presetTag) {
    const presetChip = [...tagChips].find((c) => c.dataset.tag === presetTag);
    if (presetChip) presetChip.click();
  }

  sourceChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      sourceChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeSourceType = chip.dataset.sourceType;
      applyNewsFilter();
    });
  });
});
