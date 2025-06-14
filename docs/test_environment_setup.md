# テスト環境構築手順書

## 1. ディレクトリ構造の作成

### 1.1 基本ディレクトリ構造の作成
```bash
# テスト用ディレクトリ構造の作成
mkdir -p tests/unit/{db,github_api,config}
mkdir -p tests/integration/{e2e,performance,security}
mkdir -p tests/mocks/github_api
mkdir -p tests/integration/db/data
mkdir -p tests/integration/config
mkdir -p tests/integration/logs
mkdir -p tests/utils
```

## 2. モックの作成

### 2.1 GitHub APIモックの作成
```python
# tests/mocks/github_api/responses.py
MOCK_PR_RESPONSE = {
    "number": 1,
    "title": "テストPR",
    "state": "open",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "body": "テストPRの本文",
    "user": {"login": "testuser"},
    "html_url": "https://github.com/test/repo/pull/1"
}

MOCK_COMMENT_RESPONSE = {
    "id": 1,
    "body": "テストコメント",
    "user": {"login": "reviewer"},
    "created_at": "2024-01-01T01:00:00Z",
    "html_url": "https://github.com/test/repo/pull/1#issuecomment-1"
}

# エラーレスポンス
RATE_LIMIT_ERROR = {
    "message": "API rate limit exceeded",
    "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
}

NOT_FOUND_ERROR = {
    "message": "Not Found",
    "documentation_url": "https://docs.github.com/rest"
}
```

### 2.2 モッククライアントの実装
```python
# tests/mocks/github_api/client.py
from unittest.mock import Mock
from .responses import MOCK_PR_RESPONSE, MOCK_COMMENT_RESPONSE

class MockGitHubClient:
    def __init__(self):
        self.mock = Mock()
        self.setup_mock_responses()
    
    def setup_mock_responses(self):
        self.mock.get_pull_requests.return_value = [MOCK_PR_RESPONSE]
        self.mock.get_review_comments.return_value = [MOCK_COMMENT_RESPONSE]
        
    def get_pull_requests(self, repo, state=None):
        return self.mock.get_pull_requests(repo, state)
        
    def get_review_comments(self, repo, pr_number):
        return self.mock.get_review_comments(repo, pr_number)
```

## 3. 統合テスト用データベースの構築

### 3.1 テスト用データベースの作成
```bash
# 統合テスト用データベースの作成
touch tests/integration/db/data/test.db
```

### 3.2 テストデータの準備
```python
# tests/integration/db/data/sample_data.py
SAMPLE_PRS = [
    {
        "number": 1,
        "title": "テストPR1",
        "state": "open",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "body": "テストPRの本文1",
        "user": {"login": "testuser1"},
        "html_url": "https://github.com/test/repo/pull/1"
    },
    {
        "number": 2,
        "title": "テストPR2",
        "state": "closed",
        "created_at": "2024-01-03T00:00:00Z",
        "updated_at": "2024-01-04T00:00:00Z",
        "body": "テストPRの本文2",
        "user": {"login": "testuser2"},
        "html_url": "https://github.com/test/repo/pull/2"
    }
]

SAMPLE_COMMENTS = [
    {
        "id": 1,
        "body": "テストコメント1",
        "user": {"login": "reviewer1"},
        "created_at": "2024-01-01T01:00:00Z",
        "html_url": "https://github.com/test/repo/pull/1#issuecomment-1"
    },
    {
        "id": 2,
        "body": "テストコメント2",
        "user": {"login": "reviewer2"},
        "created_at": "2024-01-03T01:00:00Z",
        "html_url": "https://github.com/test/repo/pull/2#issuecomment-2"
    }
]
```

### 3.3 データベース初期化スクリプト
```python
# tests/integration/db/init_db.py
import sqlite3
import os
from .data.sample_data import SAMPLE_PRS, SAMPLE_COMMENTS

def init_test_database():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'test.db')
    
    # データベース接続
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # スキーマの適用
    with open('src/db/schema.sql', 'r') as f:
        cursor.executescript(f.read())
    
    # サンプルデータの投入
    for pr in SAMPLE_PRS:
        cursor.execute("""
            INSERT INTO pull_requests (
                number, title, state, created_at, updated_at,
                body, author, html_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pr['number'], pr['title'], pr['state'],
            pr['created_at'], pr['updated_at'],
            pr['body'], pr['user']['login'], pr['html_url']
        ))
    
    for comment in SAMPLE_COMMENTS:
        cursor.execute("""
            INSERT INTO review_comments (
                id, body, author, created_at, html_url
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            comment['id'], comment['body'],
            comment['user']['login'],
            comment['created_at'], comment['html_url']
        ))
    
    conn.commit()
    conn.close()
```

## 4. 統合テスト用設定の準備

### 4.1 テスト用設定ファイル
```yaml
# tests/integration/config/test_config.yaml
repositories:
  - test/repo1
  - test/repo2

db_path: tests/integration/db/data/test.db

fetch_settings:
  initial_lookback_days: 1
  max_prs_per_request: 10
  request_interval: 1

logging:
  level: DEBUG
  file: tests/integration/logs/test.log
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### 4.2 テスト用環境変数
```bash
# tests/integration/config/test.env
GITHUB_TOKEN=test_token
TEST_MODE=true
DB_PATH=tests/integration/db/data/test.db
```

## 5. テスト環境セットアップスクリプト

### 5.1 セットアップスクリプト
```python
# tests/utils/setup_test_env.py
import os
import shutil
from integration.db.init_db import init_test_database

def setup_test_environment():
    # ディレクトリ作成
    os.makedirs('tests/integration/logs', exist_ok=True)
    
    # データベース初期化
    init_test_database()
    
    # 設定ファイルのコピー
    shutil.copy(
        'tests/integration/config/test_config.yaml',
        'config.yaml'
    )
    
    # 環境変数の設定
    with open('tests/integration/config/test.env', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

if __name__ == '__main__':
    setup_test_environment()
```

## 6. セットアップ手順

1. 環境のセットアップ
```bash
# 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# または
.venv\Scripts\activate  # Windows

# 依存パッケージのインストール
pip install -r requirements.txt
```

2. テスト環境の構築
```bash
# テスト環境のセットアップ
python tests/utils/setup_test_env.py
```

## 7. セットアップの確認

以下の点を確認してください：

1. ディレクトリ構造が正しく作成されているか
   - `tests/unit/`
   - `tests/integration/`
   - `tests/mocks/`
   - `tests/utils/`

2. モックが正しく実装されているか
   - `tests/mocks/github_api/responses.py`
   - `tests/mocks/github_api/client.py`

3. データベースが正しく初期化されているか
   - `tests/integration/db/data/test.db`が存在するか
   - サンプルデータが投入されているか

4. 設定ファイルが正しく配置されているか
   - `tests/integration/config/test_config.yaml`
   - `tests/integration/config/test.env`

5. ログディレクトリが作成されているか
   - `tests/integration/logs/` 