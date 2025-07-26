import pytest
from sqlalchemy.exc import SQLAlchemyError
from src.db.database import Database
from src.db.models import Base
import os
from typing import Any, Dict, Generator
from pathlib import Path
import tempfile

from sqlalchemy.orm import declarative_base
from sqlalchemy import text # text をインポート
from datetime import datetime, timezone # datetimeとtimezoneをインポート

# プロジェクトルートからの相対パスでschema.sqlを指定
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '../../../src/db/schema.sql')

@pytest.fixture(scope="module")
def database() -> Generator[Database, None, None]:
    """モジュール単位の前処理：test_github_function.dbに対してDatabaseインスタンスを生成"""
    # 一時ディレクトリを作成してtest_github_function.dbを配置
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_github_function.db")
        db_config = {'db_path': db_path}
        db = Database(db_config)
        yield db

@pytest.fixture(autouse=True)
def setup_and_teardown_tables(database: Database) -> Generator[None, None, None]:
    """テスト関数単位の前処理・後処理：スキーマ適用とテーブル削除"""
    # 前処理：schema.sqlを適用してテーブルを作成
    try:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
    except FileNotFoundError:
        pytest.fail(f"Schema file not found at {SCHEMA_PATH}. "
                    "Ensure the path is correct relative to the test file.")

    with database.get_session() as session:
        for statement in schema_sql.split(';'):
            if statement.strip():
                try:
                    session.execute(text(statement))
                except SQLAlchemyError as e:
                    pytest.fail(f"Error executing schema statement: {statement}\nError: {e}")
        session.commit()
    
    # テスト実行
    yield
    
    # 後処理：テーブルをすべてドロップ
    database.drop_tables()

def test_create_engine_success(database: Database) -> None:
    """SQLite用エンジン作成の成功テスト"""
    assert database.engine is not None
    # SQLiteの接続文字列形式を確認
    assert str(database.engine.url).endswith("test_github_function.db")
    assert str(database.engine.url).startswith("sqlite:///")

def test_create_engine_default_path(tmp_path: Path) -> None:
    """db_pathがconfigにない場合にデフォルトパスでエンジンが作成されるかテスト"""
    # 一時的にカレントディレクトリを変更してテスト
    original_cwd = os.getcwd()
    test_dir = tmp_path / "cwd_test"
    test_dir.mkdir()
    os.chdir(test_dir)
    try:
        db = Database({}) # 空のconfigを渡す
        assert db.engine is not None
        # デフォルトの 'github_data.db' が使われることを確認（相対パス）
        assert str(db.engine.url) == "sqlite:///data/github_data.db"
    finally:
        os.chdir(original_cwd) # カレントディレクトリを元に戻す

def test_get_session(database: Database) -> None:
    """セッション取得のテスト"""
    with database.get_session() as session:
        assert session is not None
        # セッションがアクティブか確認
        assert session.is_active
        # 簡単なクエリを実行して接続を確認 (SQLAlchemy Core APIを使用)
        from sqlalchemy import text
        session.execute(text("SELECT 1"))

def test_get_session_rollback(database: Database, mocker: Any) -> None:
    """セッションロールバックのテスト"""
    # SQLAlchemyErrorを発生させるモックを設定
    mock_session = mocker.MagicMock()
    # session.commit() でエラーを発生させる
    mock_session.commit.side_effect = SQLAlchemyError("Test commit error")
    # rollbackとcloseもモックしておく
    mock_session.rollback = mocker.MagicMock()
    mock_session.close = mocker.MagicMock()

    # database.session_factoryがモックセッションを返すようにパッチ
    mocker.patch.object(database, 'session_factory', return_value=mock_session)

    # get_session内でcommit時にエラーが発生し、rollbackが呼ばれることを確認
    with pytest.raises(SQLAlchemyError, match="Test commit error"):
        with database.get_session():
             # このブロック内でエラーが発生する操作を行う必要はない
             # コンテキストマネージャの __exit__ で commit が呼ばれる
             pass

    # ロールバックが呼び出されたか確認
    mock_session.rollback.assert_called_once()
    # クローズが呼び出されたか確認
    mock_session.close.assert_called_once()

def test_create_tables(database: Database, mocker: Any) -> None:
    """テーブル作成のテスト（ORMモデルがBase.metadataに登録されていることも確認）"""
    # ORMモデルがBase.metadataに登録されていることを確認
    tables = set(Base.metadata.tables.keys())
    assert 'repositories' in tables
    assert 'pull_requests' in tables
    assert 'review_comments' in tables
    assert 'users' in tables
    # We test create_tables method directly, not its effect on schema (handled by fixture)
    mock_metadata = mocker.patch.object(Base, 'metadata')
    database.create_tables()
    # Base.metadata.create_all が呼ばれることを確認
    mock_metadata.create_all.assert_called_once_with(database.engine)

