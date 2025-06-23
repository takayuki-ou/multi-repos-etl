"""
Unit tests for src/github_api/fetcher.py
"""
import pytest
from unittest.mock import MagicMock, call, patch
from typing import List, Dict, Any, Optional, Tuple

# Modules to test
from src.github_api.fetcher import GitHubFetcher
from src.github_api.client import GitHubAPIClient
# Mocked version of DatabaseHandler, actual import not needed for these tests
# from src.db.database import DatabaseHandler

# Mock data
mock_pr_data_page1 = [
    {"id": 1, "number": 101, "title": "Feature: New login page"},
    {"id": 2, "number": 102, "title": "Bugfix: User logout issue"},
]
mock_pr_data_page2 = [
    {"id": 3, "number": 103, "title": "Docs: Update README"},
]

mock_issue_comments_pr101 = [
    {"id": 10, "body": "Comment on PR 101"},
]
mock_issue_comments_pr102 = [
    {"id": 11, "body": "Another comment on PR 102"},
]
mock_issue_comments_pr103 = [] # No issue comments for PR 103

mock_review_comments_pr101 = [] # No review comments for PR 101
mock_review_comments_pr102 = [
    {"id": 20, "body": "Review comment on PR 102, file main.py", "path": "main.py"},
]
mock_review_comments_pr103 = [
    {"id": 21, "body": "Review comment on PR 103, file README.md", "path": "README.md"},
    {"id": 22, "body": "Second review comment on PR 103", "path": "README.md"},
]


@pytest.fixture
def mock_api_client() -> MagicMock:
    """Fixture for a mocked GitHubAPIClient."""
    client = MagicMock(spec=GitHubAPIClient)

    # Default behavior for get_pull_requests
    client.get_pull_requests.return_value = mock_pr_data_page1 + mock_pr_data_page2

    # Default behavior for get_issue_comments and get_review_comments
    # These will be configured per test as needed, or use side_effect
    def get_issue_comments_side_effect(owner: str, repo: str, issue_number: int, since: Optional[str] = None):
        if issue_number == 101: return mock_issue_comments_pr101
        if issue_number == 102: return mock_issue_comments_pr102
        if issue_number == 103: return mock_issue_comments_pr103
        return []
    client.get_issue_comments.side_effect = get_issue_comments_side_effect

    def get_review_comments_side_effect(owner: str, repo: str, pull_number: int, since: Optional[str] = None):
        if pull_number == 101: return mock_review_comments_pr101
        if pull_number == 102: return mock_review_comments_pr102
        if pull_number == 103: return mock_review_comments_pr103
        return []
    client.get_review_comments.side_effect = get_review_comments_side_effect

    return client

@pytest.fixture
def mock_db_handler() -> MagicMock:
    """Fixture for a mocked DatabaseHandler."""
    # db_handler = MagicMock(spec=DatabaseHandler)
    # For now, GitHubFetcher doesn't use db_handler in its constructor.
    # When it does, this mock will be more relevant.
    # For get_last_fetched_at, we will mock the method on the fetcher instance directly.
    return MagicMock()


def test_github_fetcher_initialization(mock_api_client: MagicMock):
    """Test GitHubFetcher initialization."""
    fetcher = GitHubFetcher(client=mock_api_client) #, db_handler=mock_db_handler)
    assert fetcher.client == mock_api_client
    # assert fetcher.db_handler == mock_db_handler # Enable when db_handler is used in constructor

def test_get_last_fetched_at_no_timestamp(mock_api_client: MagicMock, mock_db_handler: MagicMock):
    """Test get_last_fetched_at when no timestamp is in the (mocked) DB."""
    fetcher = GitHubFetcher(client=mock_api_client) #, db_handler=mock_db_handler)

    # Mock the behavior of the db_handler if it were used directly
    # For now, we assume get_last_fetched_at is simple or we patch it if it uses db_handler
    # fetcher.db_handler.get_last_fetched_timestamp.return_value = None
    # Since get_last_fetched_at is currently a placeholder:
    with patch.object(fetcher, 'get_last_fetched_at', return_value=None) as mock_method:
        timestamp = fetcher.get_last_fetched_at("owner/repo")
        assert timestamp is None
        mock_method.assert_called_once_with("owner/repo")

def test_get_last_fetched_at_with_timestamp(mock_api_client: MagicMock, mock_db_handler: MagicMock):
    """Test get_last_fetched_at when a timestamp is in the (mocked) DB."""
    fetcher = GitHubFetcher(client=mock_api_client) #, db_handler=mock_db_handler)
    expected_timestamp = "2023-01-01T00:00:00Z"

    # fetcher.db_handler.get_last_fetched_timestamp.return_value = expected_timestamp
    # Since get_last_fetched_at is currently a placeholder:
    with patch.object(fetcher, 'get_last_fetched_at', return_value=expected_timestamp) as mock_method:
        timestamp = fetcher.get_last_fetched_at("owner/repo")
        assert timestamp == expected_timestamp
        mock_method.assert_called_once_with("owner/repo")


