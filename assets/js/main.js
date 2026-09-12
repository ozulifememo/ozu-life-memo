/* 記事の題を、できるだけ横1行に収める(2026-09-12)
 *
 * 本人の指示:「タイトルは１行で横１列が理想！フォントサイズを小さくする、
 * １列ですべてを抑えるのが大事。」
 *
 * CSSだけでは行数を測れないので、ここで実際に測って字を詰める。
 * 本物のChromeで記事259本を測った結果(画面幅1280px・書体の読み込み後):
 *   何もしていなかったとき  1行  67本(26%)
 *   いま                    1行 219本(84%) / 2行 41本 / 3行以上 0本
 * 下限を21pxにしたのは、本文が16pxで、これ以上下げると題が本文と見分けにくく
 * なるため。残る41本は題そのものが長いので、収めるには題を短くするしかない
 * (公開済みの題を変えるのは本人の許可が要る)。
 *
 * 測るときの注意。**書体の読み込みを待ってから測ること。**
 * DOMContentLoadedの時点では代替フォントで組まれていて字幅が違う。
 * 待たずに測ると数字がずれるうえ、この処理自身も早く止まって2行のまま残る
 * (2026-09-12に実際そうなった。だから下で document.fonts.ready を待っている)。
 *
 * スマホ(幅700px未満)では詰めない。34字を1行に入れると11pxほどになり読めない。
 * 狭い画面では2〜3行で構わない。
 *
 * スクリプトは </body> の直前にあるので、この処理は最初の描画より前に走る。
 * だから28pxで出たあと縮む、というちらつきは起きない。 */
(function () {
  var FLOOR = 21, MIN_WIDTH = 700;
  var h = document.querySelector(".article-page h1, .jk-hero h1");
  if (!h) return;
  function lines() {
    var cs = getComputedStyle(h);
    var lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.4;
    return Math.round(h.getBoundingClientRect().height / lh);
  }
  function fit() {
    h.style.fontSize = "";
    if (window.innerWidth < MIN_WIDTH) return;
    var fs = parseFloat(getComputedStyle(h).fontSize);
    while (fs > FLOOR && lines() > 1) {
      fs -= 0.5;
      h.style.fontSize = fs + "px";
    }
  }
  fit();
  // 書体が届く前は代替フォントで組まれていて字幅が違う。そのままだと
  // 「収まった」と判断して途中で止まり、書体が来た瞬間に2行へ戻る。
  // 届いたらもう一度合わせる。
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(fit).catch(function () {});
  }
  var t;
  window.addEventListener("resize", function () {
    clearTimeout(t);
    t = setTimeout(fit, 150);
  });
})();

document.addEventListener("DOMContentLoaded", () => {
  // Mobile nav toggle
  const navToggle = document.querySelector(".nav-toggle");
  const mainNav = document.querySelector(".main-nav");
  if (navToggle && mainNav) {
    navToggle.addEventListener("click", () => {
      mainNav.classList.toggle("open");
    });
  }

  // Nav dropdown (タップ/クリックでも開閉できるように。hoverが効かないタッチ端末向け)
  const dropdowns = document.querySelectorAll(".nav-dropdown");
  dropdowns.forEach((dropdown) => {
    const trigger = dropdown.querySelector(".nav-dropdown-trigger");
    trigger?.addEventListener("click", (e) => {
      e.stopPropagation();
      const isOpen = dropdown.classList.contains("open");
      dropdowns.forEach((d) => d.classList.remove("open"));
      if (!isOpen) dropdown.classList.add("open");
    });
  });
  document.addEventListener("click", () => {
    dropdowns.forEach((d) => d.classList.remove("open"));
  });

  // Contact modal
  const modal = document.querySelector("[data-modal]");
  const openers = document.querySelectorAll("[data-modal-open]");
  const closers = document.querySelectorAll("[data-modal-close]");

  openers.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      modal?.classList.add("open");
      // スマホのドロワーから開いたとき、後ろに開いたまま残るドロワーを閉じる
      mainNav?.classList.remove("open");
    });
  });

  closers.forEach((btn) => {
    btn.addEventListener("click", () => modal?.classList.remove("open"));
  });

  modal?.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("open");
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      modal?.classList.remove("open");
      mainNav?.classList.remove("open");
    }
  });

  // ドロワーの外側(残り見えている本文)をタップしたら閉じる
  document.addEventListener("click", (e) => {
    if (!mainNav || !mainNav.classList.contains("open")) return;
    if (e.target.closest(".main-nav") || e.target.closest(".nav-toggle")) return;
    mainNav.classList.remove("open");
  });

  // Carousel
  const track = document.querySelector(".carousel-track");
  const prevBtn = document.querySelector("[data-carousel-prev]");
  const nextBtn = document.querySelector("[data-carousel-next]");
  const pauseBtn = document.querySelector("[data-carousel-pause]");

  if (track) {
    // 写真1枚分(gap込み)の幅ぴったりで動かす。scroll-snap-type:x mandatory と
    // 半端な量(clientWidthの割合など)を組み合わせると、ブラウザがスナップ位置に
    // 強制補正するたびに移動量がバラつき、動きがガタつく不具合があったための対応。
    const scrollStep = () => {
      const item = track.querySelector("img");
      if (!item) return track.clientWidth * 0.6;
      const gap = parseFloat(getComputedStyle(track).columnGap || "0") || 0;
      return item.getBoundingClientRect().width + gap;
    };
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
  // 記事一覧は並び替えのたびに作り直されるので、NodeListを最初に1回取ると
  // 古い要素を掴んだままになり絞り込みが効かなくなる。毎回引き直す。
  const ROW_SELECTOR =
    ".news-cards .news-card[data-category], .news-table .news-row[data-category], .monthly-list li[data-category]";
  const getRows = () => document.querySelectorAll(ROW_SELECTOR);
  const monthlyCards = document.querySelectorAll(".monthly-card");

  let activeCategory = "all";
  let activeTag = "all";
  let activeSourceType = "all";

  // ?tag=観光 のようなURLで来たとき、該当のタグチップを自動選択する
  const presetTag = new URLSearchParams(location.search).get("tag");

  function applyNewsFilter() {
    getRows().forEach((row) => {
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

  // 記事一覧ページの並び替えスクリプトから、再描画のあとに呼んでもらう
  window.ozuApplyNewsFilters = applyNewsFilter;

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

  // ── noteに転載した記事の案内 ───────────────────────
  // 台帳(news-data.js)の note: にURLが入っている記事だけ、出典欄のあとに1行出す。
  // 記事HTMLを1本ずつ手で直さなくてよいように、ここでまとめて面倒を見る。
  (function renderNoteCrosslink() {
    const page = document.querySelector(".article-page[data-slug]");
    if (!page || typeof OZU_NEWS === "undefined") return;
    const item = OZU_NEWS.find((n) => n.slug === page.dataset.slug);
    if (!item || !item.note) return;
    const p = document.createElement("p");
    p.className = "note-crosslink";
    const a = document.createElement("a");
    a.href = item.note;
    a.target = "_blank";
    a.rel = "noopener";
    a.textContent = "noteにも掲載しています";
    p.append("この記事は ", a, "。");
    const related = page.querySelector(".related-list");
    if (related) related.parentNode.insertBefore(p, related);
    else page.appendChild(p);
  })();
});
