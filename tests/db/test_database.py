import pytest
from sqlalchemy.exc import SQLAlchemyError
from src.db.database import Database, Base
import os
from typing import Any, Generator
from pathlib import Path

# sqlalchemy.orm の declarative_base は非推奨ではないですが、
# 元のコードに合わせてコメントアウトしておきます。
# from sqlalchemy.orm import declarative_base

class TestDatabase:

    # tmp_path フィクスチャを使用して一時ディレクトリを作成
    @pytest.fixture
    def db_path(self, tmp_path: Path) -> str:
        """一時的なSQLiteデータベースファイルのパスを生成"""
        # 一時ディレクトリ内に test_db ディレクトリを作成
        db_dir = tmp_path / "test_db"
        # db_dir.mkdir() # __init__ で作成されるはずなので、ここでは作成しない
        return str(db_dir / "test_github_data.db")

    @pytest.fixture
    def db_config(self, db_path: str) -> dict[str, str]:
        """テスト用のSQLiteデータベース設定"""
        return {'db_path': db_path}

    @pytest.fixture
    def database(self, db_config: dict[str, str]) -> Generator[Database, None, None]:
        """テスト用のデータベースインスタンス"""
        # Databaseインスタンス作成時にディレクトリも作成される
        db = Database(db_config)
        # テスト用にテーブルを作成（必要に応じて）
        # db.create_tables()
        yield db
        # テスト後処理（必要ならファイルを削除するなどだが、tmp_pathが自動で行う）
        # db.drop_tables()
        # if os.path.exists(db_config['db_path']):
        #     os.remove(db_config['db_path'])

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

    def test_create_engine_success(self, database: Database, db_path: str) -> None:
        """SQLite用エンジン作成の成功テスト"""
        assert database.engine is not None
        # SQLiteの接続文字列形式を確認
        # WindowsとLinuxでパス区切り文字が異なるため、os.path.normpathで正規化して比較
        # または、単純にendswithで比較する
        # assert str(database.engine.url) == f"sqlite:///{os.path.normpath(db_path)}"
        assert str(database.engine.url).endswith(os.path.basename(db_path))
        assert str(database.engine.url).startswith("sqlite:///")

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

    def test_create_tables(self, database: Database, mocker: Any) -> None:
        """テーブル作成のテスト"""
        # Base.metadata.create_all が呼ばれることを確認
        mock_metadata = mocker.patch.object(Base, 'metadata')
        database.create_tables()
        mock_metadata.create_all.assert_called_once_with(database.engine)

    def test_drop_tables(self, database: Database, mocker: Any) -> None:
        """テーブル削除のテスト"""
        # Base.metadata.drop_all が呼ばれることを確認
        mock_metadata = mocker.patch.object(Base, 'metadata')
        database.drop_tables()
        mock_metadata.drop_all.assert_called_once_with(database.engine) 