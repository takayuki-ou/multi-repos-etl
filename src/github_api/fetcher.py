"""
GitHub APIクライアント (client.py) を使用して、PR、Issueコメント、レビューコメントといった
特定の種類のデータを取得する高レベルなロジックを実装します。
最後に取得した日時を考慮したフィルタリングを行います。
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from src.github_api.client import GitHubAPIClient
# Import DatabaseHandler once it's defined and needed
# from src.db.database import DatabaseHandler # Assuming DatabaseHandler is in database.py

logger = logging.getLogger(__name__)

class GitHubFetcher:
    """
    GitHub APIクライアントを使用して、特定の種類のデータを取得する高レベルなロジックを実装します。
    """

    def __init__(self, client: GitHubAPIClient): # db_handler: DatabaseHandler):
        """
        GitHubFetcherを初期化します。

        Args:
            client: GitHubAPIClientのインスタンス。
            db_handler: DatabaseHandlerのインスタンス。
        """
        self.client = client
        # self.db_handler = db_handler # Will be used later

    def get_last_fetched_at(self, repo_full_name: str) -> Optional[str]:
        """
        指定されたリポジトリの最終取得日時をデータベースから取得します。
        現時点ではデータベースハンドラが完全に統合されていないため、Noneを返します。
        実際の処理では、self.db_handlerを使用してデータベースにクエリを実行します。

        Args:
            repo_full_name: "owner/repo"形式のリポジトリ名。

        Returns:
            最終取得日時のISO 8601形式の文字列。見つからない場合はNone。
        """
        # Placeholder: In a real scenario, this would query the database
        # e.g., return self.db_handler.get_last_fetched_timestamp(repo_full_name)
        logger.info(f"'{repo_full_name}' の最終取得日時を問い合わせ (現在はNoneを返却)")
        return None

    def fetch_all_data_for_repo(
        self,
        repo_full_name: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        指定されたリポジトリのプルリクエスト、Issueコメント、レビューコメントをすべて取得します。

        Args:
            repo_full_name: "owner/repo"形式のリポジトリ名。

        Returns:
            プルリクエストのリスト、Issueコメントのリスト、レビューコメントのリストのタプル。
        """
        owner, repo = repo_full_name.split('/')
        since = self.get_last_fetched_at(repo_full_name)

        logger.info(f"'{repo_full_name}' のデータ取得開始 (since: {since})")

        pull_requests = self.client.get_pull_requests(owner, repo, since=since)
        logger.info(f"'{repo_full_name}' からPR {len(pull_requests)}件を取得")

        all_issue_comments: List[Dict[str, Any]] = []
        all_review_comments: List[Dict[str, Any]] = []

        for pr in pull_requests:
            pr_number = pr.get("number")
            if not pr_number:
                logger.warning(f"PRデータに 'number' が含まれていません: {pr.get('id')}")
                continue

            # Issueコメントの取得 (PRはIssueでもあるため)
            # Note: The design doc mentions /repos/{owner}/{repo}/issues/{issue_number}/comments
            # and /repos/{owner}/{repo}/pulls/{pull_number}/comments.
            # For simplicity here, we'll use PR number for both, assuming PRs are a subset of issues.
            # A more robust solution might differentiate or fetch all issues separately.
            issue_comments = self.client.get_issue_comments(owner, repo, issue_number=pr_number, since=since)
            logger.debug(f"PR #{pr_number} ({repo_full_name}) からIssueコメント {len(issue_comments)}件を取得")
            all_issue_comments.extend(issue_comments)

            # レビューコメントの取得
            review_comments = self.client.get_review_comments(owner, repo, pull_number=pr_number, since=since)
            logger.debug(f"PR #{pr_number} ({repo_full_name}) からレビューコメント {len(review_comments)}件を取得")
            all_review_comments.extend(review_comments)

        logger.info(f"'{repo_full_name}' のデータ取得完了。PRs: {len(pull_requests)}, Issueコメント: {len(all_issue_comments)}, レビューコメント: {len(all_review_comments)}")
        return pull_requests, all_issue_comments, all_review_comments

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
        settings = Settings() # 環境変数などから設定を読み込む
        api_client = GitHubAPIClient(settings)
        fetcher = GitHubFetcher(api_client) #, db_handler_mock) # db_handlerはモックまたは実際のインスタンス

        # settings.repositories は設定ファイルや環境変数から読み込まれる想定
        if settings.repositories:
            test_repo_full_name = settings.repositories[0] # 最初の設定済みリポジトリを使用
            logger.info(f"テスト対象リポジトリ: {test_repo_full_name}")

            prs, issue_comments, review_comments = fetcher.fetch_all_data_for_repo(test_repo_full_name)

            print(f"\n--- Fetched Data for {test_repo_full_name} ---")
            print(f"Pull Requests: {len(prs)}")
            # for pr in prs:
            # print(f"  - PR #{pr.get('number')}: {pr.get('title')}")

            print(f"Issue Comments: {len(issue_comments)}")
            # for comment in issue_comments:
            # print(f"  - Comment ID {comment.get('id')} on PR ??: {comment.get('body', '')[:50]}...")

            print(f"Review Comments: {len(review_comments)}")
            # for comment in review_comments:
            # print(f"  - Comment ID {comment.get('id')} on PR #{comment.get('pull_request_url', '').split('/')[-1]}: {comment.get('body', '')[:50]}...")

        else:
            logger.warning("設定ファイルにリポジトリが指定されていません。手動テストはスキップされます。")

    except Exception as e:
        logger.error(f"手動テスト中にエラーが発生: {e}", exc_info=True)

    logger.info("GitHub Fetcher の手動テスト実行終了")
