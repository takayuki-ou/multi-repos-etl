"""
client.pyのテストコード
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import requests
import logging
from typing import Any
from src.github_api.client import GitHubAPIClient
from tests.mocks.github_api.settings import create_mock_settings
from tests.mocks.github_api.responses import create_mock_response, create_error_response

@pytest.fixture
def mock_settings() -> Any:
    """Settingsクラスのモック"""
    return create_mock_settings()

@pytest.fixture
def mock_response() -> Any:
    """APIレスポンスのモック"""
    return create_mock_response()

def test_github_api_client_initialization(mock_settings: Any) -> None:
    """GitHubAPIClientの初期化テスト"""
    client = GitHubAPIClient(mock_settings)
    assert client.headers['Authorization'] == 'token test_token'
    assert client.headers['Accept'] == 'application/vnd.github.v3+json'
    assert client.headers['User-Agent'] == 'GitHub-PR-Analysis-System'

@patch('requests.request')
def test_get_pull_requests_single_repo(mock_request: Any, mock_settings: Any, mock_response: Any) -> None:
    """特定のリポジトリのプルリクエスト取得のテスト"""
    # 2ページ分のデータを返すように設定
    mock_response.json.side_effect = [
        [{'id': 1, 'title': 'Test PR 1'}, {'id': 2, 'title': 'Test PR 2'}],  # 1ページ目
        []  # 2ページ目（空のリストで終了）
    ]
    mock_request.return_value = mock_response

    client = GitHubAPIClient(mock_settings)
    prs = client.get_pull_requests('owner1', 'repo1')

    assert len(prs) == 2
    assert prs[0]['id'] == 1
    assert prs[0]['title'] == 'Test PR 1'
    assert prs[1]['id'] == 2
    assert prs[1]['title'] == 'Test PR 2'
    assert mock_request.call_count == 2  # 2回のAPIリクエストを確認

@patch('requests.request')
def test_get_pull_requests_all_repos(mock_request: Any, mock_settings: Any, mock_response: Any) -> None:
    """全リポジトリのプルリクエスト取得のテスト"""
    # 各リポジトリに対して2ページ分のデータを返すように設定
    mock_response.json.side_effect = [
        [{'id': 1, 'title': 'Test PR 1'}, {'id': 2, 'title': 'Test PR 2'}],  # repo1 1ページ目
        [],  # repo1 2ページ目
        [{'id': 3, 'title': 'Test PR 3'}, {'id': 4, 'title': 'Test PR 4'}],  # repo2 1ページ目
        []  # repo2 2ページ目
    ]
    mock_request.return_value = mock_response

    client = GitHubAPIClient(mock_settings)
    prs = client.get_pull_requests()  # 引数を指定しない場合

    assert len(prs) == 4
    assert prs[0]['id'] == 1
    assert prs[0]['title'] == 'Test PR 1'
    assert prs[1]['id'] == 2
    assert prs[1]['title'] == 'Test PR 2'
    assert prs[2]['id'] == 3
    assert prs[2]['title'] == 'Test PR 3'
    assert prs[3]['id'] == 4
    assert prs[3]['title'] == 'Test PR 4'
    assert mock_request.call_count == 4  # 4回のAPIリクエストを確認

@patch('requests.request')
def test_get_issue_comments_single_repo(mock_request: Any, mock_settings: Any, mock_response: Any) -> None:
    """特定のリポジトリのIssueコメント取得のテスト"""
    # 2ページ分のデータを返すように設定
    mock_response.json.side_effect = [
        [{'id': 1, 'body': 'Comment 1'}, {'id': 2, 'body': 'Comment 2'}],  # 1ページ目
        []  # 2ページ目（空のリストで終了）
    ]
    mock_request.return_value = mock_response

    client = GitHubAPIClient(mock_settings)
    comments = client.get_issue_comments('owner1', 'repo1', 1)

    assert len(comments) == 2
    assert comments[0]['id'] == 1
    assert comments[0]['body'] == 'Comment 1'
    assert comments[1]['id'] == 2
    assert comments[1]['body'] == 'Comment 2'
    assert mock_request.call_count == 2  # 2回のAPIリクエストを確認

@patch('requests.request')
def test_get_review_comments_single_repo(mock_request: Any, mock_settings: Any, mock_response: Any) -> None:
    """特定のリポジトリのレビューコメント取得のテスト"""
    # 2ページ分のデータを返すように設定
    mock_response.json.side_effect = [
        [
            {
                'id': 1,
                'body': 'Review Comment 1',
                'path': 'src/main.py',
                'position': 10
            },
            {
                'id': 2,
                'body': 'Review Comment 2',
                'path': 'src/utils.py',
                'position': 15
            }
        ],  # 1ページ目
        []  # 2ページ目（空のリストで終了）
    ]
    mock_request.return_value = mock_response

    client = GitHubAPIClient(mock_settings)
    comments = client.get_review_comments('owner1', 'repo1', 1)

    assert len(comments) == 2
    assert comments[0]['id'] == 1
    assert comments[0]['body'] == 'Review Comment 1'
    assert comments[0]['path'] == 'src/main.py'
    assert comments[0]['position'] == 10
    assert comments[1]['id'] == 2
    assert comments[1]['body'] == 'Review Comment 2'
    assert comments[1]['path'] == 'src/utils.py'
    assert comments[1]['position'] == 15
    assert mock_request.call_count == 2  # 2回のAPIリクエストを確認

@patch('requests.request')
def test_rate_limit_handling(mock_request: Any, mock_settings: Any) -> None:
    """レート制限処理のテスト"""
    response = MagicMock()
    response.headers = {
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
    }
    mock_request.return_value = response

    with patch('time.sleep') as mock_sleep:
        # Create a public wrapper method for testing
        class TestableClient(GitHubAPIClient):
            def handle_rate_limit_test(self, response: Any) -> None:
                return self._handle_rate_limit(response)

        testable_client = TestableClient(mock_settings)
        testable_client.handle_rate_limit_test(response)
        mock_sleep.assert_called_once()

@patch('requests.request')
def test_api_error_handling(mock_request: Any, mock_settings: Any) -> None:
    """APIエラー処理のテスト"""
    mock_request.side_effect = Exception('API Error')

    with pytest.raises(Exception, match='API Error'):
        # Create a public wrapper method for testing
        class TestableClient(GitHubAPIClient):
            def make_request_test(self, method: str, endpoint: str) -> Any:
                return self._make_request(method, endpoint)

        testable_client = TestableClient(mock_settings)
        testable_client.make_request_test('GET', 'test/endpoint')

@patch('requests.request')
def test_nonexistent_repository_error(mock_request: Any, mock_settings: Any, caplog: Any) -> None:
    """存在しないリポジトリへのアクセス時のエラー処理テスト"""
    # ログレベルをDEBUGに設定
    caplog.set_level(logging.DEBUG)

    # 404エラーを返すように設定
    error_response = create_error_response(
        status_code=404,
        url="https://api.github.com/repos/nonexistent_owner/nonexistent_repo/pulls"
    )
    mock_request.return_value = error_response

    client = GitHubAPIClient(mock_settings)

    # 特定のリポジトリが存在しない場合
    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        client.get_pull_requests('nonexistent_owner', 'nonexistent_repo')

    # エラーの詳細を検証
    assert exc_info.value.response.status_code == 404
    assert "404 Not Found" in str(exc_info.value)
    assert "nonexistent_owner/nonexistent_repo" in exc_info.value.response.url

    # ログ出力を検証
    assert "HTTPエラー" in caplog.text
    assert "404 Not Found" in caplog.text
    assert "nonexistent_owner/nonexistent_repo" in caplog.text

@patch('requests.request')
def test_partial_success_with_multiple_repos(mock_request: Any, mock_settings: Any, caplog: Any) -> None:
    """複数のリポジトリのうち一部が失敗する場合の処理テスト"""
    caplog.set_level(logging.DEBUG)

    # 各リポジトリのレスポンスを用意
    success_response1 = create_mock_response(json_data=[{'id': 1, 'title': 'Test PR 1'}])
    success_response1_empty = create_mock_response(json_data=[])
    error_response = create_error_response(
        status_code=404,
        url="https://api.github.com/repos/nonexistent_owner/nonexistent_repo/pulls"
    )
    success_response2 = create_mock_response(json_data=[{'id': 2, 'title': 'Test PR 2'}])
    success_response2_empty = create_mock_response(json_data=[])

    # レスポンスのシーケンスを設定
    mock_request.side_effect = [
        success_response1,      # owner1/repo1の1ページ目
        success_response1_empty,  # owner1/repo1の2ページ目（空）
        error_response,         # nonexistent_owner/nonexistent_repoの1ページ目（404エラー）
        success_response2,      # owner2/repo2の1ページ目
        success_response2_empty   # owner2/repo2の2ページ目（空）
    ]

    mock_settings.repositories = [
        'owner1/repo1',
        'nonexistent_owner/nonexistent_repo',
        'owner2/repo2'
    ]

    client = GitHubAPIClient(mock_settings)

    prs = client.get_pull_requests()

    # 結果の検証
    assert len(prs) == 2
    assert prs[0]['id'] == 1
    assert prs[0]['title'] == 'Test PR 1'
    assert prs[1]['id'] == 2
    assert prs[1]['title'] == 'Test PR 2'

    # APIリクエスト回数の検証
    # 各リポジトリのページ数分呼ばれるが、404は1回で打ち切り
    assert mock_request.call_count == 5

    # ログ出力の検証
    assert "404 Not Found" in caplog.text
    assert "nonexistent_owner/nonexistent_repo" in caplog.text
