# 0120' SALMON LAB 自動化 第1段階

## ファイルの配置

- `index.html` → リポジトリのルートにある同名ファイルを置き換える（事前にバックアップ）
- `.github/workflows/research-review.yml` → 同じパスに配置（既存ファイルを置き換え）
- `scripts/collect.py` → 同じパスに配置（既存ファイルを置き換え）
- `research/sources.json` → 同じパスに配置（既存ファイルを置き換え）
- `research/approved.json` → 新規作成。**既に承認済みデータがある場合は上書きしない**

## 動作

1. GitHub Actions が毎日 03:17 UTC（日本時間 12:17 頃）に情報源への接続確認を試みる。GitHub の都合で遅延・スキップすることがある。
2. Actions の実行ページにある Artifacts → `salmon-research-review-candidates` から結果を確認する。
3. `http_status: 200` なら接続成功。`error` があれば接続失敗。ワークフローが緑でも接続成功とは限らない。
4. 情報の内容を人が検証してから `research/approved.json` に追加する。
5. サイトの「シャケ研究DB」にある「承認済み研究データ」欄に JSON の内容が表示される。更新後は通常 GitHub Pages の再公開が必要。

## approved.json のデータ例

```json
{
  "schema_version": 1,
  "updated_at": "2026-11-24",
  "enemies": [
    {
      "name": "例：確認済みのシャケ名",
      "category": "オオモノ",
      "hp": "検証した値",
      "weakness": "検証した弱点",
      "strategy": "自分で確認した攻略法",
      "source_url": "https://wikiwiki.jp/splatoon3mix/",
      "reviewed_at": "2026-11-24"
    }
  ]
}
```

この例は形式説明用であり、ゲームの事実を示すものではありません。

**重要**: この段階では Wiki の記事本文やシャケ23種の数値を自動抽出しません。候補の自動承認・自動公開も行いません。外部サイトの利用規約と引用条件を守り、出典を表示してください。
