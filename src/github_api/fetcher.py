"""
GitHub APIクライアント (client.py) を使用して、PR、Issueコメント、レビューコメントといった
特定の種類のデータを取得する高レベルなロジックを実装します。
最後に取得した日時を考慮したフィルタリングを行います。
"""
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from src.github_api.client import GitHubAPIClient, APIError, RateLimitError, AuthenticationError, NotFoundError
from src.db.database import Database

logger = logging.getLogger(__name__)

class FetcherError(Exception):
    """フェッチャーの基底例外クラス"""
    pass

class DataValidationError(FetcherError):
    """データ検証エラー"""
    pass

@dataclass
class FetchResult:
    """フェッチ結果"""
    repository: str
    pull_requests: List[Dict[str, Any]]
    issue_comments: List[Dict[str, Any]]
    review_comments: List[Dict[str, Any]]
    success: bool
    error_message: Optional[str] = None
    fetch_time: datetime = None
    
    def __post_init__(self):
        if self.fetch_time is None:
            self.fetch_time = datetime.now()

@dataclass
class FetchProgress:
    """フェッチ進捗"""
    total_repositories: int
    completed_repositories: int
    current_repository: str
    total_prs: int = 0
    total_comments: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def progress_percentage(self) -> float:
        """進捗率を計算"""
        if self.total_repositories == 0:
            return 0.0
        return (self.completed_repositories / self.total_repositories) * 100

