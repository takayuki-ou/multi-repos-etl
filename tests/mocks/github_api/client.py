from unittest.mock import Mock
from .responses import MOCK_PR_RESPONSE, MOCK_COMMENT_RESPONSE

class MockGitHubClient:
    def __init__(self):
        self.mock = Mock()
        self.setup_mock_responses()
    
    def setup_mock_responses(self):
        self.mock.get_pull_requests.return_value = [MOCK_PR_RESPONSE]
        self.mock.get_review_comments.return_value = [MOCK_COMMENT_RESPONSE]
        
    def get_pull_requests(self, repo, state=None):
        return self.mock.get_pull_requests(repo, state)
        
    def get_review_comments(self, repo, pr_number):
        return self.mock.get_review_comments(repo, pr_number) 