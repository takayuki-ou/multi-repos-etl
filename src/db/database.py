"""
データベース接続とセッション管理を行うモジュール
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import logging
import os
from datetime import datetime
from typing import Any
from src.db.models import Base

# --- ここでmodelsをimportしてBase.metadataにテーブル定義を登録 ---
from . import models

# ロギングの設定
logger = logging.getLogger(__name__)

# ベースクラスの作成

class Database:
    def __init__(self, config: dict[str, str]):
        """データベース接続の初期化"""
        # Store the original config if needed elsewhere, but avoid modifying it.
        # self.config = config

        # db_path を取得（なければデフォルト値）
        # Use .get from the original config for safety.
        db_path_from_config: str = config.get('db_path', 'github_data.db')
        self.resolved_db_path: str = db_path_from_config # Store resolved path separately

        # SQLiteファイルが格納されるディレクトリが存在しない場合は作成する
        # Use self.resolved_db_path for directory creation and engine
        db_dir: str = os.path.dirname(self.resolved_db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"データベースディレクトリを作成しました: {db_dir}")
        self.engine = self._create_engine()
        self.session_factory = scoped_session(sessionmaker(bind=self.engine))

    def _create_engine(self):
        """SQLAlchemyエンジンの作成"""
        try:
            # SQLiteの接続文字列を使用
            # Use the resolved_db_path attribute
            connection_string = f"sqlite:///{self.resolved_db_path}"
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

    def get_repository_list(self) -> list[dict[str, Any]]:
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

    def get_pull_requests_for_repository(self, repository_id: int) -> list[dict[str, Any]]:
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

    def get_review_comments_for_pr(self, pull_request_id: int) -> list[dict[str, Any]]:
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

    def upsert_repository(self, repo_data: dict[str, Any]) -> bool:
        """
        リポジトリ情報をUPSERTします。

        Args:
            repo_data (dict): リポジトリ情報の辞書。

        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse。
        """
        logger.info(f"リポジトリのUPSERT開始: {repo_data.get('name')}")
        try:
            with self.get_session() as session:
                owner_login = repo_data.get('owner', {}).get('login')
                name = repo_data.get('name')

                # 既存のリポジトリをチェック
                existing_repo = session.execute(text("""
                    SELECT id FROM repositories
                    WHERE owner_login = :owner AND name = :name
                """), {"owner": owner_login, "name": name}).fetchone()

                current_time = datetime.now().isoformat()

                if existing_repo:
                    # UPDATE
                    session.execute(text("""
                        UPDATE repositories
                        SET url = :url, updated_at = :updated_at, fetched_at = :fetched_at
                        WHERE owner_login = :owner AND name = :name
                    """), {
                        "url": repo_data.get('html_url'),
                        "updated_at": repo_data.get('updated_at'),
                        "fetched_at": current_time,
                        "owner": owner_login,
                        "name": name
                    })
                else:
                    # INSERT
                    session.execute(text("""
                        INSERT INTO repositories
                        (owner_login, name, url, created_at, updated_at, fetched_at)
                        VALUES (:owner, :name, :url, :created_at, :updated_at, :fetched_at)
                    """), {
                        "owner": owner_login,
                        "name": name,
                        "url": repo_data.get('html_url'),
                        "created_at": repo_data.get('created_at'),
                        "updated_at": repo_data.get('updated_at'),
                        "fetched_at": current_time
                    })

                logger.info(f"リポジトリのUPSERT完了: {repo_data.get('name')}")
                return True
        except Exception as e:
            logger.error(f"リポジトリのUPSERT中にエラーが発生しました: {e}")
            return False

    def upsert_pull_request(self, pr_data: dict[str, Any], repository_id: int) -> bool:
        """
        プルリクエスト情報をUPSERTします。

        Args:
            pr_data (dict): プルリクエスト情報の辞書。
            repository_id (int): リポジトリのDB ID。

        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse。
        """
        logger.info(f"プルリクエストのUPSERT開始: #{pr_data.get('number')}")
        try:
            with self.get_session() as session:
                number = pr_data.get('number')

                # 既存のプルリクエストをチェック
                existing_pr = session.execute(text("""
                    SELECT id FROM pull_requests
                    WHERE repository_id = :repo_id AND number = :number
                """), {"repo_id": repository_id, "number": number}).fetchone()

                current_time = datetime.now().isoformat()

                if existing_pr:
                    # UPDATE
                    session.execute(text("""
                        UPDATE pull_requests
                        SET title = :title, body = :body, state = :state,
                            updated_at = :updated_at, closed_at = :closed_at,
                            merged_at = :merged_at, url = :url, fetched_at = :fetched_at
                        WHERE repository_id = :repo_id AND number = :number
                    """), {
                        "title": pr_data.get('title'),
                        "body": pr_data.get('body'),
                        "state": pr_data.get('state'),
                        "updated_at": pr_data.get('updated_at'),
                        "closed_at": pr_data.get('closed_at'),
                        "merged_at": pr_data.get('merged_at'),
                        "url": pr_data.get('html_url'),
                        "fetched_at": current_time,
                        "repo_id": repository_id,
                        "number": number
                    })
                else:
                    # INSERT
                    session.execute(text("""
                        INSERT INTO pull_requests
                        (repository_id, number, title, user_login, state, created_at,
                         updated_at, closed_at, merged_at, body, url, api_url, fetched_at)
                        VALUES (:repo_id, :number, :title, :user_login, :state, :created_at,
                                :updated_at, :closed_at, :merged_at, :body, :url, :api_url, :fetched_at)
                    """), {
                        "repo_id": repository_id,
                        "number": number,
                        "title": pr_data.get('title'),
                        "user_login": pr_data.get('user', {}).get('login'),
                        "state": pr_data.get('state'),
                        "created_at": pr_data.get('created_at'),
                        "updated_at": pr_data.get('updated_at'),
                        "closed_at": pr_data.get('closed_at'),
                        "merged_at": pr_data.get('merged_at'),
                        "body": pr_data.get('body'),
                        "url": pr_data.get('html_url'),
                        "api_url": pr_data.get('url'),
                        "fetched_at": current_time
                    })

                logger.info(f"プルリクエストのUPSERT完了: #{pr_data.get('number')}")
                return True
        except Exception as e:
            logger.error(f"プルリクエストのUPSERT中にエラーが発生しました: {e}")
            return False

    def upsert_review_comment(self, comment_data: dict[str, Any], pull_request_id: int) -> bool:
        """
        レビューコメント情報をUPSERTします。

        Args:
            comment_data (dict): レビューコメント情報の辞書。
            pull_request_id (int): プルリクエストのDB ID。

        Returns:
            bool: 成功した場合はTrue、失敗した場合はFalse。
        """
        logger.info(f"レビューコメントのUPSERT開始: ID {comment_data.get('id')}")
        try:
            with self.get_session() as session:
                comment_html_url = comment_data.get('html_url')

                # 既存のレビューコメントをチェック（html_urlで判定）
                existing_comment = session.execute(text("""
                    SELECT id FROM review_comments
                    WHERE pull_request_id = :pr_id AND html_url = :html_url
                """), {"pr_id": pull_request_id, "html_url": comment_html_url}).fetchone()

                current_time = datetime.now().isoformat()

                if existing_comment:
                    # UPDATE
                    session.execute(text("""
                        UPDATE review_comments
                        SET body = :body, updated_at = :updated_at,
                            path = :path, position = :position, fetched_at = :fetched_at
                        WHERE pull_request_id = :pr_id AND html_url = :html_url
                    """), {
                        "body": comment_data.get('body'),
                        "updated_at": comment_data.get('updated_at'),
                        "path": comment_data.get('path'),
                        "position": comment_data.get('position'),
                        "fetched_at": current_time,
                        "pr_id": pull_request_id,
                        "html_url": comment_html_url
                    })
                else:
                    # INSERT
                    session.execute(text("""
                        INSERT INTO review_comments
                        (pull_request_id, user_login, body, created_at, updated_at,
                         api_url, html_url, diff_hunk, path, position, original_position,
                         commit_id, fetched_at)
                        VALUES (:pr_id, :user_login, :body, :created_at, :updated_at,
                                :api_url, :html_url, :diff_hunk, :path, :position,
                                :original_position, :commit_id, :fetched_at)
                    """), {
                        "pr_id": pull_request_id,
                        "user_login": comment_data.get('user', {}).get('login'),
                        "body": comment_data.get('body'),
                        "created_at": comment_data.get('created_at'),
                        "updated_at": comment_data.get('updated_at'),
                        "api_url": comment_data.get('url'),
                        "html_url": comment_html_url,
                        "diff_hunk": comment_data.get('diff_hunk'),
                        "path": comment_data.get('path'),
                        "position": comment_data.get('position'),
                        "original_position": comment_data.get('original_position'),
                        "commit_id": comment_data.get('commit_id'),
                        "fetched_at": current_time
                    })

                logger.info(f"レビューコメントのUPSERT完了: ID {comment_data.get('id')}")
                return True
        except Exception as e:
            logger.error(f"レビューコメントのUPSERT中にエラーが発生しました: {e}")
            return False

    def get_repository_by_full_name(self, owner: str, name: str) -> dict[str, Any] | None:
        """
        owner/name形式でリポジトリを取得します。

        Args:
            owner (str): リポジトリのオーナー名。
            name (str): リポジトリ名。

        Returns:
            dict | None: リポジトリ情報の辞書。見つからない場合はNone。
        """
        logger.info(f"リポジトリ取得開始: {owner}/{name}")
        try:
            with self.get_session() as session:
                query = text("""
                    SELECT id, owner_login, name, url, created_at, updated_at, fetched_at
                    FROM repositories
                    WHERE owner_login = :owner AND name = :name
                """)
                result = session.execute(query, {"owner": owner, "name": name})
                row = result.fetchone()
                if row:
                    return {
                        "id": row.id,
                        "owner_login": row.owner_login,
                        "name": row.name,
                        "url": row.url,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                        "fetched_at": row.fetched_at
                    }
                return None
        except Exception as e:
            logger.error(f"リポジトリ取得中にエラーが発生しました: {e}")
            return None

    def get_pull_requests_with_filters(self, repository_id: int, 
                                     start_date: datetime = None,
                                     end_date: datetime = None,
                                     author: str = None) -> list[dict[str, Any]]:
        """
        フィルタリング条件に基づいてプルリクエストを取得します。
        
        Args:
            repository_id (int): リポジトリID
            start_date (datetime, optional): 開始日（PR作成日でフィルタ）
            end_date (datetime, optional): 終了日（PR作成日でフィルタ）
            author (str, optional): 作成者でフィルタ
            
        Returns:
            list[dict]: フィルタされたプルリクエスト情報のリスト
        """
        logger.info(f"フィルタ付きプルリクエスト取得開始 - リポジトリID: {repository_id}")
        
        try:
            with self.get_session() as session:
                # ベースクエリ
                query_parts = ["""
                    SELECT id, number, title, user_login, state, created_at, updated_at, 
                           closed_at, merged_at, url, body
                    FROM pull_requests
                    WHERE repository_id = :repo_id
                """]
                
                params = {"repo_id": repository_id}
                
                # 日付範囲フィルタ
                if start_date:
                    query_parts.append("AND created_at >= :start_date")
                    params["start_date"] = start_date.isoformat()
                    
                if end_date:
                    query_parts.append("AND created_at <= :end_date")
                    params["end_date"] = end_date.isoformat()
                
                # 作成者フィルタ
                if author:
                    query_parts.append("AND user_login = :author")
                    params["author"] = author
                
                query_parts.append("ORDER BY created_at DESC")
                
                final_query = " ".join(query_parts)
                result = session.execute(text(final_query), params)
                
                pull_requests = [
                    {
                        "id": row.id,
                        "number": row.number,
                        "title": row.title,
                        "user_login": row.user_login,
                        "state": row.state,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                        "closed_at": row.closed_at,
                        "merged_at": row.merged_at,
                        "url": row.url,
                        "body": row.body
                    } for row in result
                ]
                
                logger.info(f"{len(pull_requests)}件のフィルタされたプルリクエストを取得しました")
                return pull_requests
                
        except Exception as e:
            logger.error(f"フィルタ付きプルリクエストの取得中にエラーが発生しました: {e}")
            return []

    def get_authors_for_repository(self, repository_id: int) -> list[str]:
        """
        指定されたリポジトリの作成者一覧を取得します。
        
        Args:
            repository_id (int): リポジトリID
            
        Returns:
            list[str]: 作成者のリスト
        """
        logger.info(f"リポジトリID {repository_id} の作成者一覧取得を開始します")
        
        try:
            with self.get_session() as session:
                query = text("""
                    SELECT DISTINCT user_login
                    FROM pull_requests
                    WHERE repository_id = :repo_id
                    ORDER BY user_login
                """)
                result = session.execute(query, {"repo_id": repository_id})
                
                authors = [row.user_login for row in result]
                logger.info(f"{len(authors)}人の作成者を取得しました")
                return authors
                
        except Exception as e:
            logger.error(f"作成者一覧の取得中にエラーが発生しました: {e}")
            return []

    def get_pull_request_by_number(self, repository_id: int, number: int) -> dict[str, Any] | None:
        """
        リポジトリIDとPR番号でプルリクエストを取得します。

        Args:
            repository_id (int): リポジトリのDB ID。
            number (int): プルリクエスト番号。

        Returns:
            dict | None: プルリクエスト情報の辞書。見つからない場合はNone。
        """
        logger.info(f"プルリクエスト取得開始: リポジトリID {repository_id}, PR番号 {number}")
        try:
            with self.get_session() as session:
                query = text("""
                    SELECT id, repository_id, number, title, body, state,
                           user_login, created_at, updated_at, closed_at, merged_at, url
                    FROM pull_requests
                    WHERE repository_id = :repository_id AND number = :number
                """)
                result = session.execute(query, {"repository_id": repository_id, "number": number})
                row = result.fetchone()
                if row:
                    return {
                        "id": row.id,
                        "repository_id": row.repository_id,
                        "number": row.number,
                        "title": row.title,
                        "body": row.body,
                        "state": row.state,
                        "user_login": row.user_login,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                        "closed_at": row.closed_at,
                        "merged_at": row.merged_at,
                        "url": row.url
                    }
                return None
        except Exception as e:
            logger.error(f"プルリクエスト取得中にエラーが発生しました: {e}")
            return None
