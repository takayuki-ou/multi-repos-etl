"""
設定ファイルの読み込みと管理を行うモジュール
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import yaml
import logging

# ロギングの設定
logger = logging.getLogger(__name__)

# 環境変数の読み込み
load_dotenv()

# プロジェクトのルートディレクトリを取得
ROOT_DIR = Path(__file__).parent.parent.parent

# 設定ファイルのパス
CONFIG_FILE = ROOT_DIR / "config.yaml"

class Settings:
    def __init__(self):
        """設定の初期化"""
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> dict:
        """設定ファイルを読み込む"""
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"設定ファイルの読み込みに失敗しました: {e}")
            raise

    def _validate_config(self):
        """設定の検証"""
        if not self.config.get('repositories'):
            raise ValueError("設定ファイルにリポジトリリストが定義されていません")

    @property
    def repositories(self) -> list:
        """対象リポジトリリストを取得"""
        return self.config.get('repositories', [])

    @property
    def github_token(self) -> str:
        """GitHub Personal Access Tokenを取得"""
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            raise ValueError("GitHub Personal Access Tokenが設定されていません")
        return token

    @property
    def db_config(self) -> dict:
        """データベース接続設定を取得"""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'github_pr_analysis'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'postgres')
        }

    @property
    def fetch_settings(self) -> dict:
        """データ取得設定を取得"""
        return self.config.get('fetch_settings', [])

    @property
    def sqlite_db_path(self) -> str:
        """SQLiteデータベースファイルのパスを取得"""
        db_path_str = self.config.get('db_path', 'github_data.db')
        db_path = Path(db_path_str)
        if not db_path.is_absolute():
            db_path = (ROOT_DIR / db_path).resolve()
        return str(db_path)