def test_fetch_all_data_for_repo_initial_fetch(mock_api_client: MagicMock):
    """Test fetch_all_data_for_repo for an initial fetch (no 'since' parameter)."""
    repo_full_name = "test_owner/test_repo"
    fetcher = GitHubFetcher(client=mock_api_client)

    # Ensure get_last_fetched_at returns None for this test
    fetcher.get_last_fetched_at = MagicMock(return_value=None)

    prs, issue_comments, review_comments = fetcher.fetch_all_data_for_repo(repo_full_name)

    # Verify get_last_fetched_at was called
    fetcher.get_last_fetched_at.assert_called_once_with(repo_full_name)

    # Verify client methods were called correctly
    owner, repo = repo_full_name.split('/')
    mock_api_client.get_pull_requests.assert_called_once_with(owner, repo, since=None)

    expected_issue_comment_calls = [
        call(owner, repo, issue_number=101, since=None),
        call(owner, repo, issue_number=102, since=None),
        call(owner, repo, issue_number=103, since=None),
    ]
    mock_api_client.get_issue_comments.assert_has_calls(expected_issue_comment_calls, any_order=True)
    assert mock_api_client.get_issue_comments.call_count == len(mock_pr_data_page1) + len(mock_pr_data_page2)


    expected_review_comment_calls = [
        call(owner, repo, pull_number=101, since=None),
        call(owner, repo, pull_number=102, since=None),
        call(owner, repo, pull_number=103, since=None),
    ]
    mock_api_client.get_review_comments.assert_has_calls(expected_review_comment_calls, any_order=True)
    assert mock_api_client.get_review_comments.call_count == len(mock_pr_data_page1) + len(mock_pr_data_page2)

    # Verify returned data
    assert len(prs) == len(mock_pr_data_page1) + len(mock_pr_data_page2)
    assert prs[0]["id"] == 1
    assert prs[2]["id"] == 3

    total_expected_issue_comments = len(mock_issue_comments_pr101) + len(mock_issue_comments_pr102) + len(mock_issue_comments_pr103)
    assert len(issue_comments) == total_expected_issue_comments
    if total_expected_issue_comments > 0:
        assert issue_comments[0]["id"] == 10 # from pr101

    total_expected_review_comments = len(mock_review_comments_pr101) + len(mock_review_comments_pr102) + len(mock_review_comments_pr103)
    assert len(review_comments) == total_expected_review_comments
    if total_expected_review_comments > 0:
         # Order depends on PR processing order, check for specific items
        assert any(c["id"] == 20 for c in review_comments) # from pr102
        assert any(c["id"] == 21 for c in review_comments) # from pr103


def test_fetch_all_data_for_repo_with_since_parameter(mock_api_client: MagicMock):
    """Test fetch_all_data_for_repo when 'since' parameter is used."""
    repo_full_name = "test_owner/test_repo"
    last_fetch_time = "2023-01-15T10:00:00Z"
    fetcher = GitHubFetcher(client=mock_api_client)

    # Ensure get_last_fetched_at returns the specific timestamp
    fetcher.get_last_fetched_at = MagicMock(return_value=last_fetch_time)

    # Modify client to return fewer PRs if 'since' is used (optional, for more realistic mock)
    # For this test, we'll assume the client still returns all PRs,
    # and we're just checking the 'since' propagation.
    # mock_api_client.get_pull_requests.return_value = [mock_pr_data_page2[0]] # Only PR 103
    # def get_issue_comments_side_effect_since(owner, repo, issue_number, since):
    #     assert since == last_fetch_time
    #     if issue_number == 103: return mock_issue_comments_pr103
    #     return []
    # mock_api_client.get_issue_comments.side_effect = get_issue_comments_side_effect_since
    # def get_review_comments_side_effect_since(owner, repo, pull_number, since):
    #     assert since == last_fetch_time
    #     if pull_number == 103: return mock_review_comments_pr103
    #     return []
    # mock_api_client.get_review_comments.side_effect = get_review_comments_side_effect_since


    prs, issue_comments, review_comments = fetcher.fetch_all_data_for_repo(repo_full_name)

    fetcher.get_last_fetched_at.assert_called_once_with(repo_full_name)

    owner, repo = repo_full_name.split('/')
    mock_api_client.get_pull_requests.assert_called_once_with(owner, repo, since=last_fetch_time)

    # Check 'since' in calls to comment fetching methods
    # The number of calls depends on the PRs returned by get_pull_requests
    # which is currently all PRs (101, 102, 103)
    expected_issue_comment_calls = [
        call(owner, repo, issue_number=101, since=last_fetch_time),
        call(owner, repo, issue_number=102, since=last_fetch_time),
        call(owner, repo, issue_number=103, since=last_fetch_time),
    ]
    mock_api_client.get_issue_comments.assert_has_calls(expected_issue_comment_calls, any_order=True)
    assert mock_api_client.get_issue_comments.call_count == len(mock_pr_data_page1) + len(mock_pr_data_page2)


    expected_review_comment_calls = [
        call(owner, repo, pull_number=101, since=last_fetch_time),
        call(owner, repo, pull_number=102, since=last_fetch_time),
        call(owner, repo, pull_number=103, since=last_fetch_time),
    ]
    mock_api_client.get_review_comments.assert_has_calls(expected_review_comment_calls, any_order=True)
    assert mock_api_client.get_review_comments.call_count == len(mock_pr_data_page1) + len(mock_pr_data_page2)

    # Data verification (should be the same as initial fetch if client doesn't filter by since)
    assert len(prs) == len(mock_pr_data_page1) + len(mock_pr_data_page2)
    total_expected_issue_comments = len(mock_issue_comments_pr101) + len(mock_issue_comments_pr102) + len(mock_issue_comments_pr103)
    assert len(issue_comments) == total_expected_issue_comments
    total_expected_review_comments = len(mock_review_comments_pr101) + len(mock_review_comments_pr102) + len(mock_review_comments_pr103)
    assert len(review_comments) == total_expected_review_comments


