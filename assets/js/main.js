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

  // News category tab filter
  const tabs = document.querySelectorAll(".news-tab");
  const rows = document.querySelectorAll(".news-cards .news-card[data-category]");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const category = tab.dataset.category;

      rows.forEach((row) => {
        if (category === "all" || row.dataset.category === category) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  });
});
