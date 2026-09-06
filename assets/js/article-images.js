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
  "sora-tobu-kuruma": { file: "photos/ozu-photo-14.jpg" }
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
  "gappei-tokureisai-owari": "合併特例債の借入額の話。被写体が無い"

  // ── 2026-09-06 追加 ──────────────────────────────
  "ozu-kyoshitsu-koza": { file: "photos/ozu-photo-16.jpg" },
  "ozu-iinkai-jikko": { file: "photos/ozu-photo-20.jpg" },
  "ozu-kinenbi-mise": { file: "photos/ozu-photo-03.jpg" },
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
            "shichosen-ryoheika"]
  },
  {
    theme: "学校・教育の現場",
    subjects: "小中学校の校舎(外観)、大洲高校の正門、体育館、通学路、給食センターの外観、教室の木製の机。児童生徒が写らない時間帯に。",
    slugs: ["chugakko-kyushoku-muryoka", "gikai-futoko-suii", "sogo-kyoiku-kaigi-honne",
            "bukatsu-chiiki-ido", "gikai-ozukoko-teiinware",
            "kyushoku-center-yoryoku", "ozu-shinrin-kankyozei-tsukue"]
  },
  {
    theme: "スーパー・商業施設",
    subjects: "マルナカ大洲店の外観、フレスポ大洲、アクトピア大洲の解体現場・跡地、家電量販店、カラオケ店の外観と料金表、コンビニのマルチコピー機。",
    slugs: ["fuji-point", "fuji-marunaka-aeon-keii", "actopia-ozu-kaitai",
            "shoene-kaden-hojo", "shoene-hojo-keisan",
            "ozu-karaoke-hikaku", "ozu-conveni-kofu"]
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
    slugs: ["ozu-okashi-shigure", "ozu-eemon-selection"]
  },
  {
    theme: "ごみ・環境",
    subjects: "ごみステーションと分別の掲示、ごみ収集カレンダーの掲示板、粗大ごみ処理券を売っている店の棚、清掃センターの受付。",
    slugs: ["gomi-dashi-7bunbetsu", "ozu-sodai-gomi-hikaku"]
  },
  {
    theme: "工場・工業団地",
    subjects: "新谷地区の工場、工業団地の造成地や案内看板、旧松下寿(パナソニック)跡地とそこに通した市道。",
    slugs: ["chosei-cost", "kigyo-yuchi-kikuyocho-hikaku",
            "matsushita-kotobuki", "matsushita-ato-shido"]
  },
  {
    theme: "夏の暑さ",
    subjects: "真夏の青空と照り返す道路、屋外の温度計、暑さ避難所(クーリングシェルター)の掲示。",
    slugs: ["mosho-alert", "cooling-shelter"]
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
            "ozu-shokuinsu-kenai-hikaku", "ozu-kouhou-genka"]
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
    slugs: ["suido-ryokin-toitsu-15pct", "ozu-kogyo-yosui"]
  },
  {
    theme: "駅・道路・タクシー",
    subjects: "伊予大洲駅の駅舎とタクシー乗り場、松山自動車道の4車線化工事の区間(歩道橋などから)、高速のインター入口。",
    slugs: ["ozu-taxi-rideshare", "shikoku-shinkansen-53nen", "matsuyama-do-4shasen-zando"]
  },
  {
    theme: "電波・通信のインフラ",
    subjects: "新しく開通したトンネルの坑口、携帯電話の基地局の鉄塔、住宅に引き込まれたケーブルテレビの線とアンテナ。",
    slugs: ["ozu-denpa-kengai", "ozu-cable-tv-nhk"]
  },
  {
    theme: "城下町の観光施設",
    subjects: "しろしたテラスの外観と看板、大洲城の入口と券売所、おおず赤煉瓦館、まちなかの観光客の流れ(顔が写らない角度で)。",
    slugs: ["shiroshita-terrace-unei", "ozu-shitei-kanrisha", "kanko-rieki-yukue"]
  },
  {
    theme: "大洲の会社・経済",
    subjects: "大洲商工会議所の建物と看板、大洲まつりのポスターやのぼり、市内の主な会社の社屋(公道から、表札が読める程度に)。",
    slugs: ["ozu-cci-shigoto", "ozu-uriage-ranking", "nanyo-kabu-jojo"]
  },
  {
    theme: "まちなかの川と橋",
    subjects: "都谷川の護岸と流れ(まちなかを通る区間)、十夜ヶ橋と橋の下、川沿いの水位標。",
    slugs: ["tsuyagawa-tokutei-toshi-kasen", "toyogabashi-henro-isan"]
  },
  {
    theme: "防犯灯・電気まわり",
    subjects: "電柱に付いた防犯灯、夜の住宅街の街路灯、住宅の分電盤と感震ブレーカー(自宅で撮れる)。",
    slugs: ["ozu-bohantou-denkidai", "kanshin-breaker"]
  },
  {
    theme: "図書館",
    subjects: "大洲市立図書館の外観と書架、返却ポスト、開館時間の掲示。利用者が写らない角度で。",
    slugs: ["ozu-toshokan-kashidashi"]
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
  }
];
