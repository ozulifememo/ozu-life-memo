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
  // ── 2026-09-20 撮影の写真(9/23に掲載) ────────────────
  "ozu-jo-nihonichi": { file: "photos/ozu-photo-83.jpg" },
  "ozu-jo-kawara-kimei": { file: "photos/ozu-photo-83.jpg" },
  "ozu-jo-matsu-hinoki": { file: "photos/ozu-photo-84.jpg" },
  "ozu-kisha-densha": { file: "photos/ozu-photo-85.jpg" },
  // ── 行政・市役所 ──────────────────────────────
  "furusato-nozei-r5-jisseki": { file: "photos/ozu-photo-17.jpg" },
  "furusato-nozei-yukue": { file: "photos/ozu-photo-17.jpg" },
  "minsei-hi-saidai": { file: "photos/ozu-photo-18.jpg" },
  "yosan-jishu-zaigen": { file: "photos/ozu-photo-18.jpg" },
  "ozu-keijoshushi-hiritsu": { file: "photos/ozu-photo-20.jpg" },
  "kurashi-benricho-2026": { file: "photos/ozu-photo-17.jpg" },
  "aihara-san": { file: "photos/ozu-photo-17.jpg" },
  "seikatsuhogo-tsuika-kyufu": { file: "photos/ozu-photo-17.jpg" },
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
  "frespo-ozu-hensen": { file: "photos/ozu-photo-33.jpg" },
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
  "ozu-kanko-5man-nin": { file: "photos/ozu-photo-05.jpg" },
  "kanko-senryaku-chukan": { file: "photos/ozu-photo-73.jpg" },
  "green-destinations-ginsho": { file: "photos/ozu-photo-68.jpg" },
  "ozu-muryo-chushajo": { file: "photos/ozu-photo-74.jpg" },
  "kanko-enquete-ondosa": { file: "photos/ozu-photo-32.jpg" },
  "ozu-kanko-visitor-ranking": { file: "photos/ozu-photo-27.jpg" },
  "sterace-workspace": { file: "photos/ozu-photo-72.jpg" },

  // ── 歴史・寺社 ───────────────────────────────
  "shisho-kamon": { file: "photos/ozu-photo-50.jpg" },
  "nyohoji-kato-bosho": { file: "photos/ozu-photo-55.jpg" },
  "sukunahikona-jinja": { file: "photos/ozu-photo-35.jpg" },

  // ── 肱川・水・防災 ─────────────────────────────
  "hijikawa-nagare": { file: "photos/ozu-photo-46.jpg" },
  "hijikawabashi-chobo-hiroba": { file: "photos/ozu-photo-69.jpg" },
  "ozu-ukai-guide": { file: "photos/ozu-photo-73.jpg" },
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
  "sora-tobu-kuruma": { file: "photos/ozu-photo-86.jpg" },
  // ── 2026-09-06 追加 ──────────────────────────────
  "ozu-kyoshitsu-koza": { file: "photos/ozu-photo-16.jpg" },
  "ozu-iinkai-jikko": { file: "photos/ozu-photo-20.jpg" },
};

