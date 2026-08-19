# OZU LIFE MEMO（非公式・作り直し版）

大洲市の暮らし情報を発信する非公式サイト。STUDIOで作っていたものを、素のHTML/CSS/JSで作り直したものです。
ビルドツールは使っていないので、ファイルをブラウザで開くだけで動きます。

## フォルダ構成

```text
ozu-life-memo/
├── index.html              トップページ
├── concept/index.html      サイト紹介（理念・免責事項・著作権ポリシー）
├── link/index.html         リンク集（25件）
├── news/index.html         大洲最新ニュース一覧（カテゴリタブ + テーブル）
├── photo/index.html        フリー写真
├── eachnews/*.html         個別ニュース記事（34本。STUDIO由来13本+Drive内PDFから新規書き起こし21本）
└── assets/
    ├── css/style.css       全ページ共通スタイル
    ├── js/
    │   ├── main.js             ナビ開閉・カルーセル・ニュースタブ切り替え・お問い合わせモーダル
    │   ├── news-data.js        ★全記事の情報（日付・タイトル・カテゴリ・出典）を1箇所で管理
    │   └── article-related.js 個別記事ページの「あわせて読みたい」を自動生成
    └── img/                プレースホルダー画像（差し替え用）
```

## 記事を1本追加する方法

`assets/js/news-data.js` の配列に1件追記するだけで、トップページの「最新ニュース」・
`news/`一覧・各記事ページの「あわせて読みたい」に自動で反映されます。

その上で `eachnews/(slug).html` を1ファイル追加してください（既存ファイルをコピーして書き換えるのが早いです）。

## ローカルで確認する

ビルド不要です。`index.html` をブラウザ（Edge/Chrome）でダブルクリックして開くだけで確認できます。

開発の経緯・記事の出典一覧・過去のTODO履歴は `private-notes/開発メモ_TODO履歴.md`（非公開）にまとめてあります。
記事を新規に書き起こすときは、`assets/js/news-data.js` に1件追記＋`eachnews/`に1ファイル追加、という
上記のパターンで増やせます。

## GitHub Pagesへの公開手順

1. <https://github.com> にログイン（アカウントがなければ作成）
2. 右上の「+」→「New repository」。リポジトリ名を決める（例: `ozu-life-memo`）。Public のままでOK。READMEなどは追加せず「Create repository」
3. このフォルダで以下を実行してGitHubにアップロード（`<GitHubのURL>` は作成したリポジトリのページに出てくる `https://github.com/ユーザー名/ozu-life-memo.git` のようなURL）

   ```bash
   git remote add origin <GitHubのURL>
   git branch -M main
   git push -u origin main
   ```

4. GitHub上のリポジトリページで「Settings」→ 左メニュー「Pages」
5. 「Build and deployment」の「Source」を `Deploy from a branch` にし、Branch を `main` / `/ (root)` にして Save
6. 数分待つと、同じ画面に `https://ユーザー名.github.io/ozu-life-memo/` のようなURLが表示され、そこで公開されます
7. 更新するときは、ファイルを直して以下を実行するだけです

   ```bash
   git add -A
   git commit -m "更新内容のメモ"
   git push
   ```
