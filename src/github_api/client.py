"""
GitHub REST APIへの低レベルなリクエスト送信、認証ヘッダーの管理、
APIレート制限のハンドリング、ページネーション処理を担当するモジュール
"""
import requests
import time
import logging
from typing import Dict, List, Optional, Generator, Callable, Any
from datetime import datetime
from src.config.settings import Settings

logger = logging.getLogger(__name__)

class GitHubAPIClient:
    """GitHub REST APIクライアント"""

    BASE_URL = "https://api.github.com"
    HEADERS = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-PR-Analysis-System"
    }

    def __init__(self, settings: Settings):
        """初期化"""
        self.settings = settings
        self.headers = self.HEADERS.copy()
        self.headers["Authorization"] = f"token {settings.github_token}"
        self.rate_limit_remaining = None
        self.rate_limit_reset = None

    @property
    def repositories(self) -> Generator[str, None, None]:
        """設定されたリポジトリのowner/repo形式の文字列を返すジェネレータ"""
        for repo in self.settings.repositories:
            yield repo

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """レート制限の処理"""
        self.rate_limit_remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
        self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

        if self.rate_limit_remaining == 0:
            reset_time = datetime.fromtimestamp(self.rate_limit_reset)
            wait_time = (reset_time - datetime.now()).total_seconds() + 1
            logger.warning(f"レート制限に達しました。{wait_time:.1f}秒待機します。")
            time.sleep(wait_time)

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, str]] = None) -> requests.Response:
        """APIリクエストの送信"""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            logger.debug(f"APIリクエスト: {method} {url} パラメータ: {params}")
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
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

        for repo_full_name in target_repos:
            try:
                result: List[Dict[str, Any]] = func(repo_full_name, **kwargs)
                results.extend(result)
            except requests.exceptions.HTTPError as e:
                # 404エラーは上位で処理するため、そのまま伝播
                raise
            except requests.exceptions.RequestException as e:
                logger.error(f"リポジトリ {repo_full_name} の処理に失敗しました: {e}")
                # その他のエラーは処理を継続
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
        while True:
            params["page"] = page
            try:
                response = self._make_request("GET", endpoint, params)
                current_prs: List[Dict[str, Any]] = response.json()
                if not current_prs:  # 空のレスポンスを受け取ったら終了
                    break
                prs.extend(current_prs)
                page += 1
                time.sleep(self.settings.fetch_settings["request_interval"])
            except requests.exceptions.HTTPError as e:
                # 404エラーは上位で処理するため、そのまま伝播させる
                raise

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
        while True:
            params["page"] = page
            response = self._make_request("GET", endpoint, params)
            current_comments: List[Dict[str, Any]] = response.json()
            if not current_comments:
                break
            comments.extend(current_comments)
            page += 1
            time.sleep(self.settings.fetch_settings["request_interval"])

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
        while True:
            params["page"] = page
            response = self._make_request("GET", endpoint, params)
            current_comments: List[Dict[str, Any]] = response.json()
            if not current_comments:
                break
            comments.extend(current_comments)
            page += 1
            time.sleep(self.settings.fetch_settings["request_interval"])

        return comments

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
    except Exception as e:
        logger.error(f"初期化中にエラーが発生しました: {e}", exc_info=True)
        raise