// 「この記事に合う写真がまだ無い」ものの一覧。
// key は撮影テーマ、subjects は撮ってきてほしいもの、slugs は待っている記事。
// 撮影して assets/img/photos/ に追加したら、photos-data.js に台帳を1行足して、
// 上の OZU_ARTICLE_IMAGES にひもづけを書けば一覧にも記事にも反映される。
// 写真が要らないと判断した記事。
// 数字と制度だけの話で、内容に合う被写体が無い(あるいは撮るのが不適切な)もの。
// ここに入れておくと「どのテーマにも入っていない記事」に出てこなくなる。
// 撮れる被写体を思いついたら、この表から外してテーマの slugs に移すこと。
const OZU_ARTICLE_NO_PHOTO = {
  "ozu-furusato-ryushutsu": "ふるさと納税の収支の話。被写体が無い",
  "ozu-kasoryo-shiminhyo": "火葬料の話。斎場を撮るのは弔いの場なので避ける",
  "ozu-mynakenkou-riyoritsu": "利用率の話。医療機関の受付を撮るのは患者が写るので避ける",
  "ozu-toilecar-kumamoto": "車両が市外に出ていることが多く、確実に撮れない",
  "smart-shrink-ozu": "市長答弁と政策論。被写体が無い",
  "kishou-bosai-advisor": "県の人事と市の方針の話。被写体が無い",
  "gappei-tokureisai-owari": "合併特例債の借入額の話。被写体が無い",


  // ── 2026-09-20、どこにも登録されていなかった112本を仕分けた。
  //    ここは「撮るべき被写体が無い」と判断した46本。
  "himeboss-ozu": "県の認証事業所の数を数えた話。被写体が無い",
  "jichitai-site-403": "自治体サイトの応答を測った話。被写体が無い",
  "kanko-towa-nanika": "「観光」の語源と全国の統計の話。被写体が無い",
  "kei-futsu-10nen": "軽と普通車の維持費の計算。車を撮るとナンバーが写るので避ける",
  "kessan-nihongo": "決算用語の言い換えの話。被写体が無い",
  "nankai-kakuritsu-2tsu": "地震の確率の出し方の話。被写体が無い",
  "nankai-kakuritsu-murotsu": "高知県室津の古文書の読みの話。市内に撮る被写体が無い",
  "nanyo-furusato-mikan": "南予各市のふるさと納税額を比べた話。大洲市内に撮る被写体が無い",
  "naze-tabi-ni-deru": "全国の外出率の統計の話。被写体が無い",
  "okane-01-dare-ga-atsumeru": "31種類の税の一覧の話。被写体が無い",
  "okane-02-chokusetsu-kansetsu": "直接税と間接税のしくみの話。被写体が無い",
  "okane-04-kuni-ken-shi": "国と県と市の役割分担の話。被写体が無い",
  "okane-05-nanyo-chihokyoku": "県の出先機関の再編の話。庁舎の外観しか撮るものが無い",
  "okane-06-kubarinaosi": "交付税の配り直しの話。被写体が無い",
  "okane-08-doko-ni-tsukau": "予算の執行率の話。被写体が無い",
  "okane-09-dare-ga-yaru": "一部事務組合と委託の話。消防庁舎の外観しか撮るものが無い",
  "okane-10-ozu-no-tsucho": "市の資金繰りの話。被写体が無い",
  "ozu-dare-ga-kaite-iru": "個人のブログを数えた話。書き手が特定されるので避ける",
  "ozu-dare-ga-kimeru": "一般財源の内訳の話。被写体が無い",
  "ozu-furui-homepage": "古いホームページを探した話。被写体が無い",
  "ozu-furusato-18nen": "寄附額18年の推移の話。被写体が無い",
  "ozu-furusato-omakase": "寄附金の使い道の決め方の話。被写体が無い",
  "ozu-furusato-shinai": "自分の市への寄附ができるかという制度の話。被写体が無い",
  "ozu-furusato-suru-gawa": "寄附の上限額の計算。被写体が無い",
  "ozu-houjin-kiesaki": "法人登記のデータを数えた話。被写体が無い",
  "ozu-jiko-kaji": "事故と火災の統計の話。現場を撮るのは当事者に失礼なので避ける",
  "ozu-jumin-kansa": "住民監査請求の手続きの話。被写体が無い",
  "ozu-kaigo-nyumon": "介護の費用と手続きの話。介護の現場を撮るのは利用者が写るので避ける",
  "ozu-kekkon-shussan": "出産の給付金と手続きの話。産科を撮るのは患者が写るので避ける",
  "ozu-kensaku-sajesuto": "検索サジェストを数えた話。被写体が無い",
  "ozu-kofuzei-hikizan": "交付税の計算式の話。被写体が無い",
  "ozu-kokuho-kennai-hikaku": "国保料の県内比較の計算。被写体が無い",
  "ozu-kotei-shisanzei-ie": "固定資産税の20年の計算。家を撮ると持ち主が特定されるので避ける",
  "ozu-kuchikiki-kiroku": "議員の口利きの記録があるかの話。被写体が無い",
  "ozu-kyujin-nenshu-sa": "求人と年収の統計の話。被写体が無い",
  "ozu-kyujin-shokushu-betsu": "求人倍率の内訳の話。被写体が無い",
  "ozu-matsuyama-seikatsuhi": "松山との生活費の比較計算。被写体が無い",
  "ozu-mondai-nenpyo": "将来の見通しを年表にした話。被写体が無い",
  "ozu-net-gokai": "ネット上の話を4件確かめた記事。ばらばらでまとまった被写体が無い",
  "ozu-saiban": "議案に出てこない裁判の条文の話。被写体が無い",
  "ozu-shakkin-hitori-atari": "借金を1人あたりで割る計算の話。被写体が無い",
  "ozu-shakyo-nanimono": "社協という法人のしくみの話。社協の建物の外観しか撮るものが無い",
  "ozu-shiminzei-yukue": "市民税の行き先の計算。被写体が無い",
  "ozu-tsukin-jikan": "通勤時間の統計の話。通勤の車列を撮るとナンバーが写るので避ける",
  "ozu-tsukin-shigai": "市外との通勤の出入りの統計。被写体が無い",
  "ozu-uchiko-setto": "行政の組織の線引きを数えた話。被写体が無い",
};

