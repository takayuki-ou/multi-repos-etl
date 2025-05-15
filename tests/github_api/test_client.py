"""
client.pyのテストコード
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import requests
import logging
from src.github_api.client import GitHubAPIClient
from src.config.settings import Settings

@pytest.fixture
def mock_settings():
    """Settingsクラスのモック"""
    settings = MagicMock(spec=Settings)
    settings.github_token = 'test_token'
    settings.fetch_settings = {
        'max_prs_per_request': 100,
        'request_interval': 0,
        'initial_lookback_days': 30
    }
    settings.repositories = [
        'owner1/repo1',
        'owner2/repo2'
    ]
    settings.logging = {
        'level': 'INFO',
        'file': 'logs/test.log',
        'format': "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
    return settings

@pytest.fixture
def mock_response():
    """APIレスポンスのモック"""
    response = MagicMock()
    response.json.return_value = [{'id': 1, 'title': 'Test PR'}]
    response.headers = {
        'X-RateLimit-Remaining': '5000',
        'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
    }
    response.status_code = 200
    response.raise_for_status = MagicMock()
    return response

def test_github_api_client_initialization(mock_settings):
    """GitHubAPIClientの初期化テスト"""
    client = GitHubAPIClient(mock_settings)
    assert client.headers['Authorization'] == 'token test_token'
    assert client.headers['Accept'] == 'application/vnd.github.v3+json'
    assert client.headers['User-Agent'] == 'GitHub-PR-Analysis-System'

@patch('requests.request')
def test_get_pull_requests_single_repo(mock_request, mock_settings, mock_response):
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
def test_get_pull_requests_all_repos(mock_request, mock_settings, mock_response):
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
def test_get_issue_comments_single_repo(mock_request, mock_settings, mock_response):
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
def test_get_review_comments_single_repo(mock_request, mock_settings, mock_response):
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
def test_rate_limit_handling(mock_request, mock_settings):
    """レート制限処理のテスト"""
    response = MagicMock()
    response.headers = {
        'X-RateLimit-Remaining': '0',
        'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
    }
    mock_request.return_value = response
    
    client = GitHubAPIClient(mock_settings)
    with patch('time.sleep') as mock_sleep:
        client._handle_rate_limit(response)
        mock_sleep.assert_called_once()

@patch('requests.request')
def test_api_error_handling(mock_request, mock_settings):
    """APIエラー処理のテスト"""
    mock_request.side_effect = Exception('API Error')
    
    client = GitHubAPIClient(mock_settings)
    with pytest.raises(Exception, match='API Error'):
        client._make_request('GET', 'test/endpoint')

@patch('requests.request')
def test_nonexistent_repository_error(mock_request, mock_settings, caplog):
    """存在しないリポジトリへのアクセス時のエラー処理テスト"""
    # ログレベルをDEBUGに設定
    caplog.set_level(logging.DEBUG)
    
    # 404エラーを返すように設定
    response = MagicMock()
    response.status_code = 404
    response.url = "https://api.github.com/repos/nonexistent_owner/nonexistent_repo/pulls"
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found",
        response=response
    )
    mock_request.return_value = response
    
    client = GitHubAPIClient(mock_settings)
    
    # 特定のリポジトリが存在しない場合
    with pytest.raises(requests.exceptions.HTTPError) as exc_info:
        client.get_pull_requests('nonexistent_owner', 'nonexistent_repo')
    
    # エラーの詳細を検証
    assert exc_info.value.response.status_code == 404
    assert "404 Not Found" in str(exc_info.value)
    assert "nonexistent_owner/nonexistent_repo" in exc_info.value.response.url
    
    # ログ出力を検証
    assert "APIリクエストエラー" in caplog.text
    assert "404 Not Found" in caplog.text
    assert "nonexistent_owner/nonexistent_repo" in caplog.text

@patch('requests.request')
def test_partial_success_with_multiple_repos(mock_request, mock_settings, caplog):
    """複数のリポジトリのうち一部が失敗する場合の処理テスト"""
    # ログレベルをDEBUGに設定
    caplog.set_level(logging.DEBUG)
    
    # 成功と失敗を交互に返すように設定
    success_response1 = MagicMock()
    success_response1.status_code = 200
    success_response1.json.return_value = [{'id': 1, 'title': 'Test PR 1'}]
    success_response1.raise_for_status = MagicMock()
    success_response1.headers = {
        'X-RateLimit-Remaining': '5000',
        'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
    }
    
    success_response1_empty = MagicMock()
    success_response1_empty.status_code = 200
    success_response1_empty.json.return_value = []
    success_response1_empty.raise_for_status = MagicMock()
    success_response1_empty.headers = success_response1.headers.copy()
    
    error_response = MagicMock()
    error_response.status_code = 404
    error_response.url = "https://api.github.com/repos/nonexistent_owner/nonexistent_repo/pulls"
    error_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "404 Not Found",
        response=error_response
    )
    error_response.headers = success_response1.headers.copy()
    
    success_response2 = MagicMock()
    success_response2.status_code = 200
    success_response2.json.return_value = [{'id': 2, 'title': 'Test PR 2'}]
    success_response2.raise_for_status = MagicMock()
    success_response2.headers = success_response1.headers.copy()
    
    success_response2_empty = MagicMock()
    success_response2_empty.status_code = 200
    success_response2_empty.json.return_value = []
    success_response2_empty.raise_for_status = MagicMock()
    success_response2_empty.headers = success_response1.headers.copy()
    
    # レスポンスのシーケンスを設定
    mock_request.side_effect = [
        success_response1,      # owner1/repo1の1ページ目
        success_response1_empty,  # owner1/repo1の2ページ目（空）
        error_response,         # nonexistent_owner/nonexistent_repoでエラー
        success_response2,      # owner2/repo2の1ページ目
        success_response2_empty   # owner2/repo2の2ページ目（空）
    ]
    
    mock_settings.repositories = [
        'owner1/repo1',
        'nonexistent_owner/nonexistent_repo',
        'owner2/repo2'
    ]
    
    client = GitHubAPIClient(mock_settings)
    
    # エラーが発生しても処理は継続され、成功したリポジトリのデータは取得できる
    prs = client.get_pull_requests()
    
    # 結果の検証
    assert len(prs) == 2  # 2つのリポジトリからデータを取得
    assert prs[0]['id'] == 1
    assert prs[0]['title'] == 'Test PR 1'
    assert prs[1]['id'] == 2
    assert prs[1]['title'] == 'Test PR 2'
    
    # APIリクエスト回数の検証
    assert mock_request.call_count == 5  # 各リポジトリに対して2回ずつ（2ページ目は空）、エラーのリポジトリに1回
    
    # ログ出力の検証
    assert "APIリクエストエラー" in caplog.text
    assert "404 Not Found" in caplog.text
    assert "nonexistent_owner/nonexistent_repo" in caplog.text
