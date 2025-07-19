"""
Data Management for the Streamlit GUI.
Handles interactions with settings and database.
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from src.config.settings import Settings
from src.db.database import Database
from src.github_api.client import GitHubAPIClient
from src.github_api.fetcher import GitHubFetcher

logger = logging.getLogger(__name__)


def _parse_datetime_string(datetime_str: Optional[str]) -> Optional[datetime]:
    """
    Parses a datetime string (typically from DB) into a datetime object.
    Assumes format like 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DDTHH:MM:SSZ'.
    """
    if not datetime_str:
        return None
    try:
        # Handle formats like '2023-10-19 08:30:00' or '2023-10-19T08:30:00Z'
        # SQLite often stores datetimes without timezone info by default.
        # GitHub API provides ISO 8601 format e.g. "2011-01-26T19:01:12Z"
        if 'T' in datetime_str and 'Z' in datetime_str:
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
        else: # Assuming 'YYYY-MM-DD HH:MM:SS' or similar from DB
            return datetime.strptime(datetime_str.split(".")[0], "%Y-%m-%d %H:%M:%S") # Handle potential millis
    except ValueError:
        logger.warning(f"Could not parse datetime string: {datetime_str}", exc_info=True)
        return None


class DataManager:
    def __init__(self):
        try:
            self.settings = Settings()
            db_config = {'db_path': self.settings.sqlite_db_path}
            self.db = Database(db_config)
            # Ensure tables exist
            self.db.create_tables()
            logger.info("DataManager initialized successfully.")
        except ValueError as ve:
            logger.error(f"Configuration error during DataManager initialization: {ve}")
            raise  # Re-raise to be caught by the GUI for user feedback
        except Exception as e:
            logger.error(f"Unexpected error during DataManager initialization: {e}", exc_info=True)
            raise # Re-raise for GUI

    def get_repositories(self) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches the list of repositories.
        Returns a tuple: (data, error_message).
        """
        try:
            repos = self.db.get_repository_list()
            if not repos: # Check if empty list instead of None
                return [], None
            return repos, None
        except Exception as e:
            logger.error(f"Error getting repositories: {e}", exc_info=True)
            return None, f"Database error while fetching repositories: {e}"

    def get_pull_requests(self, repository_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches pull requests for a given repository ID.
        Returns a tuple: (data, error_message).
        """
        try:
            prs_raw = self.db.get_pull_requests_for_repository(repository_id)
            if not prs_raw: # Check if empty list instead of None
                return [], None

            parsed_prs: List[Dict[str, Any]] = []
            for pr_data in prs_raw:
                pr_data['created_at_dt'] = _parse_datetime_string(pr_data.get('created_at'))
                pr_data['updated_at_dt'] = _parse_datetime_string(pr_data.get('updated_at'))
                # Keep original strings as well, GUI might want to display them
                parsed_prs.append(pr_data)
            return parsed_prs, None
        except Exception as e:
            logger.error(f"Error getting pull requests for repo ID {repository_id}: {e}", exc_info=True)
            return None, f"Database error while fetching pull requests: {e}"

    def get_review_comments(self, pr_db_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Fetches review comments for a given pull request database ID.
        Returns a tuple: (data, error_message).
        """
        try:
            comments_raw = self.db.get_review_comments_for_pr(pr_db_id)
            if not comments_raw: # Check if empty list instead of None
                return [], None

            parsed_comments: List[Dict[str, Any]] = []
            for comment_data in comments_raw:
                comment_data['created_at_dt'] = _parse_datetime_string(comment_data.get('created_at'))
                # updated_at for comments if available and needed
                # comment_data['updated_at_dt'] = _parse_datetime_string(comment_data.get('updated_at'))
                parsed_comments.append(comment_data)
            return parsed_comments, None
        except Exception as e:
            logger.error(f"Error getting review comments for PR ID {pr_db_id}: {e}", exc_info=True)
            return None, f"Database error while fetching review comments: {e}"

    def get_pull_requests_with_lead_time_data(self, repository_id: int, 
                                            start_date: Optional[datetime] = None,
                                            end_date: Optional[datetime] = None,
                                            author: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        リードタイム分析用のPRデータを取得（フィルタリング対応）
        
        Args:
            repository_id: リポジトリID
            start_date: 開始日（PR作成日でフィルタ）
            end_date: 終了日（PR作成日でフィルタ）
            author: 作成者でフィルタ
            
        Returns:
            Tuple[List[Dict], Optional[str]]: (PRデータリスト, エラーメッセージ)
        """
        try:
            prs_raw = self.db.get_pull_requests_with_filters(
                repository_id=repository_id,
                start_date=start_date,
                end_date=end_date,
                author=author
            )
            
            if not prs_raw:
                return [], None

            parsed_prs: List[Dict[str, Any]] = []
            for pr_data in prs_raw:
                # 日時データの解析
                pr_data['created_at_dt'] = _parse_datetime_string(pr_data.get('created_at'))
                pr_data['updated_at_dt'] = _parse_datetime_string(pr_data.get('updated_at'))
                pr_data['closed_at_dt'] = _parse_datetime_string(pr_data.get('closed_at'))
                pr_data['merged_at_dt'] = _parse_datetime_string(pr_data.get('merged_at'))
                
                parsed_prs.append(pr_data)
                
            return parsed_prs, None
            
        except Exception as e:
            logger.error(f"Error getting filtered pull requests for repo ID {repository_id}: {e}", exc_info=True)
            return None, f"Database error while fetching filtered pull requests: {e}"

    def get_authors_for_repository(self, repository_id: int) -> Tuple[List[str], Optional[str]]:
        """
        指定されたリポジトリの作成者一覧を取得
        
        Args:
            repository_id: リポジトリID
            
        Returns:
            Tuple[List[str], Optional[str]]: (作成者リスト, エラーメッセージ)
        """
        try:
            authors = self.db.get_authors_for_repository(repository_id)
            return authors, None
        except Exception as e:
            logger.error(f"Error getting authors for repo ID {repository_id}: {e}", exc_info=True)
            return [], f"Database error while fetching authors: {e}"

    def fetch_and_store_all_data(self) -> Tuple[bool, str]:
        """
        GitHub APIからすべてのリポジトリのデータを取得し、DBに保存します。

        Returns:
            Tuple[bool, str]: (成功フラグ, メッセージ)
        """
        logger.info("データ取得・DB投入処理を開始します")

        try:
            # GitHub APIクライアントとフェッチャーを初期化
            client = GitHubAPIClient(self.settings)
            fetcher = GitHubFetcher(client)

            success_count = 0
            error_count = 0
            error_messages = []

            # 設定されたリポジトリを処理
            for repo_full_name in self.settings.repositories:
                try:
                    logger.info(f"リポジトリ {repo_full_name} のデータ取得を開始")

                    # owner/repo を分離
                    owner, repo_name = repo_full_name.split('/')

                    # まずリポジトリ情報を取得・保存
                    # 簡易的にGitHub APIから基本情報を取得
                    import requests
                    repo_url = f"https://api.github.com/repos/{repo_full_name}"
                    repo_response = requests.get(repo_url, headers=client.headers)
                    repo_response.raise_for_status()
                    repo_data = repo_response.json()

                    # リポジトリ情報をUPSERT
                    if not self.db.upsert_repository(repo_data):
                        error_messages.append(f"リポジトリ {repo_full_name} の保存に失敗")
                        error_count += 1
                        continue

                    # DBからリポジトリIDを取得
                    db_repo = self.db.get_repository_by_full_name(owner, repo_name)
                    if not db_repo:
                        error_messages.append(f"リポジトリ {repo_full_name} のDB ID取得に失敗")
                        error_count += 1
                        continue

                    repository_id = db_repo['id']

                    # プルリクエスト、Issueコメント、レビューコメントを取得
                    pull_requests, _, review_comments = fetcher.fetch_all_data_for_repo(repo_full_name)

                    # プルリクエストをUPSERT
                    pr_count = 0
                    for pr_data in pull_requests:
                        if self.db.upsert_pull_request(pr_data, repository_id):
                            pr_count += 1
                        else:
                            logger.warning(f"PR #{pr_data.get('number')} の保存に失敗")

                    # レビューコメントをUPSERT
                    comment_count = 0
                    for comment_data in review_comments:
                        # PRのURLからPR番号を取得
                        pr_url = comment_data.get('pull_request_url', '')
                        if pr_url:
                            # URL例: https://api.github.com/repos/owner/repo/pulls/123
                            pr_number = int(pr_url.split('/')[-1])
                            # PR番号からDB IDを取得
                            db_pr = self.db.get_pull_request_by_number(repository_id, pr_number)
                            if db_pr:
                                if self.db.upsert_review_comment(comment_data, db_pr['id']):
                                    comment_count += 1
                                else:
                                    logger.warning(f"レビューコメント ID {comment_data.get('id')} の保存に失敗")
                            else:
                                logger.warning(f"PR番号 {pr_number} に対応するDBレコードが見つかりません")

                    logger.info(f"リポジトリ {repo_full_name} の処理完了: PRs={pr_count}, Comments={comment_count}")
                    success_count += 1

                except Exception as e:
                    logger.error(f"リポジトリ {repo_full_name} の処理中にエラー: {e}")
                    error_messages.append(f"リポジトリ {repo_full_name}: {str(e)}")
                    error_count += 1
                    continue

            # 結果メッセージの作成
            if error_count == 0:
                message = f"すべてのリポジトリの処理が正常に完了しました。(成功: {success_count}件)"
                logger.info(message)
                return True, message
            elif success_count > 0:
                message = f"一部のリポジトリで処理が完了しました。成功: {success_count}件, 失敗: {error_count}件"
                if error_messages:
                    message += f"\nエラー詳細: {'; '.join(error_messages[:3])}"  # 最初の3件のみ表示
                logger.warning(message)
                return True, message
            else:
                message = f"すべてのリポジトリの処理に失敗しました。失敗: {error_count}件"
                if error_messages:
                    message += f"\nエラー詳細: {'; '.join(error_messages[:3])}"
                logger.error(message)
                return False, message

        except Exception as e:
            error_message = f"データ取得・DB投入処理中に予期しないエラーが発生しました: {e}"
            logger.error(error_message, exc_info=True)
            return False, error_message

if __name__ == '__main__':
    # Basic test for DataManager
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing DataManager...")
    try:
        dm = DataManager()
        repos, error = dm.get_repositories()
        if error:
            logger.error(f"Test error fetching repos: {error}")
        elif repos:
            logger.info(f"Successfully fetched {len(repos)} repositories.")
            if repos:
                repo_id_to_test = repos[0]['id']
                logger.info(f"Testing with repo ID: {repo_id_to_test}")
                prs, pr_error = dm.get_pull_requests(repo_id_to_test)
                if pr_error:
                    logger.error(f"Test error fetching PRs: {pr_error}")
                elif prs:
                    logger.info(f"Successfully fetched {len(prs)} PRs for repo {repo_id_to_test}.")
                    if prs:
                        pr_db_id_to_test = prs[0]['id'] # Assuming 'id' is the DB PK
                        comments, comment_error = dm.get_review_comments(pr_db_id_to_test)
                        if comment_error:
                            logger.error(f"Test error fetching comments: {comment_error}")
                        elif comments:
                            logger.info(f"Successfully fetched {len(comments)} comments for PR {pr_db_id_to_test}.")
                        else:
                            logger.info(f"No comments found for PR {pr_db_id_to_test} (or an issue if there should be some).")
                else:
                    logger.info(f"No PRs found for repo {repo_id_to_test} (or an issue if there should be some).")

        else:
            logger.info("No repositories found (or an issue if there should be some).")

    except Exception as e:
        logger.error(f"Error during DataManager test: {e}", exc_info=True)
