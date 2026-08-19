(function () {
  function buildHeader(prefix) {
    var home = prefix === "" ? "./" : prefix;
    return (
      '<div class="wrap">' +
      '<a href="' + home + '" class="logo">OZU LIFE MEMO</a>' +
      '<nav class="main-nav">' +
      '<a href="' + home + '">HOME</a>' +
      '<a href="' + prefix + 'concept/">サイト紹介</a>' +
      '<a href="' + prefix + 'link/">リンク集</a>' +
      '<div class="nav-dropdown">' +
      '<button type="button" class="nav-dropdown-trigger">読み物<span class="nav-caret">▾</span></button>' +
      '<div class="nav-dropdown-menu">' +
      '<a href="' + prefix + 'news/">大洲ノート</a>' +
      '<a href="' + prefix + 'monthly/">月間まとめ</a>' +
      '<a href="' + prefix + 'history/">大洲の歴史</a>' +
      '<a href="' + prefix + 'book/">大洲と読書</a>' +
      "</div>" +
      "</div>" +
      '<a href="' + prefix + 'photo/">フリー写真</a>' +
      '<a href="' + prefix + 'map/">大洲の地図</a>' +
      '<div class="nav-dropdown">' +
      '<button type="button" class="nav-dropdown-trigger">遊ぶ<span class="nav-caret">▾</span></button>' +
      '<div class="nav-dropdown-menu">' +
      '<a href="' + prefix + 'quiz/">大洲検定</a>' +
      '<a href="' + prefix + 'geoguess/">大洲ジオゲッサー</a>' +
      "</div>" +
      "</div>" +
      '<a href="' + prefix + 'interview/">大洲のとなり人</a>' +
      '<a href="#" class="cta-btn" data-modal-open>お問い合わせ</a>' +
      "</nav>" +
      '<button class="nav-toggle" aria-label="メニューを開く"><span></span></button>' +
      "</div>"
    );
  }

  var FOOTER_PLAIN =
    '<div class="wrap">' +
    "<p>OZU LIFE MEMO は個人運営の非公式サイトです。大洲市の公式情報ではありません。</p>" +
    "<p>&copy; 2026 OZU LIFE MEMO</p>" +
    "</div>";

  var FOOTER_ARTICLE =
    '<div class="wrap">' +
    "<p>OZU LIFE MEMO は個人運営の非公式サイトです。大洲市の公式情報ではありません。</p>" +
    '<p class="footer-feedback">この記事の内容に誤りや古い情報があれば、ぜひ教えてください。感想やご指摘も大歓迎です。 <a href="#" data-modal-open>お問い合わせはこちら</a></p>' +
    "<p>&copy; 2026 OZU LIFE MEMO</p>" +
    "</div>";

  var MODAL_HTML =
    '<div class="modal-box">' +
    '<button class="modal-close" data-modal-close aria-label="閉じる">&times;</button>' +
    "<h3>お問い合わせ・Googleフォームはこちら</h3>" +
    '<p class="modal-note">＼ 名前やメールアドレスの入力は一切不要です ／</p>' +
    '<p class="modal-warning">' +
    "<strong>【非公式・個人ボランティアです】</strong>" +
    "制度の詳細は必ず公式HPを確認してください。情報のまとめ・感想は個人の見解です。" +
    "</p>" +
    '<a href="https://docs.google.com/forms/d/e/1FAIpQLSfevBytb8aZmkEUX9m5aC0EUHxDmmYM0jYog33aPFr8AT_OEA/viewform?usp=dialog" class="form-btn" target="_blank" rel="noopener">Google フォーム</a>' +
    "</div>";

  function markCurrentNav() {
    var here = location.pathname.replace(/index\.html$/, "");
    var links = document.querySelectorAll(".main-nav a[href]");
    links.forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href || href === "#") return;
      try {
        var resolved = new URL(href, location.href).pathname.replace(/index\.html$/, "");
        if (resolved === here) {
          a.classList.add("current");
          var dropdown = a.closest(".nav-dropdown");
          if (dropdown) dropdown.querySelector(".nav-dropdown-trigger").classList.add("current");
        }
      } catch (e) {}
    });
  }

  var headerEl = document.querySelector("[data-site-header]");
  if (headerEl) {
    headerEl.outerHTML =
      '<header class="site-header">' + buildHeader(headerEl.getAttribute("data-prefix") || "") + "</header>";
  }

  var footerEl = document.querySelector("[data-site-footer]");
  if (footerEl) {
    var variant = footerEl.getAttribute("data-site-footer");
    footerEl.outerHTML =
      '<footer class="site-footer">' + (variant === "article" ? FOOTER_ARTICLE : FOOTER_PLAIN) + "</footer>";
  }

  var modalEl = document.querySelector("[data-site-modal]");
  if (modalEl) {
    modalEl.outerHTML = '<div class="modal-overlay" data-modal>' + MODAL_HTML + "</div>";
  }

  markCurrentNav();
})();
