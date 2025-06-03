"""
データベース接続とセッション管理を行うモジュール
"""
from sqlalchemy import create_engine, text
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

    def get_repository_list(self) -> list[dict]:
        """
        データベースからリポジトリのリストを取得します。

        Returns:
            list[dict]: リポジトリ情報 (id, owner_login, name, url) のリスト。
                        エラーが発生した場合は空のリストを返します。
        """
        logger.info("リポジトリリストの取得を開始します")
        try:
            with self.get_session() as session:
                query = text("SELECT id, owner_login, name, url FROM repositories;")
                result = session.execute(query)
                repositories = [
                    {
                        "id": row.id,
                        "owner_login": row.owner_login,
                        "name": row.name,
                        "url": row.url
                    } for row in result
                ]
                logger.info(f"{len(repositories)}件のリポジトリを取得しました")
                return repositories
        except Exception as e:
            logger.error(f"リポジトリリストの取得中にエラーが発生しました: {e}")
            return []

    def get_pull_requests_for_repository(self, repository_id: int) -> list[dict]:
        """
        指定されたリポジトリIDのプルリクエストリストをデータベースから取得します。

        Args:
            repository_id (int): プルリクエストを取得するリポジトリのID。

        Returns:
            list[dict]: プルリクエスト情報の辞書のリスト。
                        カラム: number, title, user_login, state, created_at, updated_at, url, body
                        エラーが発生した場合は空のリストを返します。
        """
        logger.info(f"リポジトリID {repository_id} のプルリクエスト取得を開始します")
        try:
            with self.get_session() as session:
                query = text("""
                    SELECT id, number, title, user_login, state, created_at, updated_at, url, body
                    FROM pull_requests
                    WHERE repository_id = :repo_id
                    ORDER BY created_at DESC;
                """)
                result = session.execute(query, {"repo_id": repository_id})
                pull_requests = [
                    {
                        "id": row.id, # PRのIDも取得しておく（コメント取得時に使うため）
                        "number": row.number,
                        "title": row.title,
                        "user_login": row.user_login,
                        "state": row.state,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                        "url": row.url,
                        "body": row.body
                    } for row in result
                ]
                logger.info(f"{len(pull_requests)}件のプルリクエストを取得しました (リポジトリID: {repository_id})")
                return pull_requests
        except Exception as e:
            logger.error(f"プルリクエストの取得中にエラーが発生しました (リポジトリID: {repository_id}): {e}")
            return []

    def get_review_comments_for_pr(self, pull_request_id: int) -> list[dict]:
        """
        指定されたプルリクエストIDのレビューコメントリストをデータベースから取得します。

        Args:
            pull_request_id (int): レビューコメントを取得するプルリクエストのID。

        Returns:
            list[dict]: レビューコメント情報の辞書のリスト。
                        カラム: user_login, body, created_at, html_url
                        エラーが発生した場合は空のリストを返します。
        """
        logger.info(f"プルリクエストID {pull_request_id} のレビューコメント取得を開始します")
        try:
            with self.get_session() as session:
                query = text("""
                    SELECT user_login, body, created_at, html_url
                    FROM review_comments
                    WHERE pull_request_id = :pr_id
                    ORDER BY created_at ASC;
                """)
                result = session.execute(query, {"pr_id": pull_request_id})
                comments = [
                    {
                        "user_login": row.user_login,
                        "body": row.body,
                        "created_at": row.created_at,
                        "html_url": row.html_url
                    } for row in result
                ]
                logger.info(f"{len(comments)}件のレビューコメントを取得しました (プルリクエストID: {pull_request_id})")
                return comments
        except Exception as e:
            logger.error(f"レビューコメントの取得中にエラーが発生しました (プルリクエストID: {pull_request_id}): {e}")
            return []