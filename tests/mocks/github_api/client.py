from unittest.mock import Mock
from typing import List, Dict, Any, Optional
from .responses import MOCK_PR_RESPONSE, MOCK_COMMENT_RESPONSE

class MockGitHubClient:
    def __init__(self):
        self.mock = Mock()
        self.setup_mock_responses()

    def setup_mock_responses(self):
        self.mock.get_pull_requests.return_value = [MOCK_PR_RESPONSE]
        self.mock.get_review_comments.return_value = [MOCK_COMMENT_RESPONSE]

    def get_pull_requests(self, repo: str, state: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.mock.get_pull_requests(repo, state)

    def get_review_comments(self, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        return self.mock.get_review_comments(repo, pr_number)