const OZU_ARTICLE_PHOTO_WANTED = [
  {
    theme: "空き家・古い民家",
    subjects: "傷んだ空き家の外観、板が外れた壁、草の茂った敷地。人物や表札が写らない角度で。",
    slugs: ["kiken-akiya-jokyaku-hojokin", "akiya-441ko-kaitai-level", "akiya-kaitai-soneki-bunkiten",
            "akiyabank-640man-kazoku-shisan", "akiya-taisaku-keikaku", "ozu-arts-taiwan",
            "ozu-reform-hojo"]
  },
  {
    theme: "長浜地区・長浜港",
    subjects: "長浜港の岸壁と埋立予定地、長浜大橋、海と町並み、長浜高校の外観。",
    slugs: ["nagahama-umetate-pabukome", "nagahama-tsunami-takasa", "nagahama-umetate-shisetsu",
            "nagahama-umetate-keii", "nagahama-kihonkeikaku-nyusatsu", "gikai-tsunami-sotei",
            "shichosen-ryoheika",
            "nagahama-akabashi"]
  },
  {
    theme: "学校・教育の現場",
    subjects: "小中学校の校舎(外観)、大洲高校の正門、体育館、通学路、給食センターの外観、教室の木製の机。児童生徒が写らない時間帯に。",
    slugs: ["chugakko-kyushoku-muryoka", "gikai-futoko-suii", "sogo-kyoiku-kaigi-honne",
            "bukatsu-chiiki-ido", "gikai-ozukoko-teiinware",
            "kyushoku-center-yoryoku", "ozu-shinrin-kankyozei-tsukue",
            "ozu-furusato-tsukaimichi", "ozu-kyoin-ken-to-shi", "ozu-chugaku-shinro-shinai", "kyushoku-taberarenai-ko", "taiikukan-kucho"]
  },
  {
    theme: "スーパー・商業施設",
    subjects: "マルナカ大洲店の外観、フレスポ大洲、アクトピア大洲の解体現場・跡地、家電量販店、カラオケ店の外観と料金表、コンビニのマルチコピー機。",
    slugs: ["fuji-point", "fuji-marunaka-aeon-keii", "actopia-ozu-kaitai",
            "shoene-kaden-hojo",
            "ozu-karaoke-hikaku", "ozu-conveni-kofu",
            "ozu-shohinken-nagare", "ozu-supa-toho-10pun", "ozu-conveni-itsukara", "ozu-ramenshop-nazo", "ozu-shoten-nanken"]
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
    subjects: "上須戒コミュニティセンターの外観(CLTパネルが分かる角度)、他地区のコミュニティセンターの表札、入口の鍵まわり(スマートロックの有無が分かるもの)。",
    slugs: ["kamisuga-community-center", "kominkan-community-center-itsu",
            "smartlock-community-center"]
  },
  {
    theme: "ダム(野村ダム・鹿野川ダム)",
    subjects: "ダム堤体と銘板(どちらのダムか分かるもの)、貯水池、放流設備。鹿野川荘・「風の里」の外観も。",
    slugs: ["ozu-mizubusoku-shinso", "kanogawaso",
            "kassui-nani-ga-okiru"]
  },
  {
    theme: "青島・猫",
    subjects: "青島の港と集落、猫。長浜港からの定期船も。",
    slugs: ["aoshima-jinko-kakusa", "gikai-neko-fusai-hojokin"]
  },
  {
    theme: "鵜飼",
    subjects: "うかいの屋形船、鵜飼の船着場、鵜匠(顔が写らない角度で)。",
    slugs: [
            "ozu-ukai-kanransha"]
  },
  {
    theme: "臥龍山荘",
    subjects: "臥龍山荘の外観・不老庵・庭。いま「臥龍山荘」として台帳に入れていた写真は、実際には少彦名神社の参籠殿だったため、臥龍山荘の写真は1枚も無い。",
    slugs: []
  },
  {
    theme: "盤泉荘",
    subjects: "盤泉荘の外観と門、庭。",
    slugs: ["kouhou-2022-seika-bansenso"]
  },
  {
    theme: "大洲の菓子・特産品",
    subjects: "志ぐれを売っている店の外構え、「大洲ええモンセレクション」の商品棚やのぼり。",
    slugs: ["ozu-okashi-shigure", "ozu-eemon-selection",
            "ozu-furui-mise", "ozu-imotaki-makete", "ozu-mugimiso-shoyu"]
  },
  {
    theme: "ごみ・環境",
    subjects: "ごみステーションと分別の掲示、ごみ収集カレンダーの掲示板、粗大ごみ処理券を売っている店の棚、清掃センターの受付。",
    slugs: ["gomi-dashi-7bunbetsu", "ozu-sodai-gomi-hikaku",
            "ehime-gomibukuro-20", "juden-denchi-dashikata"]
  },
  {
    theme: "工場・工業団地",
    subjects: "新谷地区の工場、工業団地の造成地や案内看板、旧松下寿(パナソニック)跡地とそこに通した市道。",
    slugs: ["chosei-cost", "kigyo-yuchi-kikuyocho-hikaku",
            "matsushita-kotobuki", "matsushita-ato-shido",
            "higashi-ozu-sangyo-danchi"]
  },
  {
    theme: "夏の暑さ",
    subjects: "真夏の青空と照り返す道路、屋外の温度計、暑さ避難所(クーリングシェルター)の掲示。",
    slugs: ["mosho-alert", "cooling-shelter",
            "ozu-atsusa-samusa-denkidai"]
  },
  {
    theme: "犬・動物",
    subjects: "狂犬病予防注射の集合会場の掲示、動物病院の看板。",
    slugs: ["kyokenbyo-yobo-2027", "ozu-inuneko-hikitori"]
  },
  {
    theme: "市役所まわりのバリエーション(急がないが効く)",
    subjects: "議場・委員会室、市役所の窓口フロア、市役所の別角度・別の季節、庁舎前の掲示板、庁舎の駐車場に並ぶ公用車、窓口に置いてある軟骨伝導イヤホン、広報おおずの配布ラック。行政・財政の記事が19本あり、いまは同じ3枚を使い回しているため、角度違いが数枚あるだけで一覧の見え方が変わる。",
    slugs: ["nankotsu-dendo-earphone", "ozu-koyosha-ev", "ozu-shiyakusho-zangyo",
            "ozu-shokuinsu-kenai-hikaku", "ozu-kouhou-genka",
            "ozu-shokuin-tsukin", "okane-07-shiyakusho-keiei", "ozu-yosan-calendar", "ozu-gikai-kotoba", "ozu-seigan-hosoru", "ozu-kentoshimasu-kaigiroku", "ozu-kaikei-nendo-ninyo", "ozu-joho-kokai-tsukaikata", "shimin-post-teigen", "gikai-2026-09-tsukoku"]
  },
  {
    theme: "まちづくりの現場",
    subjects: "地域おこし協力隊が関わる拠点、総合計画ワークショップの会場、「OZU 555 PROJECT」の関連施設。",
    slugs: ["sogo-keikaku-workshop", "ozu-555-project"]
  },
  {
    theme: "保育所・学童・保健センター",
    subjects: "保育所・こども園の外観と門(園児が写らない時間帯に)、放課後児童クラブの入口、保健センターの外観と健診の案内掲示。",
    slugs: ["rikkoho-hoikusho-nyusho", "gosaiji-kenshin-ozu", "ozu-hokago-jido-club"]
  },
  {
    theme: "選挙・投票の現場",
    subjects: "選挙ポスターの掲示板、オズメッセ大洲店の入口と期日前投票所の案内、選挙公報を置いてある棚。",
    slugs: ["ozmesse-kijitsuzen-tohyo", "ozu-senkyo-kouhou"]
  },
  {
    theme: "太陽光パネル",
    subjects: "住宅の屋根に載った太陽光パネル、山の斜面のメガソーラー(公道からの遠景)、パワーコンディショナーの箱。",
    slugs: ["ozu-solar-katei", "ozu-solar-yama"]
  },
  {
    theme: "水道・浄水場",
    subjects: "浄水場・配水池の外観と銘板、水道メーターの検針票(番号と氏名を隠して)、工業用水の管路や施設の看板。",
    slugs: ["suido-ryokin-toitsu-15pct", "ozu-kogyo-yosui",
            "nanyo-suido-ryokin", "ozu-suido-10nengo", "ozu-gesuido-jokaso", "suido-daicho-system"]
  },
  {
    theme: "駅・道路・タクシー",
    subjects: "伊予大洲駅の駅舎とタクシー乗り場、松山自動車道の4車線化工事の区間(歩道橋などから)、高速のインター入口。",
    slugs: ["ozu-taxi-rideshare", "shikoku-shinkansen-53nen", "matsuyama-do-4shasen-zando",
            "ozu-kotsu-anzen-kofukin", "jr-1025oku-zeikin", "ozu-shimin-ga-ugoita", "seikatsu-doro-30km"]
  },
  {
    theme: "電波・通信のインフラ",
    subjects: "新しく開通したトンネルの坑口、携帯電話の基地局の鉄塔、住宅に引き込まれたケーブルテレビの線とアンテナ。",
    slugs: ["ozu-denpa-kengai", "ozu-cable-tv-nhk"]
  },
  {
    theme: "城下町の観光施設",
    subjects: "しろしたテラスの外観と看板、大洲城の入口と券売所、おおず赤煉瓦館、まちなかの観光客の流れ(顔が写らない角度で)。",
    slugs: ["shiroshita-terrace-unei", "ozu-shitei-kanrisha", "kanko-rieki-yukue",
            "ozu-namae-no-yurai", "uchiko-ozu-kanko"]
  },
  {
    theme: "大洲の会社・経済",
    subjects: "大洲商工会議所の建物と看板、大洲まつりのポスターやのぼり、市内の主な会社の社屋(公道から、表札が読める程度に)。",
    slugs: ["ozu-cci-shigoto", "ozu-uriage-ranking", "nanyo-kabu-jojo"]
  },
  {
    theme: "まちなかの川と橋",
    subjects: "都谷川の護岸と流れ(まちなかを通る区間)、十夜ヶ橋と橋の下、川沿いの水位標。",
    slugs: ["tsuyagawa-tokutei-toshi-kasen", "toyogabashi-henro-isan",
            "ozu-suitengu-hashi", "ozu-takuchi-kasaage"]
  },
  {
    theme: "防犯灯・電気まわり",
    subjects: "電柱に付いた防犯灯、夜の住宅街の街路灯、住宅の分電盤と感震ブレーカー(自宅で撮れる)。",
    slugs: ["ozu-bohantou-denkidai", "kanshin-breaker"]
  },
  {
    theme: "図書館",
    subjects: "大洲市立図書館の外観と書架、返却ポスト、開館時間の掲示。利用者が写らない角度で。",
    slugs: ["ozu-toshokan-kashidashi",
            "ozu-saiban-toshokan"]
  },
  {
    theme: "道の駅・あさもや",
    subjects: "道の駅「清流の里ひじかわ」の看板とトイレ棟、あさもやの外観と駐車場、直売所の棚。",
    slugs: ["ozu-michinoeki-machinoeki"]
  },
  {
    theme: "ハゼの細道",
    subjects: "「ハゼの細道」に植えられたハゼの並木、樹名板、紅葉の時期の様子。",
    slugs: ["ozu-haze-no-hosomichi"]
  },


  // ── 2026-09-20に足した新しいテーマ
  {
    theme: "冨士山公園と山の眺め",
    subjects: "冨士山公園の展望台から見た大洲の町、つつじまつりの時期のツツジ、公園の入口と駐車場（500円の料金の掲示があれば一緒に）、まちなかから見える神南山・壺神山の遠景。",
    slugs: ["ozu-mieru-yama", "ozu-takai-tokoro-tenbo", "ozu-kotsu-seiri-ryo-kotoba", "ozu-kato-yasumichi-kifu", "tomisuyama-tsutsuji"]
  },
  {
    theme: "田んぼ・畑・竹林",
    subjects: "山を削って作った国営農地の段々の畑、耕作放棄地の草に埋もれた畑、区画を作り直している田んぼ（南久米の野佐来）、栗の木と柑橘の畑、放置された竹林。農作業をしている人が写らない角度で。",
    slugs: ["ozu-yasarai-nochi", "ozu-jabara-10nen", "ozu-tabako-haisaku", "ozu-kokuei-nochi", "ozu-chosen-sakumotsu", "ozu-menma-takenoko", "ozu-kuri-nakayama"]
  },
  {
    theme: "文化会館・市民会館",
    subjects: "建て替えの対象になっている大洲市民会館の外観（別角度・別の季節）、建設予定地とその掲示、工事の看板。いま台帳にある1枚しか無いため、角度違いが要る。",
    slugs: ["okane-03-tsukaimichi", "kokubunsai-2028-ehime", "bunka-kaikan-nyusatsu-fucho"]
  },
  {
    theme: "市営・県営住宅とアパート",
    subjects: "市営住宅・県営住宅の棟の外観と入居募集の掲示、まちなかの民間アパートの遠景。表札・洗濯物・人・車のナンバーが写らない角度で。",
    slugs: ["ozu-kariru-tetsuzuki", "ozu-yachin-soba"]
  },
  {
    theme: "地名の看板・標識",
    subjects: "地名が入った道路標識・交差点の標識・バス停の標柱（長浜の「黒田」、冨士など読みにくい地名を優先）、町名の案内板、ふりがなの付いた表示。",
    slugs: ["ozu-yubin-bango-nai", "ozu-nandoku-chimei"]
  },
];
