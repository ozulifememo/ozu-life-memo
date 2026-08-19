// 記事(slug)と写真のひもづけ。
//
// ここに載っている記事だけ、一覧カードと記事ページに写真が出る。
// 「記事の中身と実際に写っているものが合っているか」だけを基準に選んでいる。
// 合う写真が無い記事は、あえて何も出さない(ランダムな写真でごまかさない)。
//
// ・写真の説明(alt)は assets/js/photos-data.js の台帳から自動で引く。
// ・記事ごとに言い回しを変えたいときだけ caption を書く。
// ・撮影待ちの記事は OZU_ARTICLE_PHOTO_WANTED に「何を撮ればいいか」を書いてある。
//   写真が用意できたら、この表に1行足すだけで一覧にもサムネイルが出る。
//
// news-data.js とは別ファイルにしてある(記事の追加作業と、写真の割り当て作業が
// ぶつからないようにするため)。

const OZU_ARTICLE_IMAGES = {
  // ── 行政・市役所 ──────────────────────────────
  "furusato-nozei-r5-jisseki": { file: "photos/ozu-photo-17.jpg" },
  "furusato-nozei-yukue": { file: "photos/ozu-photo-17.jpg" },
  "minsei-hi-saidai": { file: "photos/ozu-photo-18.jpg" },
  "yosan-jishu-zaigen": { file: "photos/ozu-photo-18.jpg" },
  "ozu-keijoshushi-hiritsu": { file: "photos/ozu-photo-20.jpg" },
  "kurashi-benricho-2026": { file: "photos/ozu-photo-17.jpg" },
  "aihara-san": { file: "photos/ozu-photo-17.jpg" },
  "note-taiyou-konatsu-matome": { file: "photos/ozu-photo-18.jpg" },
  "seikatsuhogo-tsuika-kyufu": { file: "photos/ozu-photo-17.jpg" },

  "danjo-kyuyo-sai": { file: "photos/ozu-photo-20.jpg" },
  "danjo-kyuyo-naiwake": { file: "photos/ozu-photo-20.jpg" },
  "nyusatsu-jitsurei": { file: "photos/ozu-photo-20.jpg" },
  "chokai-shobun-kouhyo": { file: "photos/ozu-photo-20.jpg" },
  "sogo-keikaku-d-hyoka": { file: "photos/ozu-photo-20.jpg" },
  "sogo3-pabukome-5nin": { file: "photos/ozu-photo-17.jpg" },
  "gikai-dx-line": { file: "photos/ozu-photo-20.jpg" },
  "ozu-dx-suishin": { file: "photos/ozu-photo-18.jpg" },

  "keijidousha-paypay": { file: "photos/ozu-photo-18.jpg" },
  "keijidosha-zei-hyojun": { file: "photos/ozu-photo-18.jpg" },

  // ── 福祉・医療 ───────────────────────────────
  "ozu-mirai-note": { file: "photos/ozu-photo-16.jpg" },
  "hochoki-jyosei": { file: "photos/ozu-photo-16.jpg" },
  "shakyo-magokoro-bank": { file: "photos/ozu-photo-16.jpg" },
  "ozu-shakyo-kessan": { file: "photos/ozu-photo-16.jpg" },
  "kenko-ishiki-enquete": { file: "photos/ozu-photo-16.jpg" },
  "gikai-minseiiin-nintesoku": { file: "photos/ozu-photo-16.jpg" },

  "yakuzaishi-fusoku": { file: "photos/ozu-photo-78.jpg" },
  "hifuka-hijoukin": { file: "photos/ozu-photo-78.jpg" },

  "kosodate-shien-ichiran": { file: "photos/ozu-photo-19.jpg" },
  "kosodate-ranking-1i": { file: "photos/ozu-photo-19.jpg" },

  // ── 文化会館 ────────────────────────────────
  "bunka-kaikan-kibo-shukusho": { file: "photos/ozu-photo-75.jpg", caption: "建て替えの対象になっている大洲市民会館" },
  "gikai-bunka-kaikan-zaigen": { file: "photos/ozu-photo-75.jpg", caption: "建て替えの対象になっている大洲市民会館" },

  // ── 産業・農業 ───────────────────────────────
  "ja-taiki-shisan": { file: "photos/ozu-photo-21.jpg" },
  "ozmesse-ja-history": { file: "photos/ozu-photo-21.jpg" },
  "chiseki-chosa-83pct": { file: "photos/ozu-photo-77.jpg" },
  "yosan-noka": { file: "real-photo-6.jpg" },

  // ── 買い物・商業 ──────────────────────────────
  "gikai-kaimono-chiketto": { file: "photos/ozu-photo-33.jpg" },
  "setai-nenshu-200": { file: "photos/ozu-photo-03.jpg" },
  "ozu-ben": { file: "real-photo-13.jpg" },

  // ── 大洲城・城下町・観光 ────────────────────────
  "kato-mitsuyasu": { file: "photos/ozu-photo-13.jpg" },
  "iyo-no-shokyoto": { file: "photos/ozu-photo-12.jpg" },
  "ozu-castle-fund": { file: "photos/ozu-photo-22.jpg" },
  "ukai-baru": { file: "photos/ozu-photo-22.jpg" },
  "ozu-chiiki-okoshi-tai": { file: "photos/ozu-photo-22.jpg" },
  "yatsugi-akiya-saisei": { file: "real-photo-10.jpg" },
  "castle-stay-hyakuman": { file: "real-photo-9.jpg" },
  "ozu-kanko-jisseki-r7": { file: "real-photo-14.jpg" },
  "ozu-kanko-5man-nin": { file: "photos/ozu-photo-35.jpg" },
  "kanko-senryaku-chukan": { file: "photos/ozu-photo-73.jpg" },
  "green-destinations-ginsho": { file: "photos/ozu-photo-68.jpg" },
  "ozu-muryo-chushajo": { file: "photos/ozu-photo-74.jpg" },
  "kanko-enquete-ondosa": { file: "photos/ozu-photo-32.jpg" },
  "ozu-kanko-visitor-ranking": { file: "photos/ozu-photo-27.jpg" },
  "sterace-workspace": { file: "photos/ozu-photo-72.jpg" },

  // ── 歴史・寺社 ───────────────────────────────
  "shisho-kamon": { file: "photos/ozu-photo-50.jpg" },
  "nyohoji-kato-bosho": { file: "photos/ozu-photo-55.jpg" },

  // ── 肱川・水・防災 ─────────────────────────────
  "hijikawa-nagare": { file: "photos/ozu-photo-46.jpg" },
  "hijikawabashi-chobo-hiroba": { file: "photos/ozu-photo-69.jpg" },
  "ozu-ukai-guide": { file: "photos/ozu-photo-39.jpg" },
  "ukai-seitaikei": { file: "photos/ozu-photo-39.jpg" },
  "bukatsu-chiiki-ido-kanu": { file: "photos/ozu-photo-39.jpg" },
  "hijikawa-osanshouo-kaseki": { file: "photos/ozu-photo-45.jpg" },
  "gsi-shinsui-chizu": { file: "photos/ozu-photo-64.jpg" },
  "gouu-bosai": { file: "photos/ozu-photo-65.jpg" },
  "bosai-song": { file: "photos/ozu-photo-41.jpg" },
  "hijikawa-arashi-shohyo": { file: "photos/ozu-photo-40.jpg" },
  "natsu-kion-20nen": { file: "photos/ozu-photo-40.jpg" },
  "hijikawa-okami-kaseki": { file: "photos/ozu-photo-80.jpg" },
  "minkan-heli-bosai": { file: "photos/ozu-photo-80.jpg" },

  // ── 人口・まちづくり ────────────────────────────
  "kaso-keikaku-jinko": { file: "photos/ozu-photo-10.jpg" },
  "kaso-chiiki-keikaku": { file: "photos/ozu-photo-10.jpg" },
  "tokei-jinko": { file: "photos/ozu-photo-09.jpg" },
  "juki-jinko-chiku": { file: "photos/ozu-photo-15.jpg" },
  "jinko-vision-3man": { file: "photos/ozu-photo-06.jpg" },
  "ozu-kasseika-keikaku-kenshou": { file: "real-photo-5.jpg" },
  "2005-gappei-kaiko": { file: "real-photo-8.jpg" },
  "machizukuri-hyosho": { file: "photos/ozu-photo-30.jpg" },

  // ── 交通・インフラ ─────────────────────────────
  "jr-akaji-jinko": { file: "real-photo-1.jpg" },
  "chimei-otsu-taisaku": { file: "real-photo-3.jpg" },
  "shikoku-hachinoji-network": { file: "photos/ozu-photo-82.jpg" },
  "michi-ijihi": { file: "photos/ozu-photo-60.jpg" },
  "ozu-toori-namae": { file: "photos/ozu-photo-63.jpg" },
  "shiyuchi-baikyaku": { file: "photos/ozu-photo-42.jpg" },
  "sora-tobu-kuruma": { file: "photos/ozu-photo-14.jpg" }
};

