# 0120’ SALMON LAB Ver.3.0 — 研究収集・承認方式

## GitHub Pagesへの導入
1. ZIPを展開し、**中身のファイルとフォルダ**をリポジトリのルートにアップロードします（ZIP自体はアップロードしません）。
2. `index.html`, `research/approved.json`, `research/sources.json`, `scripts/collect.py`, `.github/workflows/research-review.yml` のパスを維持してください。
3. GitHubの Actions → Research candidate collection → Run workflow で手動収集します。
4. 実行後の Artifacts から `salmon-research-review-candidates` を取得して内容を確認します。
5. 出典と数値を検証し、**自分の文章で要約した研究**を `research/approved.json` に追記してコミットするとサイトに表示されます。

## 承認済みデータの書式
```json
{
  "ヘビ": {
    "approved": true,
    "reviewed_at": "2026-11-23",
    "source": "https://wikiwiki.jp/splatoon3mix/サーモンラン/シャケの種類/ヘビ",
    "stats": "確認した数値とその条件",
    "behavior": "追跡・弱点の要約",
    "basic": "初心者向け対処",
    "advanced": "上級者向けの独自分析",
    "cautions": "検証の限界"
  }
}
```

**注意:** 収集処理は原文の短い抜粋を**非公開のレビュー用Artifact**に作成するだけです。AIによる全文自動研究・自動承認・自動公開はありません。GitHub ActionsのArtifactsはリポジトリの公開設定・権限に応じて閲覧可能な場合があります。取得頻度は手動で管理し、Wikiの利用条件・アクセス方針を確認してください。Wiki原文の転載は避けてください。
