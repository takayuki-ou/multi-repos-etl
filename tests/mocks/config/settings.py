import os
import yaml
from typing import Generator, Dict, Any
from unittest.mock import patch

def create_mock_env_vars() -> Generator[None, None, None]:
    """環境変数のモック"""
    # 既存の環境変数をクリア
    with patch.dict(os.environ, {}, clear=True):
        # 新しい環境変数を設定
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

def create_mock_config_data() -> Dict[str, Any]:
    """設定データのモック"""
    return {
        'repositories': ['owner1/repo1', 'owner2/repo2'],
        'fetch_settings': {
            'initial_lookback_days': 30,
            'max_prs_per_request': 100,
            'request_interval': 1
        },
        'db_path': 'test_github_data.db'
    }

def create_mock_config_file() -> str:
    """設定ファイルのモック"""
    return yaml.dump(create_mock_config_data())

def create_invalid_config_file() -> str:
    """無効な設定ファイルのモック"""
    return 'invalid: yaml: content'

def create_missing_repositories_config_file() -> str:
    """リポジトリリストが欠落した設定ファイルのモック"""
    config_data = {'fetch_settings': {'initial_lookback_days': 30}}
    return yaml.dump(config_data)
