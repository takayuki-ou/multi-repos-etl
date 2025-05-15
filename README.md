# GitHub PRログ分析システム

GitHubのプルリクエスト（PR）のデータを収集・分析し、開発プロセスの改善に役立つインサイトを提供するシステムです。

複数のリポジトリを一元的に管理・分析します。

## 機能

- GitHub APIを使用したPRデータの自動収集
- PR、コメント、レビューの詳細な分析
- 時系列でのトレンド分析
- テキスト/CSV形式のレポート生成
- データの可視化（グラフ）

## 必要条件

- Python 3.8以上
- PostgreSQL 12以上
- GitHub Personal Access Token (PAT)

## セットアップ

1. リポジトリのクローン:
```bash
git clone https://github.com/your-username/github-pr-da.git
cd github-pr-da
```

2. 仮想環境の作成と有効化:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# または
.\venv\Scripts\activate  # Windows
```

3. 依存パッケージのインストール:
```bash
pip install -r requirements.txt
```

4. 環境変数の設定:
`.env`ファイルを作成し、以下の内容を設定:
```
GITHUB_TOKEN=your_github_personal_access_token
DB_HOST=localhost
DB_PORT=5432
DB_NAME=github_pr_analysis
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

5. データベースのセットアップ:
```bash
psql -U your_db_user -d github_pr_analysis -f src/db/schema.sql
```

6. 設定ファイルの編集:
`config.yaml`を編集し、分析対象のリポジトリを設定:
```yaml
# GitHub PRログ分析システム設定ファイル

# 対象リポジトリリスト
repositories:
  - your-org/your-repo

# データ取得設定
fetch_settings:
  # 初回取得時の遡及期間（日数）
  initial_lookback_days: 30
  # 1回のAPIリクエストで取得する最大PR数
  max_prs_per_request: 100
  # APIリクエスト間の待機時間（秒）
  request_interval: 10

# ログ設定
logging:
  level: INFO
  file: logs/github_pr_analysis.log
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 使用方法

1. GitHubデータの取得:
```bash
python scripts/fetch_github_data.py
```

2. 分析の実行:
```bash
python scripts/run_analysis.py
```

3. レポートの確認:
- テキストレポート: `output/reports/report.txt`
- CSVレポート: `output/reports/metrics.csv`
- グラフ: `output/graphs/`ディレクトリ内

## 出力例

### テキストレポート
```
GitHub PR分析レポート
生成日時: 2024-01-01 12:00:00

プルリクエストの統計
--------------------------------------------------
総PR数: 100
オープン中のPR数: 10
クローズされたPR数: 80
マージされたPR数: 70
平均追加行数: 150.5
平均削除行数: 75.2
平均変更ファイル数: 5.8
平均リードタイム: 24.5時間
...

```

### グラフ
- PRの状態分布
- レビューの分布
- 時系列でのPR作成数推移
- 時系列でのコメント数推移
- 時系列でのレビュー数推移