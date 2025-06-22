# GitHub PRログ分析システム

GitHubのプルリクエスト（PR）のデータを収集・分析し、開発プロセスの改善に役立つインサイトを提供するシステムです。

複数のリポジトリを一元的に管理・分析します。

## 機能

- GitHub APIを使用したPRデータの収集機能（`GitHubAPIClient`経由）
- Streamlit GUIによるPRデータの可視化とインタラクティブな分析:
    - リポジトリ一覧の表示
    - 選択したリポジトリのPR一覧表示（状態・作成日でフィルタリング可能）
    - PR詳細表示（タイトル、作成者、状態、説明本文、GitHubリンク）
    - PRごとのレビューコメント表示
- PR、コメント、レビューに関する情報のデータベースへの保存と利用

## GUIの実行

プロジェクトのルートディレクトリで以下のコマンドを実行してStreamlitアプリケーションを起動します。

```bash
streamlit run src/gui/app.py
```

ブラウザでGUIが開かれ、設定されたリポジトリのPRデータを閲覧・分析できます。

## 必要条件

- Python 3.8以上
- GitHub Personal Access Token (PAT)

## セットアップ

1. リポジトリのクローン:
```bash
git clone git https://github.com/takayuki-ou/multi-repos-etl.git
cd multi-repo-etl
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
`.env`ファイルを作成し、少なくとも以下の内容を設定します:
```
GITHUB_TOKEN=your_github_personal_access_token
```
`GITHUB_TOKEN` はGitHub APIからデータを取得するために必須です。

5. 設定ファイルの編集:
`config.yaml`を編集して、分析対象のリポジトリやデータベースのパスを設定します。
```yaml
# GitHub PRログ分析システム設定ファイル

# 対象リポジトリリスト (例)
repositories:
  - owner1/repoA
  # - owner2/repoB

# SQLiteデータベースファイルのパス
# 絶対パスまたはプロジェクトルートからの相対パスで指定
db_path: github_data.db
# 例: data/my_prs.db

# データ取得設定 (データ取得スクリプト用)
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
  file: logs/app.log # ログファイル名を変更しました
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

6. データベースについて:
    - このシステムはデータベースとしてSQLiteを使用します。SQLiteはファイルベースのデータベースであり、`config.yaml`で指定された`db_path`の場所にデータベースファイルが作成されます。
    - アプリケーション（GUIまたはデータ取得スクリプト）の初回実行時に、`src/db/schema.sql`に基づいて必要なテーブルが自動的に作成されます。
    - **注意:** `schema.sql`が更新された場合（例: カラムの追加）、既存のデータベースファイルに対しては自動的に変更が適用されません。手動でのスキーマ変更、マイグレーションツールの導入、またはデータベースファイルの再作成が必要になる場合があります。
    - PRの本文（Description）は`pull_requests`テーブルの`body`カラムに格納されます。GUIで表示するためには、データ収集時にこの情報を取得・保存する必要があります。

## 使用方法

1.  **設定**:
    *   `config.yaml`に対象リポジトリと`db_path`（SQLiteデータベースファイルへのパス）を設定します。
    *   `.env`ファイルに`GITHUB_TOKEN`を設定します。

2.  **データ収集**:
    *   （現時点では、このリポジトリに汎用的なデータ収集スクriptは同梱されていません）
    *   `src.data_collection.GitHubAPIClient`クラスを利用して、対象リポジトリからPRデータを収集し、設定されたSQLiteデータベースに保存するスクリプトを別途作成・実行する必要があります。
    *   この際、PRの`body`（本文）やレビューコメントも収集し、データベースに保存するようにしてください。これらが収集されていれば、GUIで表示されます。

3.  **GUIの実行**:
    *   上記「GUIの実行」セクションの指示に従い、Streamlitアプリケーションを起動します。
    ```bash
    streamlit run src/gui/app.py
    ```
    *   GUIを通じて、収集・保存されたPRデータのフィルタリング、詳細表示（本文含む）、レビューコメントの確認が可能です。

## 注意事項
- `config.yaml`内のリポジトリ名は `owner/repository_name` の形式で正しく指定してください。
- `GITHUB_TOKEN`には、対象リポジトリへのアクセス権限（`repo`スコープなど）が必要です。
- 現状、`Settings`クラス内にはPostgreSQL接続用の設定 (`db_config`プロパティ) も残っていますが、SQLiteを主として利用する場合、`config.yaml`の`db_path`が主に参照されます。

## 出力例（GUI）

Streamlit GUIでは以下の情報がインタラクティブに表示されます（データベースに該当データが存在する場合）。

-   **リポジトリ選択**: サイドバーで分析対象のリポジトリを選択。
-   **PR一覧**: 選択されたリポジトリのPRをフィルタリング（状態、日付）して表形式で表示（番号、タイトル、作成者、状態、作成日時、更新日時、URL）。
-   **PR詳細**:
    -   タイトル（番号含む）、作成者、状態。
    -   GitHub上のPRへの直接リンク。
    -   PR本文（Description）。
-   **レビューコメント**:
    -   コメント投稿者、投稿日時。
    -   コメント本文（Markdown形式で表示）。
    -   GitHub上のコメントへの直接リンク。
