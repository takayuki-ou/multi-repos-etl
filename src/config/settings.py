"""
設定ファイルの読み込みと管理を行うモジュール
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# ロギングの設定
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

# プロジェクトのルートディレクトリを取得
ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# 設定ファイルのパス
CONFIG_FILE = ROOT_DIR / "config.yaml"

class ConfigError(Exception):
    """設定エラーの基底例外クラス"""
    pass

class ValidationError(ConfigError):
    """設定検証エラー"""
    pass

class MissingConfigError(ConfigError):
    """設定不足エラー"""
    pass

@dataclass
class DatabaseConfig:
    """データベース設定"""
    host: str = "localhost"
    port: str = "5432"
    database: str = "github_pr_analysis"
    user: str = "postgres"
    password: str = "postgres"
    db_path: str = "github_data.db"
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """環境変数からデータベース設定を作成"""
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'github_pr_analysis'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres'),
            db_path=os.getenv('DB_PATH', 'github_data.db')
        )

@dataclass
class FetchSettings:
    """データ取得設定"""
    max_prs_per_request: int = 100
    request_interval: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FetchSettings':
        """辞書からフェッチ設定を作成"""
        return cls(
            max_prs_per_request=data.get('max_prs_per_request', 100),
            request_interval=data.get('request_interval', 1.0),
            max_retries=data.get('max_retries', 3),
            timeout=data.get('timeout', 30)
        )

class Settings:
    def __init__(self, config_file: Optional[Path] = None):
        """設定の初期化"""
        self.config_file = config_file or CONFIG_FILE
        self.config = self._load_config()
        self._validate_config(self.config)
        
        # 設定オブジェクトの初期化
        self.db_config = DatabaseConfig.from_env()
        self.fetch_settings = FetchSettings.from_dict(self.config.get('fetch_settings', {}))

    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        try:
            if not self.config_file.exists():
                logger.warning(f"設定ファイルが見つかりません: {self.config_file}")
                logger.info("デフォルト設定を使用します")
                return self._get_default_config()
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None:
                    logger.warning("設定ファイルが空です。デフォルト設定を使用します")
                    return self._get_default_config()
                return config
        except yaml.YAMLError as e:
            logger.error(f"YAML設定ファイルの解析に失敗しました: {e}")
            raise ValidationError(f"設定ファイルの解析に失敗: {e}")
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
            raise ConfigError(f"設定ファイルの読み込みに失敗: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        return {
            'repositories': [],
            'fetch_settings': {
                'max_prs_per_request': 100,
                'request_interval': 1.0,
                'max_retries': 3,
                'timeout': 30
            },
            'database': {
                'db_path': 'github_data.db'
            }
        }

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """設定の検証"""
        if not isinstance(config, dict):
            raise ValidationError("設定は辞書形式である必要があります")

        # リポジトリ設定の検証
        repositories = config.get('repositories', [])
        if not isinstance(repositories, list):
            raise ValidationError("repositoriesはリスト形式である必要があります")
        
        for repo in repositories:
            if not isinstance(repo, str):
                raise ValidationError("リポジトリ名は文字列である必要があります")
            if '/' not in repo:
                raise ValidationError(f"リポジトリ名は 'owner/repo' 形式である必要があります: {repo}")

        # フェッチ設定の検証
        fetch_settings = config.get('fetch_settings', {})
        if not isinstance(fetch_settings, dict):
            raise ValidationError("fetch_settingsは辞書形式である必要があります")
        
        if 'max_prs_per_request' in fetch_settings:
            max_prs = fetch_settings['max_prs_per_request']
            if not isinstance(max_prs, int) or max_prs <= 0 or max_prs > 1000:
                raise ValidationError("max_prs_per_requestは1-1000の整数である必要があります")
        
        if 'request_interval' in fetch_settings:
            interval = fetch_settings['request_interval']
            if not isinstance(interval, (int, float)) or interval < 0:
                raise ValidationError("request_intervalは0以上の数値である必要があります")

    @property
    def repositories(self) -> List[str]:
        """対象リポジトリリストを取得"""
        return self.config.get('repositories', [])

    @property
    def github_pat(self) -> str:
        """GitHub Personal Access Tokenを取得"""
        token = os.getenv('GITHUB_PAT')
        if not token:
            raise MissingConfigError("GitHub Personal Access Tokenが設定されていません。GITHUB_PAT環境変数を設定してください")
        
        if len(token) < 10:
            raise ValidationError("GitHub Personal Access Tokenが短すぎます")
        
        return token

    @property
    def db_config_dict(self) -> Dict[str, str]:
        """データベース接続設定を辞書形式で取得"""
        return {
            'host': self.db_config.host,
            'port': self.db_config.port,
            'database': self.db_config.database,
            'user': self.db_config.user,
            'password': self.db_config.password,
            'db_path': self.db_config.db_path
        }

    @property
    def fetch_settings_dict(self) -> Dict[str, Any]:
        """データ取得設定を辞書形式で取得"""
        return {
            'max_prs_per_request': self.fetch_settings.max_prs_per_request,
            'request_interval': self.fetch_settings.request_interval,
            'max_retries': self.fetch_settings.max_retries,
            'timeout': self.fetch_settings.timeout
        }

    @property
    def sqlite_db_path(self) -> str:
        """SQLiteデータベースファイルのパスを取得"""
        db_path_str = self.db_config.db_path
        db_path = Path(db_path_str)
        
        if not db_path.is_absolute():
            db_path = (ROOT_DIR / db_path).resolve()
        
        # ディレクトリが存在しない場合は作成
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(db_path)

    def validate_github_token(self) -> bool:
        """GitHubトークンの有効性を検証"""
        try:
            token = self.github_pat
            # 基本的な形式チェック
            if not token.startswith('ghp_') and not token.startswith('github_pat_'):
                logger.warning("GitHub Personal Access Tokenの形式が正しくない可能性があります")
            return True
        except Exception as e:
            logger.error(f"GitHubトークンの検証に失敗: {e}")
            return False

    def get_config_summary(self) -> Dict[str, Any]:
        """設定の概要を取得"""
        return {
            'repositories_count': len(self.repositories),
            'repositories': self.repositories,
            'fetch_settings': self.fetch_settings_dict,
            'database_path': self.sqlite_db_path,
            'github_token_configured': bool(os.getenv('GITHUB_PAT')),
            'config_file': str(self.config_file)
        }

    def save_config(self, output_path: Optional[Path] = None) -> None:
        """現在の設定をファイルに保存"""
        output_path = output_path or self.config_file
        
        try:
            config_data = {
                'repositories': self.repositories,
                'fetch_settings': self.fetch_settings_dict,
                'database': {
                    'db_path': self.db_config.db_path
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"設定を保存しました: {output_path}")
        except Exception as e:
            logger.error(f"設定の保存に失敗しました: {e}")
            raise ConfigError(f"設定の保存に失敗: {e}")

if __name__ == "__main__":
    """設定のテスト"""
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        settings = Settings()
        logger.info("設定の読み込みが完了しました")
        
        summary = settings.get_config_summary()
        logger.info(f"設定概要: {summary}")
        
        if settings.validate_github_token():
            logger.info("GitHubトークンの検証が完了しました")
        else:
            logger.warning("GitHubトークンの検証に失敗しました")
            
    except Exception as e:
        logger.error(f"設定の初期化に失敗しました: {e}")
        raise