def test_create_tables_creates_all_tables(database: Database) -> None:
    """ORM定義に基づき全テーブルが作成されることをテスト"""
    # テーブルは既にsetup_and_teardown_tablesフィクスチャで作成されているので、
    # 存在確認のみ行う
    with database.get_session() as session:
        # repositories, pull_requests, review_comments, users テーブルが存在すること
        for table in ["repositories", "pull_requests", "review_comments", "users"]:
            result = session.execute(text(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"))
            assert result.fetchone() is not None, f"{table} テーブルが作成されていません"

def test_drop_tables(database: Database, mocker: Any) -> None:
    """テーブル削除のテスト"""
    # Base.metadata.drop_all が呼ばれることを確認
    mock_metadata = mocker.patch.object(Base, 'metadata')
    database.drop_tables()
    mock_metadata.drop_all.assert_called_once_with(database.engine)

# --- Tests for data retrieval methods ---

def test_get_repository_list_empty(database: Database) -> None:
    """データベースが空の場合に空のリストを返すことをテスト"""
    assert database.get_repository_list() == []

def test_get_repository_list_with_data(database: Database) -> None:
    """データが存在する場合にリポジトリリストを正しく返すことをテスト"""
    now_str = datetime.now(timezone.utc).isoformat()
    repo_data = [
        (1, 'owner1', 'repo1', 'url1', now_str, now_str, now_str),
        (2, 'owner2', 'repo2', 'url2', now_str, now_str, now_str),
    ]
    with database.get_session() as session:
        for repo in repo_data:
            session.execute(text("""
                INSERT INTO repositories (id, owner_login, name, url, created_at, updated_at, fetched_at)
                VALUES (:id, :owner, :name, :url, :created, :updated, :fetched)
            """), {'id': repo[0], 'owner': repo[1], 'name': repo[2], 'url': repo[3],
                   'created': repo[4], 'updated': repo[5], 'fetched': repo[6]})
        session.commit()

    result = database.get_repository_list()
    assert len(result) == 2
    assert {'id': 1, 'owner_login': 'owner1', 'name': 'repo1', 'url': 'url1'} in result
    assert {'id': 2, 'owner_login': 'owner2', 'name': 'repo2', 'url': 'url2'} in result

def test_get_pull_requests_no_prs(database: Database) -> None:
    """リポジトリにPRがない場合に空のリストを返すことをテスト"""
    now_str = datetime.now(timezone.utc).isoformat()
    with database.get_session() as session:
        session.execute(text("""
            INSERT INTO repositories (id, owner_login, name, url, created_at, updated_at, fetched_at)
            VALUES (1, 'owner1', 'repo1', 'url1', :now, :now, :now)
        """), {'now': now_str})
        session.commit()
    assert database.get_pull_requests_for_repository(repository_id=1) == []

def test_get_pull_requests_with_data(database: Database) -> None:
    """リポジトリにPRがある場合に正しくPRリストを返すことをテスト"""
    now_str = datetime.now(timezone.utc).isoformat()
    repo_id = 1
    pr_data = [
        (101, repo_id, 1, 'PR Title 1', 'userA', 'open', now_str, now_str, None, None, 'Body 1', 'url_pr1', 'api1', now_str),
        (102, repo_id, 2, 'PR Title 2', 'userB', 'closed', now_str, now_str, now_str, now_str, 'Body 2', 'url_pr2', 'api2', now_str),
    ]
    with database.get_session() as session:
        session.execute(text("INSERT INTO repositories VALUES (1, 'o', 'n', 'u', :n, :n, :n)"), {'n': now_str})
        for pr in pr_data:
            session.execute(text("""
                INSERT INTO pull_requests (id, repository_id, number, title, user_login, state, created_at,
                                         updated_at, closed_at, merged_at, body, url, api_url, fetched_at)
                VALUES (:id, :repo_id, :num, :title, :user, :state, :created, :updated, :closed, :merged, :body, :url, :api, :fetched)
            """), {'id': pr[0], 'repo_id': pr[1], 'num': pr[2], 'title': pr[3], 'user': pr[4], 'state': pr[5],
                   'created': pr[6], 'updated': pr[7], 'closed': pr[8], 'merged': pr[9], 'body': pr[10],
                   'url': pr[11], 'api': pr[12], 'fetched': pr[13]})
        session.commit()

    result = database.get_pull_requests_for_repository(repository_id=repo_id)
    assert len(result) == 2
    # Order is DESC by created_at, but they are same here, so order might vary by insertion. Check content.
    expected_pr1 = {'id': 101, 'number': 1, 'title': 'PR Title 1', 'user_login': 'userA', 'state': 'open',
                    'created_at': now_str, 'updated_at': now_str, 'url': 'url_pr1', 'body': 'Body 1'}
    expected_pr2 = {'id': 102, 'number': 2, 'title': 'PR Title 2', 'user_login': 'userB', 'state': 'closed',
                    'created_at': now_str, 'updated_at': now_str, 'url': 'url_pr2', 'body': 'Body 2'}

    # Convert list of dicts to set of tuples of items for order-agnostic comparison
    result_set = {tuple(sorted(d.items())) for d in result}
    expected_set = {tuple(sorted(expected_pr1.items())), tuple(sorted(expected_pr2.items()))}
    assert result_set == expected_set


def test_get_pull_requests_non_existent_repo(database: Database) -> None:
    """存在しないリポジトリIDの場合に空のリストを返すことをテスト"""
    assert database.get_pull_requests_for_repository(repository_id=99999) == []

def test_get_review_comments_no_comments(database: Database) -> None:
    """PRにコメントがない場合に空のリストを返すことをテスト"""
    now_str = datetime.now(timezone.utc).isoformat()
    with database.get_session() as session:
        session.execute(text("INSERT INTO repositories VALUES (1, 'o', 'n', 'u', :n, :n, :n)"), {'n': now_str})
        session.execute(text("""
            INSERT INTO pull_requests (id, repository_id, number, title, user_login, state, created_at,
                                     updated_at, body, url, api_url, fetched_at)
            VALUES (201, 1, 3, 'PR for comments test', 'userC', 'open', :now, :now, 'Body', 'url_pr3', 'api3', :now)
        """), {'now': now_str})
        session.commit()
    assert database.get_review_comments_for_pr(pull_request_id=201) == []

def test_get_review_comments_with_data(database: Database) -> None:
    """PRにコメントがある場合に正しくコメントリストを返すことをテスト"""
    now_str = datetime.now(timezone.utc).isoformat()
    pr_id = 202
    comments_data = [
        (301, pr_id, 'commenter1', 'This is a comment', now_str, now_str, 'api_c1', 'html_c1', now_str),
        (302, pr_id, 'commenter2', 'Another comment', now_str, now_str, 'api_c2', 'html_c2', now_str),
    ]
    with database.get_session() as session:
        session.execute(text("INSERT INTO repositories VALUES (1, 'o', 'n', 'u', :n, :n, :n)"), {'n': now_str})
        session.execute(text("""
            INSERT INTO pull_requests (id, repository_id, number, title, user_login, state, created_at,
                                     updated_at, body, url, api_url, fetched_at)
            VALUES (:pr_id, 1, 4, 'PR for comments data', 'userD', 'open', :now, :now, 'Body PR4', 'url_pr4', 'api4', :now)
        """), {'pr_id': pr_id, 'now': now_str})
        for c in comments_data:
            session.execute(text("""
                INSERT INTO review_comments (id, pull_request_id, user_login, body, created_at, updated_at,
                                           api_url, html_url, fetched_at)
                VALUES (:id, :pr_id, :user, :body, :created, :updated, :api, :html, :fetched)
            """), {'id': c[0], 'pr_id': c[1], 'user': c[2], 'body': c[3], 'created': c[4],
                   'updated': c[5], 'api': c[6], 'html': c[7], 'fetched': c[8]})
        session.commit()

    result = database.get_review_comments_for_pr(pull_request_id=pr_id)
    assert len(result) == 2
    expected_c1 = {'user_login': 'commenter1', 'body': 'This is a comment', 'created_at': now_str, 'html_url': 'html_c1'}
    expected_c2 = {'user_login': 'commenter2', 'body': 'Another comment', 'created_at': now_str, 'html_url': 'html_c2'}

    # Order is ASC by created_at, but they are same here. Convert to set for comparison.
    result_set = {tuple(sorted(d.items())) for d in result}
    expected_set = {tuple(sorted(expected_c1.items())), tuple(sorted(expected_c2.items()))}
    assert result_set == expected_set


def test_get_review_comments_non_existent_pr(database: Database) -> None:
    """存在しないPR IDの場合に空のリストを返すことをテスト"""
    assert database.get_review_comments_for_pr(pull_request_id=88888) == []
