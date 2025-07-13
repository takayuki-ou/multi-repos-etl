"""
GitHub REST APIへの低レベルなリクエスト送信、認証ヘッダーの管理、
APIレート制限のハンドリング、ページネーション処理を担当するモジュール
"""
import requests
import time
import logging
from typing import Dict, List, Optional, Generator, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from src.config.settings import Settings

logger = logging.getLogger(__name__)

class APIError(Exception):
    """API操作の基底例外クラス"""
    pass

class RateLimitError(APIError):
    """レート制限エラー"""
    pass

class AuthenticationError(APIError):
    """認証エラー"""
    pass

class NotFoundError(APIError):
    """リソースが見つからないエラー"""
    pass

@dataclass
class RetryConfig:
    """リトライ設定"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0

class RateLimitStatus:
    """レート制限の状態管理"""
    def __init__(self):
        self.remaining: Optional[int] = None
        self.reset_time: Optional[datetime] = None
        self.limit: Optional[int] = None

    def update_from_headers(self, headers: Dict[str, str]):
        """レスポンスヘッダーからレート制限情報を更新"""
        self.remaining = int(headers.get("X-RateLimit-Remaining", 0))
        reset_timestamp = int(headers.get("X-RateLimit-Reset", 0))
        self.reset_time = datetime.fromtimestamp(reset_timestamp)
        self.limit = int(headers.get("X-RateLimit-Limit", 0))

    def should_wait(self) -> bool:
        """レート制限により待機が必要かチェック"""
        return self.remaining == 0 and self.reset_time is not None

    def get_wait_time(self) -> float:
        """待機時間を計算"""
        if self.reset_time is None:
            return 0.0
        wait_time = (self.reset_time - datetime.now()).total_seconds() + 1
        return max(wait_time, 0.0)

class GitHubAPIClient:
    """GitHub REST APIクライアント"""

    BASE_URL = "https://api.github.com"
    HEADERS = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-PR-Analysis-System"
    }

    def __init__(self, settings: Settings, retry_config: Optional[RetryConfig] = None):
        """初期化"""
        self.settings = settings
        self.retry_config = retry_config or RetryConfig()
        self.headers = self.HEADERS.copy()
        self.headers["Authorization"] = f"token {settings.github_pat}"
        self.rate_limit_status = RateLimitStatus()

    @property
    def repositories(self) -> Generator[str, None, None]:
        """設定されたリポジトリのowner/repo形式の文字列を返すジェネレータ"""
        for repo in self.settings.repositories:
            yield repo

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """レート制限の処理"""
        self.rate_limit_status.update_from_headers(response.headers)
        
        if self.rate_limit_status.should_wait():
            wait_time = self.rate_limit_status.get_wait_time()
            logger.warning(f"レート制限に達しました。{wait_time:.1f}秒待機します。")
            time.sleep(wait_time)

    def _handle_http_error(self, response: requests.Response) -> None:
        """HTTPエラーの処理"""
        if response.status_code == 401:
            raise AuthenticationError("認証に失敗しました。GitHub Personal Access Tokenを確認してください。")
        elif response.status_code == 403:
            if "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
                raise RateLimitError("レート制限に達しました。")
            else:
                raise APIError("アクセスが拒否されました。権限を確認してください。")
        elif response.status_code == 404:
            raise NotFoundError("リソースが見つかりません。")
        elif response.status_code >= 500:
            raise APIError(f"サーバーエラーが発生しました: {response.status_code}")
        else:
            raise APIError(f"HTTPエラー {response.status_code}: {response.text}")

    def _retry_operation(self, operation: Callable, *args, **kwargs):
        """リトライ機能付きの操作実行"""
        last_exception = None
        delay = self.retry_config.base_delay
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            except RateLimitError:
                # レート制限の場合は特別な処理
                if self.rate_limit_status.should_wait():
                    wait_time = self.rate_limit_status.get_wait_time()
                    logger.warning(f"レート制限により待機: {wait_time:.1f}秒")
                    time.sleep(wait_time)
                    continue
                else:
                    raise
            except (AuthenticationError, NotFoundError):
                # 認証エラーや404エラーはリトライしない
                raise
            except Exception as e:
                last_exception = e
                if attempt < self.retry_config.max_retries:
                    logger.warning(f"操作に失敗しました (試行 {attempt + 1}/{self.retry_config.max_retries + 1}): {e}")
                    time.sleep(delay)
                    delay = min(delay * self.retry_config.backoff_factor, self.retry_config.max_delay)
                else:
                    logger.error(f"最大試行回数に達しました: {e}")
                    raise last_exception

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, str]] = None) -> requests.Response:
        """APIリクエストの送信"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        def _make_request_operation():
            try:
                logger.debug(f"APIリクエスト: {method} {url} パラメータ: {params}")
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    timeout=30  # タイムアウトを設定
                )
                
                if response.status_code >= 400:
                    self._handle_http_error(response)
                
                logger.debug(f"APIレスポンス: ステータス {response.status_code}")
                logger.debug(f"レート制限: 残り {response.headers.get('X-RateLimit-Remaining')} リセット時刻 {response.headers.get('X-RateLimit-Reset')}")
                self._handle_rate_limit(response)
                return response
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTPエラー: {e}")
                raise
            except requests.exceptions.ConnectionError as e:
                logger.error(f"接続エラー: {e}")
                raise
            except requests.exceptions.Timeout as e:
                logger.error(f"タイムアウト: {e}")
                raise
        
        return self._retry_operation(_make_request_operation)

    def _process_repositories(self, func: Callable[..., List[Dict[str, Any]]], owner: Optional[str] = None, repo: Optional[str] = None, **kwargs: Any) -> List[Dict[str, Any]]:
        """リポジトリ処理の共通ロジック

        Args:
            func: 各リポジトリに対して実行する関数
            owner: リポジトリのオーナー（オプション）
            repo: リポジトリ名（オプション）
            **kwargs: 関数に渡す追加の引数

        Returns:
            List[Dict[str, Any]]: 処理結果のリスト
        """
        results: List[Dict[str, Any]] = []
        target_repos = [f"{owner}/{repo}"] if owner and repo else self.repositories
        is_single_repo = owner is not None and repo is not None

        for repo_full_name in target_repos:
            try:
                result: List[Dict[str, Any]] = func(repo_full_name, **kwargs)
                results.extend(result)
            except NotFoundError as e:
                logger.error(f"リポジトリ {repo_full_name} が見つかりません: {e}")
                if is_single_repo:
                    raise
                continue
            except AuthenticationError as e:
                logger.error(f"認証エラー: {e}")
                raise
            except RateLimitError as e:
                logger.error(f"レート制限エラー: {e}")
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"リポジトリ {repo_full_name} の処理に失敗しました: {e}")
                if is_single_repo:
                    raise
                continue

        return results

    def get_pull_requests(self, owner: Optional[str] = None, repo: Optional[str] = None, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """プルリクエストの取得"""
        return self._process_repositories(
            self._get_pull_requests_for_repo,
            owner,
            repo,
            since=since
        )

    def _get_pull_requests_for_repo(self, repo_full_name: str, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """特定のリポジトリのプルリクエストを取得"""
        endpoint = f"repos/{repo_full_name}/pulls"
        params = {
            "state": "all",
            "per_page": self.settings.fetch_settings["max_prs_per_request"]
        }
        if since:
            params["since"] = since

        prs: List[Dict[str, Any]] = []
        page = 1
        max_pages = 100  # ページネーションの上限を設定
        
        while page <= max_pages:
            params["page"] = page
            try:
                response = self._make_request("GET", endpoint, params)
                current_prs: List[Dict[str, Any]] = response.json()
                if not current_prs:  # 空のレスポンスを受け取ったら終了
                    break
                prs.extend(current_prs)
                page += 1
                time.sleep(self.settings.fetch_settings["request_interval"])
            except Exception as e:
                logger.error(f"プルリクエスト取得中にエラーが発生しました: {e}")
                raise

        logger.info(f"{repo_full_name} から {len(prs)} 件のプルリクエストを取得しました")
        return prs

    def get_issue_comments(self, owner: Optional[str] = None, repo: Optional[str] = None, issue_number: Optional[int] = None, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Issueコメントの取得"""
        return self._process_repositories(
            self._get_issue_comments_for_repo,
            owner,
            repo,
            issue_number=issue_number,
            since=since
        )

    def _get_issue_comments_for_repo(self, repo_full_name: str, issue_number: int, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """特定のリポジトリのIssueコメントを取得"""
        endpoint = f"repos/{repo_full_name}/issues/{issue_number}/comments"
        params = {
            "per_page": self.settings.fetch_settings["max_prs_per_request"]
        }
        if since:
            params["since"] = since

        comments: List[Dict[str, Any]] = []
        page = 1
        max_pages = 50  # コメントのページネーション上限
        
        while page <= max_pages:
            params["page"] = page
            try:
                response = self._make_request("GET", endpoint, params)
                current_comments: List[Dict[str, Any]] = response.json()
                if not current_comments:
                    break
                comments.extend(current_comments)
                page += 1
                time.sleep(self.settings.fetch_settings["request_interval"])
            except Exception as e:
                logger.error(f"Issueコメント取得中にエラーが発生しました: {e}")
                raise

        return comments

    def get_review_comments(self, owner: Optional[str] = None, repo: Optional[str] = None, pull_number: Optional[int] = None, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """レビューコメントの取得"""
        return self._process_repositories(
            self._get_review_comments_for_repo,
            owner,
            repo,
            pull_number=pull_number,
            since=since
        )

    def _get_review_comments_for_repo(self, repo_full_name: str, pull_number: int, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """特定のリポジトリのレビューコメントを取得"""
        endpoint = f"repos/{repo_full_name}/pulls/{pull_number}/comments"
        params = {
            "per_page": self.settings.fetch_settings["max_prs_per_request"]
        }
        if since:
            params["since"] = since

        comments: List[Dict[str, Any]] = []
        page = 1
        max_pages = 50  # コメントのページネーション上限
        
        while page <= max_pages:
            params["page"] = page
            try:
                response = self._make_request("GET", endpoint, params)
                current_comments: List[Dict[str, Any]] = response.json()
                if not current_comments:
                    break
                comments.extend(current_comments)
                page += 1
                time.sleep(self.settings.fetch_settings["request_interval"])
            except Exception as e:
                logger.error(f"レビューコメント取得中にエラーが発生しました: {e}")
                raise

        return comments

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """レート制限の状態を取得"""
        try:
            response = self._make_request("GET", "rate_limit")
            rate_limit_data = response.json()
            return {
                "core": rate_limit_data.get("resources", {}).get("core", {}),
                "search": rate_limit_data.get("resources", {}).get("search", {}),
                "graphql": rate_limit_data.get("resources", {}).get("graphql", {})
            }
        except Exception as e:
            logger.error(f"レート制限状態の取得に失敗しました: {e}")
            return {}

if __name__ == "__main__":
    """メイン関数"""
    from src.config.settings import Settings
    import logging

    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)
    logger.info("GitHub APIクライアントの初期化を開始します")

    try:
        settings = Settings()
        client = GitHubAPIClient(settings)
        logger.info("GitHub APIクライアントの初期化が完了しました")
        
        # レート制限状態を確認
        rate_limit = client.get_rate_limit_status()
        logger.info(f"レート制限状態: {rate_limit}")
        
    except Exception as e:
        logger.error(f"初期化中にエラーが発生しました: {e}", exc_info=True)
        raise