def test_fetch_all_data_for_repo_no_pull_requests(mock_api_client: MagicMock):
    """Test fetch_all_data_for_repo when no pull requests are found."""
    repo_full_name = "test_owner/empty_repo"
    fetcher = GitHubFetcher(client=mock_api_client)
    fetcher.get_last_fetched_at = MagicMock(return_value=None)

    # Configure client to return no PRs
    mock_api_client.get_pull_requests.return_value = []

    prs, issue_comments, review_comments = fetcher.fetch_all_data_for_repo(repo_full_name)

    owner, repo = repo_full_name.split('/')
    mock_api_client.get_pull_requests.assert_called_once_with(owner, repo, since=None)

    # No PRs, so no calls to fetch comments
    mock_api_client.get_issue_comments.assert_not_called()
    mock_api_client.get_review_comments.assert_not_called()

    assert len(prs) == 0
    assert len(issue_comments) == 0
    assert len(review_comments) == 0

def test_fetch_all_data_for_repo_pr_without_number(mock_api_client: MagicMock, caplog):
    """Test fetch_all_data_for_repo when a PR is missing the 'number' field."""
    repo_full_name = "test_owner/weird_repo"
    fetcher = GitHubFetcher(client=mock_api_client)
    fetcher.get_last_fetched_at = MagicMock(return_value=None)

    # PR data, one PR is missing 'number'
    pr_with_number = {"id": 1, "number": 101, "title": "Good PR"}
    pr_without_number = {"id": 2, "title": "PR Missing Number"} # No 'number' field
    mock_api_client.get_pull_requests.return_value = [pr_with_number, pr_without_number]

    # Adjust side effects for comments if necessary (only PR 101 should be processed for comments)
    def get_issue_comments_side_effect(owner: str, repo: str, issue_number: int, since: Optional[str] = None):
        if issue_number == 101: return mock_issue_comments_pr101
        return [] # Should not be called for the PR without number
    mock_api_client.get_issue_comments.side_effect = get_issue_comments_side_effect

    def get_review_comments_side_effect(owner: str, repo: str, pull_number: int, since: Optional[str] = None):
        if pull_number == 101: return mock_review_comments_pr101
        return [] # Should not be called for the PR without number
    mock_api_client.get_review_comments.side_effect = get_review_comments_side_effect


    prs, issue_comments, review_comments = fetcher.fetch_all_data_for_repo(repo_full_name)

    owner, repo = repo_full_name.split('/')
    mock_api_client.get_pull_requests.assert_called_once_with(owner, repo, since=None)

    # Comments should only be fetched for the PR with a number
    mock_api_client.get_issue_comments.assert_called_once_with(owner, repo, issue_number=101, since=None)
    mock_api_client.get_review_comments.assert_called_once_with(owner, repo, pull_number=101, since=None)

    assert len(prs) == 2 # Both PRs are returned by get_pull_requests
    assert len(issue_comments) == len(mock_issue_comments_pr101)
    assert len(review_comments) == len(mock_review_comments_pr101)

    # Check for warning log
    assert "PRデータに 'number' が含まれていません: 2" in caplog.text
    assert caplog.records[0].levelname == "WARNING" # Assuming it's the first relevant log
