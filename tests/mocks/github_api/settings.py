from unittest.mock import MagicMock
from src.config.settings import Settings

def create_mock_settings():
    """Settingsクラスのモックを作成"""
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