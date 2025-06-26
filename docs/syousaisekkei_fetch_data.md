## **GitHub PRログ分析システム データ取得機能詳細設計**

本ドキュメントは、「GitHub PRログ分析システム 基本設計書」の「3. 機能設計 \- データ取得機能」を詳細化したものです。

### **1\. 概要**

データ取得機能は、Mac OS Scheduler (cron) によって定期的に実行され、設定ファイルで指定された複数GitHubリポジトリから、新規または更新されたプルリクエスト (PR)、Issueコメント、レビューコメントを取得し、ローカルのSQLiteデータベースに蓄積する役割を担います。取得にはGitHub REST APIを使用します。

### **2\. モジュール構成**

提案ディレクトリ構成 (src/) に基づき、データ取得機能は主に以下のモジュールで構成されます。

* src/config/settings.py: システム設定（対象リポジトリリスト、DB接続情報、API認証情報など）を読み込み、提供します。
* src/db/database.py: SQLiteデータベースへの接続確立、セッション管理、トランザクション処理など、DB操作の共通基盤を提供します。
* src/github\_api/client.py: GitHub REST APIへの低レベルなリクエスト送信、認証ヘッダーの管理、APIレート制限のハンドリング、ページネーション処理を担当します。
* src/github_api/fetcher.py: GitHub APIクライアント (client.py) を使用して、PR、Issueコメント、レビューコメントといった特定の種類のデータを取得する高レベルなロジックを実装します。GitHubFetcherクラスは、データベースから最終取得日時を取得し、それを基準にしたデータフィルタリングを行います。リポジトリ単位で全データタイプを一括取得するfetch_all_data_for_repo()メソッドを提供します。
* src/data\_processing/processor.py: fetcher.pyで取得したAPI応答データを受け取り、データベーススキーマに合わせてデータを整形し、データベースへの投入（UPSERT）処理を実行します。
* scripts/fetch\_github\_data.py: データ取得処理全体の実行を制御するトップレベルのスクリプトです。設定読み込み、DB接続確立、各リポジトリに対するデータ取得・投入処理のループ、エラーハンドリング、ログ出力を担当します。

### **3\. 設定読み込みと認証**

* **設定ファイル:** 対象リポジトリリストは config.yaml ファイルで定義します。形式はYAMLリストとし、各要素は owner/repo の文字列とします。
  repositories:
    \- owner1/repoA
    \- owner2/repoB
    \- owner3/repoC

* **API認証情報:** GitHub Personal Access Token (PAT) は、システムの実行環境の環境変数（例: GITHUB\_PAT）として設定します。src/config/settings.py は os.environ.get('GITHUB\_PAT') のように環境変数からPATを読み込みます。DB接続情報も同様に環境変数または別途安全な設定ファイルから読み込むようにします。
* **認証ヘッダー:** src/github\_api/client.py 内で、読み込んだPATを使用してAPIリクエストの Authorization: token YOUR\_PAT ヘッダーを設定します。

### **4. データ取得ロジックの詳細 (GitHubFetcherクラス)**

src/github_api/fetcher.py のGitHubFetcherクラスは、以下の処理フローでデータを取得します：

#### **4.1 GitHubFetcherクラスの構成**

```python
class GitHubFetcher:
    def __init__(self, client: GitHubAPIClient):
        self.client = client
        # self.db_handler = db_handler  # 将来的にデータベースハンドラを統合予定
```

#### **4.2 メインメソッド: fetch_all_data_for_repo()**

このメソッドは指定されたリポジトリの全データを取得する中核的な処理を実行します：

1. **リポジトリ名の解析:**
   * "owner/repo"形式の文字列を owner と repo に分割
   * 例: "microsoft/vscode" → owner="microsoft", repo="vscode"

2. **最終取得日時の特定:**
   * `get_last_fetched_at(repo_full_name)` メソッドを呼び出し
   * 現在の実装では、データベースハンドラが完全統合されていないためNoneを返却
   * 実装完了時は、データベースから該当リポジトリの最終取得日時（ISO 8601形式）を取得
   * 初回取得時（最終取得日時が存在しない場合）はNoneのままGitHub APIに渡され、全データが取得される

3. **プルリクエストの取得:**
   ```python
   pull_requests = self.client.get_pull_requests(owner, repo, since=since)
   ```
   * GitHub APIクライアントを使用してPRリストを取得
   * `since` パラメータにより、最終取得日時以降に更新されたPRのみを取得
   * 取得件数をログに記録

4. **各PRに対するコメント取得:**
   
   **Issueコメントの取得:**
   ```python
   issue_comments = self.client.get_issue_comments(owner, repo, issue_number=pr_number, since=since)
   ```
   * 各PRについて、関連するIssueコメントを取得
   * PRはIssueの一種であるため、PR番号をissue_numberとして使用
   * `since` パラメータにより、最終取得日時以降のコメントのみを取得
   * 取得したコメントを `all_issue_comments` リストに追加

   **レビューコメントの取得:**
   ```python
   review_comments = self.client.get_review_comments(owner, repo, pull_number=pr_number, since=since)
   ```
   * 各PRについて、関連するレビューコメントを取得
   * `since` パラメータにより、最終取得日時以降のコメントのみを取得
   * 取得したコメントを `all_review_comments` リストに追加

