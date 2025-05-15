"""
データベース接続とセッション管理を行うモジュール
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import logging
import os

# ロギングの設定
logger = logging.getLogger(__name__)

# ベースクラスの作成
Base = declarative_base()

class Database:
    def __init__(self, config: dict):
        """データベース接続の初期化"""
        self.config = config
        # db_path を取得（なければデフォルト値）
        db_path = self.config.get('db_path', 'github_data.db')
        # self.config にもデフォルト値を反映させておく（後続処理で使う場合）
        self.config['db_path'] = db_path

        # SQLiteファイルが格納されるディレクトリが存在しない場合は作成する
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"データベースディレクトリを作成しました: {db_dir}")
        self.engine = self._create_engine()
        self.session_factory = scoped_session(sessionmaker(bind=self.engine))

    def _create_engine(self):
        """SQLAlchemyエンジンの作成"""
        try:
            # SQLiteの接続文字列を使用
            # configからdb_pathを取得 (__init__でデフォルト値が設定済み)
            db_path = self.config['db_path']
            connection_string = f"sqlite:///{db_path}"
            logger.info(f"データベースに接続します: {connection_string}")
            return create_engine(connection_string)
        except Exception as e:
            logger.error(f"データベースエンジンの作成に失敗しました: {e}")
            raise

    @contextmanager
    def get_session(self):
        """セッションの取得（コンテキストマネージャ）"""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"セッション処理中にエラーが発生しました: {e}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """テーブルの作成"""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("テーブルの作成が完了しました")
        except Exception as e:
            logger.error(f"テーブルの作成に失敗しました: {e}")
            raise

    def drop_tables(self):
        """テーブルの削除"""
        try:
            Base.metadata.drop_all(self.engine)
            logger.info("テーブルの削除が完了しました")
        except Exception as e:
            logger.error(f"テーブルの削除に失敗しました: {e}")
            raise 