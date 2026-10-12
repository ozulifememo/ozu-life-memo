// 大洲市限定ジオゲッサー用の写真データ。
// file: assets/img/geoguess/<file名> に置いた画像ファイル名
// lat / lng: その写真の実際の撮影場所(緯度経度)
// hint: 画面には出さない任意メモ(空文字でOK)
//
// 写真にGPS情報(EXIF)が入っていなかったため、緯度経度はOpenStreetMapの
// 地名検索(Nominatim)で各ランドマークの登録座標と照合して設定した。
// 現地の看板・建物などその場で撮ったことが明確な写真だけを採用しており、
// 遠くから城などを撮った写真(撮影場所と被写体の場所がずれる)は除外している。
// 誤差はおおむね数m〜30m程度とみられるが、GPS実測ではないため、
// プレイして違和感があれば教えてほしい。
const OZU_GEOGUESS_PHOTOS = [
  { file: "ozu-photo-18.jpg", lat: 33.506291, lng: 132.544656, hint: "大洲市役所の看板" },
  { file: "ozu-photo-19.jpg", lat: 33.506291, lng: 132.544656, hint: "市役所前の「愛と信頼」像" },
  { file: "ozu-photo-33.jpg", lat: 33.531917, lng: 132.577502, hint: "ラ・ムー大洲店" },
  { file: "ozu-photo-34.jpg", lat: 33.506816, lng: 132.576477, hint: "少彦名神社の案内板" },
  { file: "ozu-photo-35.jpg", lat: 33.506816, lng: 132.576477, hint: "少彦名神社の鳥居・社殿" },
  { file: "ozu-photo-36.jpg", lat: 33.506816, lng: 132.576477, hint: "少彦名神社の拝殿内部" },
  { file: "ozu-photo-50.jpg", lat: 33.506506, lng: 132.555008, hint: "如法寺・大洲藩主加藤家墓所の碑" },
  { file: "ozu-photo-51.jpg", lat: 33.506506, lng: 132.555008, hint: "如法寺仏殿の説明板" },
  { file: "ozu-photo-52.jpg", lat: 33.506506, lng: 132.555008, hint: "如法寺の鐘楼" },
  { file: "ozu-photo-53.jpg", lat: 33.506506, lng: 132.555008, hint: "如法寺の本堂" },
  { file: "ozu-photo-68.jpg", lat: 33.508849, lng: 132.545336, hint: "肱川橋の銘板" },
  { file: "ozu-photo-16.jpg", lat: 33.520862, lng: 132.555266, hint: "大洲市総合福祉センター" },
  { file: "ozu-photo-78.jpg", lat: 33.504883, lng: 132.524040, hint: "市立大洲病院" },
];
