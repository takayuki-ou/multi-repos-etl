from datetime import datetime
from typing import Optional, Any, Dict, List, Union

MOCK_PR_RESPONSE = {
    "number": 1,
    "title": "テストPR",
    "state": "open",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "body": "テストPRの本文",
    "user": {"login": "testuser"},
    "html_url": "https://github.com/test/repo/pull/1"
}

MOCK_COMMENT_RESPONSE = {
    "id": 1,
    "body": "テストコメント",
    "user": {"login": "reviewer"},
    "created_at": "2024-01-01T01:00:00Z",
    "html_url": "https://github.com/test/repo/pull/1#issuecomment-1"
}

# エラーレスポンス
RATE_LIMIT_ERROR = {
    "message": "API rate limit exceeded",
    "documentation_url": "https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting"
}

NOT_FOUND_ERROR = {
    "message": "Not Found",
    "documentation_url": "https://docs.github.com/rest"
}

# APIレスポンスのモック
def create_mock_response(json_data: Optional[Union[Dict[str, Any], List[Any]]] = None, status_code: int = 200):
    """APIレスポンスのモックを作成"""
    from unittest.mock import MagicMock
    response = MagicMock()
    response.json.return_value = json_data if json_data is not None else [{'id': 1, 'title': 'Test PR'}]
    response.headers = {
        'X-RateLimit-Remaining': '5000',
        'X-RateLimit-Reset': str(int(datetime.now().timestamp()) + 3600)
    }
    response.status_code = status_code
    response.raise_for_status = MagicMock()
    return response

# エラーレスポンスのモック
def create_error_response(status_code: int = 404, url: Optional[str] = None):
    """エラーレスポンスのモックを作成"""
    from unittest.mock import MagicMock
    import requests
    response = MagicMock()
    response.status_code = status_code
    response.url = url or "https://api.github.com/repos/test/repo/pulls"
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        f"{status_code} {'Not Found' if status_code == 404 else 'Error'}",
        response=response
    )
    return response
