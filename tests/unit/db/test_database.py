import pytest
from sqlalchemy.exc import SQLAlchemyError
from src.db.database import Database, Base
import os
from typing import Any, Dict, Generator
from pathlib import Path

# sqlalchemy.orm の declarative_base は非推奨ではないですが、
# 元のコードに合わせてコメントアウトしておきます。
# from sqlalchemy.orm import declarative_base
from sqlalchemy import text # text をインポート
from datetime import datetime, timezone # datetimeとtimezoneをインポート

# プロジェクトルートからの相対パスでschema.sqlを指定
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '../../../src/db/schema.sql')

class TestDatabase:

    # tmp_path フィクスチャを使用して一時ディレクトリを作成
    @pytest.fixture
    def db_path(self, tmp_path: Path) -> str:
        """一時的なSQLiteデータベースファイルのパスを生成"""
        db_dir = tmp_path / "test_db_func" # Use a different dir for function scope
        # db_dir.mkdir(exist_ok=True) # Ensure directory exists, __init__ should handle it
        return str(db_dir / "test_github_data_func.db")

    @pytest.fixture(scope="function")
    def db_config(self, db_path: str) -> Dict[str, str]:
        """テスト用のSQLiteデータベース設定"""
        return {'db_path': db_path}

    @pytest.fixture(scope="function")
    def database(self, db_config: Dict[str, str]) -> Generator[Database, None, None]:
        """テスト用のデータベースインスタンス（スキーマ適用済み）"""

        db = Database(db_config)

        # スキーマファイル読み込みと実行
        try:
            with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
        except FileNotFoundError:
            pytest.fail(f"Schema file not found at {SCHEMA_PATH}. "
                        "Ensure the path is correct relative to the test file.")

        with db.get_session() as session:
            for statement in schema_sql.split(';'):
                if statement.strip():
                    try:
                        session.execute(text(statement))
                    except SQLAlchemyError as e:
                        # For "CREATE TABLE IF NOT EXISTS", errors might be ignorable
                        # if tables are somehow persisting across test runs (though they shouldn't with tmp_path)
                        # However, other errors should fail the test.
                        # For simplicity in this context, we'll let it fail on any SQL error during setup.
                        pytest.fail(f"Error executing schema statement: {statement}\nError: {e}")
            session.commit()
        yield db
        # tmp_path should handle cleanup of the db file

    @pytest.mark.usefixtures('database')
    def test_init_creates_directory(self, db_path: str) -> None:
        """__init__ がデータベースファイル用のディレクトリを作成することを確認"""
        db_dir = os.path.dirname(db_path)
        # ディレクトリが存在しない状態でインスタンス化
        if os.path.exists(db_dir):
             # 安全のため、もし存在していたら削除（通常はtmp_pathで不要）
             os.rmdir(db_dir)
        assert not os.path.exists(db_dir)
        Database({'db_path': db_path})
        # ディレクトリが作成されたことを確認
        assert os.path.exists(db_dir)

    @pytest.mark.usefixtures('database')
    def test_create_engine_success(self, database: Database, db_path: str) -> None:
        """SQLite用エンジン作成の成功テスト"""
        assert database.engine is not None
        # SQLiteの接続文字列形式を確認
        # WindowsとLinuxでパス区切り文字が異なるため、os.path.normpathで正規化して比較
        # または、単純にendswithで比較する
        # assert str(database.engine.url) == f"sqlite:///{os.path.normpath(db_path)}"
        assert str(database.engine.url).endswith(os.path.basename(db_path))
        assert str(database.engine.url).startswith("sqlite:///")

    @pytest.mark.usefixtures('database')
    def test_create_engine_default_path(self, tmp_path: Path) -> None:
        """db_pathがconfigにない場合にデフォルトパスでエンジンが作成されるかテスト"""
        # デフォルトパスの親ディレクトリを作成しておく（必要ない場合もある）
        # default_dir = tmp_path / "default_db_dir"
        # default_dir.mkdir()
        # 一時的にカレントディレクトリを変更してテスト
        original_cwd = os.getcwd()
        test_dir = tmp_path / "cwd_test"
        test_dir.mkdir()
        os.chdir(test_dir)
        try:
            db = Database({}) # 空のconfigを渡す
            assert db.engine is not None
            # デフォルトの 'github_data.db' が使われることを確認（相対パス）
            assert str(db.engine.url) == "sqlite:///github_data.db"
            # デフォルトファイルが実際に作成されるか確認（エンジン作成だけではされない）
            # テーブル作成などを試みる
            # assert not default_db_file.exists()
            # db.create_tables() # これを実行するとファイルが作られる
            # assert default_db_file.exists()
        finally:
            os.chdir(original_cwd) # カレントディレクトリを元に戻す
            # tryブロックでファイルが作成された場合に備えて削除
            pass

    @pytest.mark.usefixtures('database')
    def test_get_session(self, database: Database) -> None:
        """セッション取得のテスト"""
        with database.get_session() as session:
            assert session is not None
            # 'closed' 属性は存在しないため削除
            # assert not session.closed
            # 代わりに is_active を使うか、クエリ実行で確認
            assert session.is_active # セッションがアクティブか確認
            # 簡単なクエリを実行して接続を確認 (SQLAlchemy Core APIを使用)
            from sqlalchemy import text
            session.execute(text("SELECT 1"))

    @pytest.mark.usefixtures('database')
    def test_get_session_rollback(self, database: Database, mocker: Any) -> None:
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

    @pytest.mark.usefixtures('database')
    def test_create_tables(self, database: Database, mocker: Any, db_config: Dict[str, str]) -> None:
        """テーブル作成のテスト（ORMモデルがBase.metadataに登録されていることも確認）"""
        # Base.metadata.create_all が呼ばれることを確認
        mock_metadata = mocker.patch.object(Base, 'metadata')
        # ORMモデルがBase.metadataに登録されていることを確認
        from src.db.models import Repository, PullRequest, ReviewComment, User
        tables = set(Base.metadata.tables.keys())
        assert 'repositories' in tables
        assert 'pull_requests' in tables
        assert 'review_comments' in tables
        assert 'users' in tables
        # We test create_tables method directly, not its effect on schema (handled by fixture)
        db_instance_for_mock_test = Database(db_config) # Use a separate instance for this mock test
        db_instance_for_mock_test.create_tables()
        mock_metadata.create_all.assert_called_once_with(db_instance_for_mock_test.engine)

    @pytest.mark.usefixtures('database')
    def test_create_tables_creates_all_tables(self, tmp_path):
        """ORM定義に基づき全テーブルが作成されることをテスト"""
        db_path = tmp_path / "test_create_tables.db"
        db = Database({'db_path': str(db_path)})
        db.create_tables()
        # SQLiteのメタデータを直接確認
        import sqlite3
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        # repositories, pull_requests, review_comments, users テーブルが存在すること
        for table in ["repositories", "pull_requests", "review_comments", "users"]:
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            assert cur.fetchone() is not None, f"{table} テーブルが作成されていません"
        con.close()

    def test_drop_tables(self, database: Database, mocker: Any, db_config: Dict[str, str]) -> None:
        """テーブル削除のテスト"""
        # Base.metadata.drop_all が呼ばれることを確認
        mock_metadata = mocker.patch.object(Base, 'metadata')
        # We test drop_tables method directly
        db_instance_for_mock_test = Database(db_config) # Use a separate instance for this mock test
        db_instance_for_mock_test.drop_tables()
        mock_metadata.drop_all.assert_called_once_with(db_instance_for_mock_test.engine)

    # --- Tests for data retrieval methods ---

    @pytest.mark.usefixtures('database')
    def test_get_repository_list_empty(self, database: Database) -> None:
        """データベースが空の場合に空のリストを返すことをテスト"""
        assert database.get_repository_list() == []

    @pytest.mark.usefixtures('database')
    def test_get_repository_list_with_data(self, database: Database) -> None:
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

    @pytest.mark.usefixtures('database')
    def test_get_pull_requests_no_prs(self, database: Database) -> None:
        """リポジトリにPRがない場合に空のリストを返すことをテスト"""
        now_str = datetime.now(timezone.utc).isoformat()
        with database.get_session() as session:
            session.execute(text("""
                INSERT INTO repositories (id, owner_login, name, url, created_at, updated_at, fetched_at)
                VALUES (1, 'owner1', 'repo1', 'url1', :now, :now, :now)
            """), {'now': now_str})
            session.commit()
        assert database.get_pull_requests_for_repository(repository_id=1) == []

    @pytest.mark.usefixtures('database')
    def test_get_pull_requests_with_data(self, database: Database) -> None:
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


    @pytest.mark.usefixtures('database')
    def test_get_pull_requests_non_existent_repo(self, database: Database) -> None:
        """存在しないリポジトリIDの場合に空のリストを返すことをテスト"""
        assert database.get_pull_requests_for_repository(repository_id=99999) == []

    @pytest.mark.usefixtures('database')
    def test_get_review_comments_no_comments(self, database: Database) -> None:
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

    @pytest.mark.usefixtures('database')
    def test_get_review_comments_with_data(self, database: Database) -> None:
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


    @pytest.mark.usefixtures('database')
    def test_get_review_comments_non_existent_pr(self, database: Database) -> None:
        """存在しないPR IDの場合に空のリストを返すことをテスト"""
        assert database.get_review_comments_for_pr(pull_request_id=88888) == []