5. **エラーハンドリング:**
   * PRデータに必須の'number'フィールドが存在しない場合、警告ログを出力してそのPRをスキップ
   * 各段階で取得件数をデバッグログに記録

6. **戻り値:**
   * タプル形式で3つのリストを返却: `(pull_requests, all_issue_comments, all_review_comments)`
   * 呼び出し元で各データタイプを個別に処理可能

#### **4.3 ログ出力**

取得処理の各段階で詳細なログを出力：
- リポジトリごとの処理開始・完了
- 各データタイプの取得件数
- エラーやスキップされたデータの詳細
- デバッグレベルでの各PR単位の取得状況

#### **4.4 手動テスト機能**

`__main__` ブロックでは、設定ファイルから読み込んだ最初のリポジトリに対してテスト実行を行い、取得結果の概要を標準出力に表示します。

### **5\. データベース投入 (UPSERT)**

src/data\_processing/processor.py が整形済みデータを受け取り、データベースに投入します。

1. **DB接続:** src/db/database.py を使用してデータベース接続を確立し、トランザクションを開始します。
2. **データ投入:**
   * 整形済みのPRデータ、Issueコメントデータ、レビューコメントデータを、それぞれのテーブルに投入します。
   * 投入はバッチ処理で行うことで、DBへの負荷を軽減します。
   * **UPSERTロジック:** 各テーブルの主キー（GitHub ID）に基づいて、データが既に存在する場合は UPDATE を行い、存在しない場合は INSERT を行います。
     * SQLiteでは INSERT INTO table (...) VALUES (...) ON CONFLICT (id) DO UPDATE SET ...; の構文が利用できます (SQLite 3.24.0以降)。
     * 更新時には、APIから取得した最新のデータでカラム（title, body, stateなど）を更新します。
     * fetched\_at カラムは、新規挿入時および更新時の両方で、現在のシステム時刻（ISO 8601形式のテキスト）で更新します。これにより、そのデータが最後に正常に取得・投入された日時を記録します。
3. **トランザクション:** 各リポジトリのデータ取得・投入処理全体、または各データタイプ（PRs, comments, review\_comments）ごとの投入処理を一つのトランザクションとして管理し、エラー発生時にはロールバックできるように設計します。
4. **最終取得日時の更新:** 各リポジトリのデータ取得・投入が正常に完了した後、repositories テーブルの該当リポジトリの fetched\_at カラムを現在のシステム時刻（ISO 8601形式のテキスト）で更新します。これにより、次回の取得基準日時を記録します。

### **6\. エラーハンドリング**

* **APIエラー:**
  * src/github\_api/client.py 内で、APIからのエラー応答（HTTPステータスコード 4xx, 5xx）を検知し、例外を発生させます。
  * **レート制限 (HTTP 403):** レスポンスヘッダーの X-RateLimit-Remaining が0の場合、X-RateLimit-Reset ヘッダーで示される時刻まで処理を一時停止（スリープ）し、その後リトライするロジックを実装します。
  * その他のAPIエラーについても、エラーコードやメッセージをログに詳細に出力します。
* **ネットワークエラー:** API呼び出し時の接続エラーなどを検知し、ログに出力します。簡易的なリトライ処理（数回試行するなど）を実装しても良いでしょう。
* **DBエラー:** データベースへの接続失敗、SQL実行エラーなどを検知し、ログに出力します。DB投入中のエラーの場合はトランザクションをロールバックします。
* **ログ出力:** Python標準の logging モジュールを使用します。処理の開始・終了、対象リポジトリ、取得件数、DB投入件数、発生したエラーの詳細などを、タイムスタンプ付きでログファイルまたは標準出力に記録します。ログレベル（DEBUG, INFO, WARNING, ERROR）を適切に使い分けます。

### **7\. 実行スクリプト (**scripts/fetch\_github\_data.py**)**

このスクリプトは、以下の流れで処理を実行します。

1. ロギング設定の初期化。
2. src/config/settings.py を使用して設定（リポジトリリスト、認証情報など）を読み込み。
3. src/db/database.py を使用してDB接続を確立。
4. 設定ファイルのリポジトリリストをループ。
5. 各リポジトリについて、以下の処理を try...except ブロックで囲み、エラー発生時も他のリポジトリの処理を継続できるようにする。
   * 対象リポジトリの最終取得日時を取得。
   * src/github\_api/fetcher.py を使用して、PR、Issueコメント、レビューコメントを取得。
   * src/data\_processing/processor.py を使用して、取得データを整形し、DBに投入（UPSERT）。
   * リポジトリの fetched\_at を更新。
   * 処理件数などをログに出力。
6. DB接続をクローズ。
7. 処理終了メッセージをログに出力。

この詳細設計に基づき、各モジュールのコードを実装することで、GitHub PRログの自動取得・蓄積機能を実現できます。