// 「この記事に合う写真がまだ無い」ものの一覧。
// key は撮影テーマ、subjects は撮ってきてほしいもの、slugs は待っている記事。
// 撮影して assets/img/photos/ に追加したら、photos-data.js に台帳を1行足して、
// 上の OZU_ARTICLE_IMAGES にひもづけを書けば一覧にも記事にも反映される。
const OZU_ARTICLE_PHOTO_WANTED = [
  {
    theme: "空き家・古い民家",
    subjects: "傷んだ空き家の外観、板が外れた壁、草の茂った敷地。人物や表札が写らない角度で。",
    slugs: ["kiken-akiya-jokyaku-hojokin", "akiya-441ko-kaitai-level", "akiya-kaitai-soneki-bunkiten",
            "akiyabank-640man-kazoku-shisan", "akiya-taisaku-keikaku", "ozu-arts-taiwan"]
  },
  {
    theme: "長浜地区・長浜港",
    subjects: "長浜港の岸壁と埋立予定地、長浜大橋、海と町並み、長浜高校の外観。",
    slugs: ["nagahama-umetate-pabukome", "nagahama-tsunami-takasa", "nagahama-umetate-shisetsu",
            "nagahama-umetate-keii", "nagahama-kihonkeikaku-nyusatsu", "gikai-tsunami-sotei",
            "shichosen-ryoheika"]
  },
  {
    theme: "学校・教育の現場",
    subjects: "小中学校の校舎(外観)、大洲高校の正門、体育館、通学路。児童生徒が写らない時間帯に。",
    slugs: ["chugakko-kyushoku-muryoka", "gikai-futoko-suii", "sogo-kyoiku-kaigi-honne",
            "bukatsu-chiiki-ido", "gikai-ozukoko-teiinware"]
  },
  {
    theme: "スーパー・商業施設",
    subjects: "マルナカ大洲店の外観、フレスポ大洲、アクトピア大洲の解体現場・跡地、家電量販店。",
    slugs: ["fuji-point", "fuji-marunaka-aeon-keii", "frespo-ozu-hensen", "actopia-ozu-kaitai",
            "shoene-kaden-hojo", "shoene-hojo-keisan"]
  },
  {
    theme: "循環バス「ぐるりんおおず」",
    subjects: "バス車両の外観、バス停の標識と時刻表。",
    slugs: ["gikai-gururin-ozu-shushi", "gururin-ozu-bus-guide"]
  },
  {
    theme: "国立大洲青少年交流の家",
    subjects: "施設の外観と看板、宿泊棟、研修室。",
    slugs: ["kokuritsu-seishonen-riyou-guide", "kokuritsu-seishonen-ozu"]
  },
  {
    theme: "公民館・コミュニティセンター",
    subjects: "上須戒コミュニティセンターの外観(CLTパネルが分かる角度)、他地区のコミュニティセンターの表札。",
    slugs: ["kamisuga-community-center", "kominkan-community-center-itsu"]
  },
  {
    theme: "ダム(野村ダム・鹿野川ダム)",
    subjects: "ダム堤体と銘板(どちらのダムか分かるもの)、貯水池、放流設備。鹿野川荘・「風の里」の外観も。",
    slugs: ["ozu-mizubusoku-shinso", "kanogawaso"]
  },
  {
    theme: "青島・猫",
    subjects: "青島の港と集落、猫。長浜港からの定期船も。",
    slugs: ["aoshima-jinko-kakusa", "gikai-neko-fusai-hojokin"]
  },
  {
    theme: "鵜飼",
    subjects: "うかいの屋形船、鵜飼の船着場、鵜匠(顔が写らない角度で)。",
    slugs: []
  },
  {
    theme: "少彦名神社(菅田町)",
    subjects: "鳥居、社殿、社号標。",
    slugs: ["sukunahikona-jinja"]
  },
  {
    theme: "盤泉荘",
    subjects: "盤泉荘の外観と門、庭。",
    slugs: ["kouhou-2022-seika-bansenso"]
  },
  {
    theme: "大洲の菓子・特産品",
    subjects: "志ぐれを売っている店の外構え、「大洲ええモンセレクション」の商品棚やのぼり。",
    slugs: ["ozu-okashi-shigure", "ozu-eemon-selection"]
  },
  {
    theme: "ごみ・環境",
    subjects: "ごみステーションと分別の掲示、ごみ収集カレンダーの掲示板。",
    slugs: ["gomi-dashi-7bunbetsu"]
  },
  {
    theme: "工場・工業団地",
    subjects: "新谷地区の工場、工業団地の造成地や案内看板。",
    slugs: ["chosei-cost", "kigyo-yuchi-kikuyocho-hikaku"]
  },
  {
    theme: "夏の暑さ",
    subjects: "真夏の青空と照り返す道路、屋外の温度計、暑さ避難所(クーリングシェルター)の掲示。",
    slugs: ["mosho-alert", "cooling-shelter"]
  },
  {
    theme: "犬・動物",
    subjects: "狂犬病予防注射の集合会場の掲示、動物病院の看板。",
    slugs: ["kyokenbyo-yobo-2027"]
  },
  {
    theme: "市役所まわりのバリエーション(急がないが効く)",
    subjects: "議場・委員会室、市役所の窓口フロア、市役所の別角度・別の季節、庁舎前の掲示板。行政・財政の記事が19本あり、いまは同じ3枚を使い回しているため、角度違いが数枚あるだけで一覧の見え方が変わる。",
    slugs: []
  },
  {
    theme: "まちづくりの現場",
    subjects: "地域おこし協力隊が関わる拠点、総合計画ワークショップの会場、「OZU 555 PROJECT」の関連施設。",
    slugs: ["sogo-keikaku-workshop", "ozu-555-project"]
  }
];
