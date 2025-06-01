"""
settings.pyのテストコード
"""
import os
import pytest
from unittest.mock import patch, mock_open
from typing import Any, Generator
import yaml
from src.config.settings import Settings

@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """環境変数のモック"""
    with patch.dict(os.environ, {
        'GITHUB_TOKEN': 'test_token',
        'DB_HOST': 'test_host',
        'DB_PORT': '5432',
        'DB_NAME': 'test_db',
        'DB_USER': 'test_user',
        'DB_PASSWORD': 'test_password',
        'APP_ENV': 'test',
        'LOG_LEVEL': 'DEBUG'
    }):
        yield

@pytest.fixture
def mock_config_file() -> str:
    """設定ファイルのモック"""
    config_data = {
        'repositories': ['owner1/repo1', 'owner2/repo2'],
        'fetch_settings': {
            'initial_lookback_days': 30,
            'max_prs_per_request': 100,
            'request_interval': 1
        }
    }
    return yaml.dump(config_data)

def test_settings_initialization(mock_env_vars: Any, mock_config_file: str) -> None:
    """Settingsクラスの初期化テスト"""
    with patch('builtins.open', mock_open(read_data=mock_config_file)):
        settings = Settings()
        
        # リポジトリリストの確認
        assert settings.repositories == ['owner1/repo1', 'owner2/repo2']
        
        # GitHubトークンの確認
        assert settings.github_token == 'test_token'
        
        # データベース設定の確認
        db_config = settings.db_config
        assert db_config['host'] == 'test_host'
        assert db_config['port'] == '5432'
        assert db_config['database'] == 'test_db'
        assert db_config['user'] == 'test_user'
        assert db_config['password'] == 'test_password'
        
        # フェッチ設定の確認
        fetch_settings = settings.fetch_settings
        assert fetch_settings['initial_lookback_days'] == 30
        assert fetch_settings['max_prs_per_request'] == 100
        assert fetch_settings['request_interval'] == 1

def test_missing_github_token() -> None:
    """GitHubトークンが設定されていない場合のテスト"""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        with pytest.raises(ValueError, match="GitHub Personal Access Tokenが設定されていません"):
            _ = settings.github_token

def test_invalid_config_file() -> None:
    """無効な設定ファイルのテスト"""
    with patch('builtins.open', mock_open(read_data='invalid: yaml: content')):
        with pytest.raises(Exception):
            Settings()

def test_missing_repositories() -> None:
    """リポジトリリストが設定されていない場合のテスト"""
    config_data = {'fetch_settings': {'initial_lookback_days': 30}}
    with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
        with pytest.raises(ValueError, match="設定ファイルにリポジトリリストが定義されていません"):
            Settings() 