class GitHubFetcher:
    """
    GitHub APIクライアントを使用して、特定の種類のデータを取得する高レベルなロジックを実装します。
    """

    def __init__(self, client: GitHubAPIClient, database: Optional[Database] = None):
        """
        GitHubFetcherを初期化します。

        Args:
            client: GitHubAPIClientのインスタンス。
            database: Databaseのインスタンス（オプション）。
        """
        self.client = client
        self.database = database
        self.progress_callback: Optional[Callable[[FetchProgress], None]] = None

    def set_progress_callback(self, callback: Callable[[FetchProgress], None]) -> None:
        """進捗コールバックを設定"""
        self.progress_callback = callback

    def _validate_repository_data(self, repo_data: Dict[str, Any]) -> None:
        """リポジトリデータの検証"""
        required_fields = ['id', 'name', 'owner', 'html_url']
        for field in required_fields:
            if field not in repo_data:
                raise DataValidationError(f"リポジトリデータに必須フィールド '{field}' が不足しています")
        
        if not isinstance(repo_data.get('owner'), dict) or 'login' not in repo_data['owner']:
            raise DataValidationError("リポジトリデータのowner.loginが不正です")

    def _validate_pull_request_data(self, pr_data: Dict[str, Any]) -> None:
        """プルリクエストデータの検証"""
        required_fields = ['id', 'number', 'title', 'user', 'state', 'html_url']
        for field in required_fields:
            if field not in pr_data:
                raise DataValidationError(f"プルリクエストデータに必須フィールド '{field}' が不足しています")
        
        if not isinstance(pr_data.get('user'), dict) or 'login' not in pr_data['user']:
            raise DataValidationError("プルリクエストデータのuser.loginが不正です")
        
        valid_states = ['open', 'closed']
        if pr_data.get('state') not in valid_states:
            raise DataValidationError(f"プルリクエストのstateが不正です: {pr_data.get('state')}")

    def _validate_comment_data(self, comment_data: Dict[str, Any]) -> None:
        """コメントデータの検証"""
        required_fields = ['id', 'user', 'body', 'html_url']
        for field in required_fields:
            if field not in comment_data:
                raise DataValidationError(f"コメントデータに必須フィールド '{field}' が不足しています")
        
        if not isinstance(comment_data.get('user'), dict) or 'login' not in comment_data['user']:
            raise DataValidationError("コメントデータのuser.loginが不正です")

    def get_last_fetched_at(self, repo_full_name: str) -> Optional[str]:
        """
        指定されたリポジトリの最終取得日時をデータベースから取得します。

        Args:
            repo_full_name: "owner/repo"形式のリポジトリ名。

        Returns:
            最終取得日時のISO 8601形式の文字列。見つからない場合はNone。
        """
        if not self.database:
            logger.info(f"'{repo_full_name}' の最終取得日時を問い合わせ (データベース未接続のためNoneを返却)")
            return None
        
        try:
            owner, repo = repo_full_name.split('/')
            repo_data = self.database.get_repository_by_full_name(owner, repo)
            if repo_data and repo_data.get('fetched_at'):
                logger.info(f"'{repo_full_name}' の最終取得日時: {repo_data['fetched_at']}")
                return repo_data['fetched_at']
            return None
        except Exception as e:
            logger.error(f"最終取得日時の取得に失敗しました: {e}")
            return None

    def fetch_all_data_for_repo(
        self,
        repo_full_name: str
    ) -> FetchResult:
        """
        指定されたリポジトリのプルリクエスト、Issueコメント、レビューコメントをすべて取得します。

        Args:
            repo_full_name: "owner/repo"形式のリポジトリ名。

        Returns:
            FetchResult: フェッチ結果。
        """
        owner, repo = repo_full_name.split('/')
        since = self.get_last_fetched_at(repo_full_name)

        logger.info(f"'{repo_full_name}' のデータ取得開始 (since: {since})")

        try:
            # プルリクエストの取得
            pull_requests = self.client.get_pull_requests(owner, repo, since=since)
            logger.info(f"'{repo_full_name}' からPR {len(pull_requests)}件を取得")

            # データ検証
            for pr in pull_requests:
                self._validate_pull_request_data(pr)

            all_issue_comments: List[Dict[str, Any]] = []
            all_review_comments: List[Dict[str, Any]] = []

            # 各プルリクエストのコメントを取得
            for pr in pull_requests:
                pr_number = pr.get("number")
                if not pr_number:
                    logger.warning(f"PRデータに 'number' が含まれていません: {pr.get('id')}")
                    continue

                try:
                    # Issueコメントの取得
                    issue_comments = self.client.get_issue_comments(owner, repo, issue_number=pr_number, since=since)
                    logger.debug(f"PR #{pr_number} ({repo_full_name}) からIssueコメント {len(issue_comments)}件を取得")
                    
                    # コメントデータの検証
                    for comment in issue_comments:
                        self._validate_comment_data(comment)
                    
                    all_issue_comments.extend(issue_comments)

                    # レビューコメントの取得
                    review_comments = self.client.get_review_comments(owner, repo, pull_number=pr_number, since=since)
                    logger.debug(f"PR #{pr_number} ({repo_full_name}) からレビューコメント {len(review_comments)}件を取得")
                    
                    # レビューコメントデータの検証
                    for comment in review_comments:
                        self._validate_comment_data(comment)
                    
                    all_review_comments.extend(review_comments)
                    
                except Exception as e:
                    logger.error(f"PR #{pr_number} のコメント取得に失敗しました: {e}")
                    # 個別のPRのコメント取得失敗は全体の処理を停止しない
                    continue

            logger.info(f"'{repo_full_name}' のデータ取得完了。PRs: {len(pull_requests)}, Issueコメント: {len(all_issue_comments)}, レビューコメント: {len(all_review_comments)}")
            
            return FetchResult(
                repository=repo_full_name,
                pull_requests=pull_requests,
                issue_comments=all_issue_comments,
                review_comments=all_review_comments,
                success=True
            )
            
        except NotFoundError as e:
            error_msg = f"リポジトリ '{repo_full_name}' が見つかりません: {e}"
            logger.error(error_msg)
            return FetchResult(
                repository=repo_full_name,
                pull_requests=[],
                issue_comments=[],
                review_comments=[],
                success=False,
                error_message=error_msg
            )
        except AuthenticationError as e:
            error_msg = f"認証エラー: {e}"
            logger.error(error_msg)
            return FetchResult(
                repository=repo_full_name,
                pull_requests=[],
                issue_comments=[],
                review_comments=[],
                success=False,
                error_message=error_msg
            )
        except RateLimitError as e:
            error_msg = f"レート制限エラー: {e}"
            logger.error(error_msg)
            return FetchResult(
                repository=repo_full_name,
                pull_requests=[],
                issue_comments=[],
                review_comments=[],
                success=False,
                error_message=error_msg
            )
        except Exception as e:
            error_msg = f"データ取得中にエラーが発生しました: {e}"
            logger.error(error_msg)
            return FetchResult(
                repository=repo_full_name,
                pull_requests=[],
                issue_comments=[],
                review_comments=[],
                success=False,
                error_message=error_msg
            )

    def fetch_all_repositories(self) -> List[FetchResult]:
        """
        設定されたすべてのリポジトリからデータを取得します。

        Returns:
            List[FetchResult]: 各リポジトリのフェッチ結果。
        """
        repositories = list(self.client.repositories)
        if not repositories:
            logger.warning("設定されたリポジトリがありません")
            return []

        progress = FetchProgress(
            total_repositories=len(repositories),
            completed_repositories=0,
            current_repository=""
        )

        results: List[FetchResult] = []
        
        for i, repo_full_name in enumerate(repositories):
            progress.current_repository = repo_full_name
            progress.completed_repositories = i
            
            if self.progress_callback:
                self.progress_callback(progress)

            logger.info(f"リポジトリ {i+1}/{len(repositories)} を処理中: {repo_full_name}")
            
            result = self.fetch_all_data_for_repo(repo_full_name)
            results.append(result)
            
            if not result.success:
                progress.errors.append(f"{repo_full_name}: {result.error_message}")
            else:
                progress.total_prs += len(result.pull_requests)
                progress.total_comments += len(result.issue_comments) + len(result.review_comments)

        progress.completed_repositories = len(repositories)
        if self.progress_callback:
            self.progress_callback(progress)

        # 結果のサマリーをログ出力
        successful_fetches = sum(1 for r in results if r.success)
        total_prs = sum(len(r.pull_requests) for r in results if r.success)
        total_comments = sum(len(r.issue_comments) + len(r.review_comments) for r in results if r.success)
        
        logger.info(f"フェッチ完了: {successful_fetches}/{len(repositories)} リポジトリ成功, "
                   f"PR {total_prs}件, コメント {total_comments}件")

        return results

    def save_to_database(self, results: List[FetchResult]) -> bool:
        """
        フェッチ結果をデータベースに保存します。

        Args:
            results: フェッチ結果のリスト。

        Returns:
            bool: 保存が成功した場合はTrue。
        """
        if not self.database:
            logger.warning("データベースが設定されていないため、保存をスキップします")
            return False

        try:
            for result in results:
                if not result.success:
                    logger.warning(f"失敗したリポジトリ '{result.repository}' はスキップします")
                    continue

                owner, repo = result.repository.split('/')
                
                # リポジトリ情報を保存
                repo_data = {
                    'id': 0,  # データベースで自動生成
                    'name': repo,
                    'owner': {'login': owner},
                    'html_url': f"https://github.com/{owner}/{repo}",
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                if not self.database.upsert_repository(repo_data):
                    logger.error(f"リポジトリ '{result.repository}' の保存に失敗しました")
                    continue

                # リポジトリIDを取得
                repo_db_data = self.database.get_repository_by_full_name(owner, repo)
                if not repo_db_data:
                    logger.error(f"リポジトリ '{result.repository}' のID取得に失敗しました")
                    continue

                repository_id = repo_db_data['id']

                # プルリクエストを保存
                for pr in result.pull_requests:
                    if not self.database.upsert_pull_request(pr, repository_id):
                        logger.error(f"プルリクエスト #{pr.get('number')} の保存に失敗しました")

                # プルリクエストIDを取得してレビューコメントを保存
                for pr in result.pull_requests:
                    pr_db_data = self.database.get_pull_request_by_number(repository_id, pr.get('number'))
                    if pr_db_data:
                        for comment in result.review_comments:
                            if not self.database.upsert_review_comment(comment, pr_db_data['id']):
                                logger.error(f"レビューコメント ID {comment.get('id')} の保存に失敗しました")

            logger.info("データベースへの保存が完了しました")
            return True
            
        except Exception as e:
            logger.error(f"データベースへの保存中にエラーが発生しました: {e}")
            return False

if __name__ == "__main__":
    # このブロックは基本的なテストや手動実行用です。
    # ユニットテストは別途 test_fetcher.py に記述します。
    from src.config.settings import Settings

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger.info("GitHub Fetcher の手動テスト実行開始")

    try:
        settings = Settings()
        api_client = GitHubAPIClient(settings)
        fetcher = GitHubFetcher(api_client)

        # 進捗コールバックを設定
        def progress_callback(progress: FetchProgress):
            logger.info(f"進捗: {progress.progress_percentage:.1f}% "
                       f"({progress.completed_repositories}/{progress.total_repositories}) "
                       f"現在: {progress.current_repository}")

        fetcher.set_progress_callback(progress_callback)

        # settings.repositories は設定ファイルや環境変数から読み込まれる想定
        if settings.repositories:
            logger.info(f"設定されたリポジトリ数: {len(settings.repositories)}")
            
            # すべてのリポジトリをフェッチ
            results = fetcher.fetch_all_repositories()
            
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]
            
            print(f"\n--- Fetch Results ---")
            print(f"成功: {len(successful_results)}/{len(results)} リポジトリ")
            print(f"失敗: {len(failed_results)} リポジトリ")
            
            if failed_results:
                print("\n失敗したリポジトリ:")
                for result in failed_results:
                    print(f"  - {result.repository}: {result.error_message}")
            
            total_prs = sum(len(r.pull_requests) for r in successful_results)
            total_comments = sum(len(r.issue_comments) + len(r.review_comments) for r in successful_results)
            
            print(f"\n取得データ:")
            print(f"  プルリクエスト: {total_prs}件")
            print(f"  コメント: {total_comments}件")

        else:
            logger.warning("設定ファイルにリポジトリが指定されていません。手動テストはスキップされます。")

    except Exception as e:
        logger.error(f"手動テスト中にエラーが発生: {e}", exc_info=True)

    logger.info("GitHub Fetcher の手動テスト実行終了")
