import sqlite3
import os
import sys

# プロジェクトルートをsys.pathに追加
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tests.integration.db.data.sample_data import SAMPLE_PRS, SAMPLE_COMMENTS

# プロジェクトルートからの相対パスでschema.sqlを指定
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '../../../src/db/schema.sql')

def init_test_database():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'test.db')
    
    # データベース接続
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # スキーマの適用
    with open(SCHEMA_PATH, 'r') as f:
        cursor.executescript(f.read())
    
    # サンプルデータの投入
    for pr in SAMPLE_PRS:
        cursor.execute("""
            INSERT INTO pull_requests (
                number, title, state, created_at, updated_at,
                body, author, html_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pr['number'], pr['title'], pr['state'],
            pr['created_at'], pr['updated_at'],
            pr['body'], pr['user']['login'], pr['html_url']
        ))
    
    for comment in SAMPLE_COMMENTS:
        cursor.execute("""
            INSERT INTO review_comments (
                id, body, author, created_at, html_url
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            comment['id'], comment['body'],
            comment['user']['login'],
            comment['created_at'], comment['html_url']
        ))
    
    conn.commit()
    conn.close() 