import os
import shutil
from integration.db.init_db import init_test_database

def setup_test_environment():
    # ディレクトリ作成
    os.makedirs('tests/integration/logs', exist_ok=True)
    
    # データベース初期化
    init_test_database()
    
    # 設定ファイルのコピー
    shutil.copy(
        'tests/integration/config/test_config.yaml',
        'config.yaml'
    )
    
    # 環境変数の設定
    with open('tests/integration/config/test.env', 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

if __name__ == '__main__':
    setup_test_environment() 