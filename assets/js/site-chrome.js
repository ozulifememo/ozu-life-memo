(function () {
  function buildHeader(prefix) {
    var home = prefix === "" ? "./" : prefix;
    return (
      '<div class="wrap">' +
      '<a href="' + home + '" class="logo">' +
      '<img src="' + prefix + 'assets/img/logo-mark.png" alt="" class="logo-mark" width="30" height="30" decoding="async">' +
      "<span>OZU LIFE MEMO</span></a>" +
      '<nav class="main-nav">' +
      '<a href="' + home + '">HOME</a>' +
      '<a href="' + prefix + 'concept/">サイト紹介</a>' +
      '<a href="' + prefix + 'link/">リンク集</a>' +
      '<a href="' + prefix + 'sakuin/">こんなときは</a>' +
      '<div class="nav-dropdown">' +
      '<button type="button" class="nav-dropdown-trigger">読み物<span class="nav-caret">▾</span></button>' +
      '<div class="nav-dropdown-menu">' +
      '<a href="' + prefix + 'news/">大洲ノート</a>' +
      '<a href="' + prefix + 'best/">おすすめ10選</a>' +
      '<a href="' + prefix + 'monthly/">月間まとめ</a>' +
      '<a href="' + prefix + 'history/">大洲の歴史</a>' +
      '<a href="' + prefix + 'book/">大洲と読書</a>' +
      '<a href="' + prefix + 'jiyu-kenkyu/">大洲の自由研究</a>' +
      '<a href="' + prefix + 'okane/">大洲のお金の教科書</a>' +
      '<a href="' + prefix + 'data/">データで見る大洲</a>' +
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
      '<a href="' + prefix + 'search/" class="nav-search">さがす</a>' +
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
      '<a href="' + prefix + 'sakuin/">こんなときは</a>' +
      '<a href="' + prefix + 'news/">大洲ノート</a>' +
      '<a href="' + prefix + 'best/">おすすめ10選</a>' +
      '<a href="' + prefix + 'jiyu-kenkyu/">大洲の自由研究</a>' +
      '<a href="' + prefix + 'okane/">大洲のお金の教科書</a>' +
      '<a href="' + prefix + 'nengaku/">暮らしの年額</a>' +
      '<a href="' + prefix + 'dogubako/">市を動かす道具箱</a>' +
      '<a href="' + prefix + 'gimon/">大洲の疑問</a>' +
      '<a href="' + prefix + 'data/">データで見る大洲</a>' +
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
      '<a href="' + prefix + 'uta/">サイトの歌</a>' +
      '<a href="' + prefix + 'teisei/">直した記録</a>' +
      '<a href="' + prefix + 'koe/">読者の声</a>' +
      '<a href="' + home + '">トップページ</a>' +
      '<a href="#" data-modal-open>お問い合わせ</a>' +
      // 外部の発信先。なりすまし防止も兼ねて、本物はここから辿れる状態にしておく。
      '<a href="https://note.com/ozulifememo" target="_blank" rel="noopener">note</a>' +
      '<a href="https://www.instagram.com/ozulifememo/" target="_blank" rel="noopener">Instagram</a>' +
      '<a href="' + prefix + 'feed.xml">更新をRSSで受け取る</a>' +
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

  // モーダルにも「メモう」を出す。案内役として、読者と接する場所にだけ顔を出す方針
  function buildModal(prefix) {
    return (
    '<div class="modal-box">' +
    '<button class="modal-close" data-modal-close aria-label="閉じる">&times;</button>' +
    '<img src="' + prefix + 'assets/img/memou.svg" alt="" class="modal-memou" width="76" height="76" decoding="async">' +
    "<h3>お問い合わせ・Googleフォームはこちら</h3>" +
    '<p class="modal-note">＼ 名前やメールアドレスの入力は一切不要です ／</p>' +
    '<p class="modal-note">調べてほしいことがあれば、1行で。それが次の記事の種になります。</p>' +
    '<p class="modal-note">大洲で小さな集まりを開くとき、知らせてほしい方は「知らせて」とだけ送ってください。メールアドレスの欄に書いてくれた方にだけ、知らせます。</p>' +
    '<p class="modal-warning">' +
    "<strong>【非公式・個人ボランティアです】</strong>" +
    "制度の詳細は必ず公式HPを確認してください。情報のまとめ・感想は個人の見解です。" +
    "</p>" +
    '<a href="https://docs.google.com/forms/d/e/1FAIpQLSfevBytb8aZmkEUX9m5aC0EUHxDmmYM0jYog33aPFr8AT_OEA/viewform?usp=dialog" class="form-btn" target="_blank" rel="noopener">Google フォーム</a>' +
    "</div>"
    );
  }

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
    var modalPrefix = headerEl ? headerEl.getAttribute("data-prefix") || "" : "";
    modalEl.outerHTML = '<div class="modal-overlay" data-modal>' + buildModal(modalPrefix) + "</div>";
  }

  markCurrentNav();

  // ── 読者の声(記事のページだけ。2026-10-18) ──────────────
  // assets/js/koe-data.js に、この記事への声があれば、フッターのすぐ上に3件まで出す。
  // 声が1件も無い記事には何も出さない(空の箱を見せない)。一覧は koe/ のページ。
  if (variant === "article") {
    var here = (location.pathname.match(/[^\/]+\/[^\/]+\.html$/) || [""])[0];
    var koePrefix = headerEl ? headerEl.getAttribute("data-prefix") || "" : "";
    var koeScript = document.createElement("script");
    koeScript.src = koePrefix + "assets/js/koe-data.js";
    koeScript.onload = function () {
      var all = (typeof OZU_KOE !== "undefined" && OZU_KOE) || [];
      var mine = all.filter(function (k) { return here && k.page === here; }).slice(0, 3);
      var footer = document.querySelector(".site-footer");
      if (!mine.length || !footer) return;
      var esc = function (s) {
        return String(s || "").replace(/[&<>"]/g, function (c) {
          return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
        });
      };
      var box = document.createElement("section");
      box.className = "koe-box";
      box.innerHTML =
        '<div class="wrap"><h2>この記事に届いた声</h2><ul>' +
        mine.map(function (k) {
          var m = /^(\d{4})-(\d{2})$/.exec(k.month || "");
          return "<li><blockquote>" + esc(k.text) + "</blockquote>" +
            (m ? "<p>" + m[1] + "年" + Number(m[2]) + "月に届いた声</p>" : "") + "</li>";
        }).join("") +
        '</ul><p class="koe-box-more"><a href="' + koePrefix + 'koe/">ほかの記事に届いた声</a> ・ ' +
        '<a href="#" class="koe-box-send">声を送る</a></p></div>';
      footer.parentNode.insertBefore(box, footer);
      // main.js は読み込んだときに [data-modal-open] へ印を付けるので、あとから足したこのリンクには付かない。
      // フッターの「お問い合わせ」を押したのと同じにする
      box.querySelector(".koe-box-send").addEventListener("click", function (e) {
        e.preventDefault();
        var opener = footer.querySelector("[data-modal-open]");
        if (opener) opener.click();
      });
    };
    document.body.appendChild(koeScript);
  }

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
