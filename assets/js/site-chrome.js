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
      '<a href="' + prefix + 'best/">おすすめ10選</a>' +
      '<a href="' + prefix + 'monthly/">月間まとめ</a>' +
      '<a href="' + prefix + 'history/">大洲の歴史</a>' +
      '<a href="' + prefix + 'book/">大洲と読書</a>' +
      '<a href="' + prefix + 'jiyu-kenkyu/">大洲の自由研究</a>' +
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

  // フッターは「2行だけ」だと、ページの終わりが唐突で作りかけに見える。
  // サイトの中身が一望できる索引として組み直した。
  // data-prefix はヘッダー側で持っているので、フッターも同じ値を使う。
  function buildFooter(prefix, variant) {
    var home = prefix === "" ? "./" : prefix;
    var cols =
      '<div class="footer-cols">' +
      '<div class="footer-col footer-col--about">' +
      '<p class="footer-logo">OZU LIFE MEMO</p>' +
      "<p>大洲市の非公式生活情報サイト。市役所や議会の硬い資料、SNSの断片的な話題を、" +
      "1人の市民の目線で読み解いています。</p>" +
      '<p class="footer-note">個人運営の非公式サイトです。大洲市の公式情報ではありません。' +
      "制度の詳細は必ず公式ホームページでご確認ください。</p>" +
      "</div>" +

      '<div class="footer-col">' +
      "<h3>読み物</h3>" +
      '<a href="' + prefix + 'news/">大洲ノート</a>' +
      '<a href="' + prefix + 'best/">おすすめ10選</a>' +
      '<a href="' + prefix + 'jiyu-kenkyu/">大洲の自由研究</a>' +
      '<a href="' + prefix + 'monthly/">月間まとめ</a>' +
      '<a href="' + prefix + 'history/">大洲の歴史</a>' +
      '<a href="' + prefix + 'book/">大洲と読書</a>' +
      '<a href="' + prefix + 'interview/">大洲のとなり人</a>' +
      "</div>" +

      '<div class="footer-col">' +
      "<h3>調べる・遊ぶ</h3>" +
      '<a href="' + prefix + 'map/">大洲の地図</a>' +
      '<a href="' + prefix + 'photo/">フリー写真</a>' +
      '<a href="' + prefix + 'link/">リンク集</a>' +
      '<a href="' + prefix + 'quiz/">大洲検定</a>' +
      '<a href="' + prefix + 'geoguess/">大洲ジオゲッサー</a>' +
      "</div>" +

      '<div class="footer-col">' +
      "<h3>このサイトについて</h3>" +
      '<a href="' + prefix + 'concept/">サイト紹介</a>' +
      '<a href="' + home + '">トップページ</a>' +
      '<a href="#" data-modal-open>お問い合わせ</a>' +
      "</div>" +
      "</div>";

    var feedback =
      variant === "article"
        ? '<p class="footer-feedback">この記事の内容に誤りや古い情報があれば、ぜひ教えてください。' +
          '感想やご指摘も大歓迎です。 <a href="#" data-modal-open>お問い合わせはこちら</a></p>'
        : "";

    // 累計訪問数の行(トップページだけ。prefixが空=トップ)。
    // 中身はGoatCounterのカウンターAPIから後で入れる。取れないときは隠れたまま。
    var stats = prefix === "" ? '<p class="footer-stats" id="footer-stats" hidden></p>' : "";

    return (
      '<div class="wrap">' + cols + feedback + stats +
      '<p class="footer-copy">&copy; 2026 OZU LIFE MEMO</p>' +
      "</div>"
    );
  }

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
    // フッターのリンクもヘッダーと同じ相対パスを使う
    var footerPrefix = headerEl ? headerEl.getAttribute("data-prefix") || "" : "";
    footerEl.outerHTML = '<footer class="site-footer">' + buildFooter(footerPrefix, variant) + "</footer>";
  }

  var modalEl = document.querySelector("[data-site-modal]");
  if (modalEl) {
    modalEl.outerHTML = '<div class="modal-overlay" data-modal>' + MODAL_HTML + "</div>";
  }

  markCurrentNav();

  // ── 累計訪問数(トップページのフッターだけ) ──────────────
  // GoatCounterの公式カウンターAPIで、サイト全体の累計訪問数を取って表示する。
  // GoatCounter側の設定「Allow adding visitor counts on your website」がONのときだけ動く。
  // 設定がOFF・広告ブロッカー・通信失敗のときは、行ごと隠れたままにする(何も壊れない)。
  // 数字は最大4時間キャッシュされるので、リアルタイムではない。
  var statsEl = document.getElementById("footer-stats");
  if (statsEl && window.fetch) {
    fetch("https://ozulifememo.goatcounter.com/counter/TOTAL.json")
      .then(function (res) {
        if (!res.ok) throw new Error("counter unavailable");
        return res.json();
      })
      .then(function (data) {
        var n = String(data.count || "").trim();
        if (!n || n === "0") return;
        // GoatCounterは桁区切りに細いスペースを使うので、コンマに直す
        n = n.replace(/[\s  ]+/g, ",");
        statsEl.textContent = "これまでの訪問: のべ" + n + "回(2026年8月からの累計)";
        statsEl.hidden = false;
      })
      .catch(function () {});
  }
})();
