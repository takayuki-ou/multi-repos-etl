"""
DataManagerフィルタリング機能の統合テスト
"""
import pytest
import os
import tempfile
from datetime import datetime
from src.gui.data_manager import DataManager
from src.db.database import Database


class TestDataManagerFilteringIntegration:
    """DataManagerフィルタリング機能の統合テストクラス"""

    @pytest.fixture
    def temp_database(self):
        """テスト用の一時データベースを作成"""
        # 一時ファイルを作成
        temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
        os.close(temp_fd)
        
        try:
            # データベースを初期化
            db_config = {'db_path': temp_path}
            db = Database(db_config)
            db.create_tables()
            
            # テストデータを挿入
            self._insert_test_data(db)
            
            yield temp_path
        finally:
            # クリーンアップ
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def _insert_test_data(self, db):
        """テストデータを挿入"""
        from sqlalchemy import text
        
        with db.get_session() as session:
            # リポジトリデータ
            session.execute(text("""
                INSERT INTO repositories (id, owner_login, name, url, created_at, updated_at, fetched_at)
                VALUES (1, 'testowner', 'testrepo', 'https://github.com/testowner/testrepo', 
                        '2023-01-01T00:00:00Z', '2023-01-01T00:00:00Z', '2023-01-01T00:00:00Z')
            """))
            
            # プルリクエストデータ
            test_prs = [
                (1, 1, 1, 'First PR', 'user1', 'closed', '2023-01-01T10:00:00Z', '2023-01-01T12:00:00Z', 
                 '2023-01-01T12:00:00Z', '2023-01-01T12:00:00Z', 'First PR body', 
                 'https://github.com/testowner/testrepo/pull/1', 'https://api.github.com/repos/testowner/testrepo/pulls/1', 
                 '2023-01-01T00:00:00Z'),
                (2, 1, 2, 'Second PR', 'user2', 'closed', '2023-02-01T10:00:00Z', '2023-02-01T14:00:00Z', 
                 '2023-02-01T14:00:00Z', None, 'Second PR body', 
                 'https://github.com/testowner/testrepo/pull/2', 'https://api.github.com/repos/testowner/testrepo/pulls/2', 
                 '2023-02-01T00:00:00Z'),
                (3, 1, 3, 'Third PR', 'user1', 'open', '2023-03-01T10:00:00Z', '2023-03-01T10:00:00Z', 
                 None, None, 'Third PR body', 
                 'https://github.com/testowner/testrepo/pull/3', 'https://api.github.com/repos/testowner/testrepo/pulls/3', 
                 '2023-03-01T00:00:00Z'),
                (4, 1, 4, 'Fourth PR', 'user3', 'closed', '2023-04-01T10:00:00Z', '2023-04-01T16:00:00Z', 
                 '2023-04-01T16:00:00Z', '2023-04-01T16:00:00Z', 'Fourth PR body', 
                 'https://github.com/testowner/testrepo/pull/4', 'https://api.github.com/repos/testowner/testrepo/pulls/4', 
                 '2023-04-01T00:00:00Z')
            ]
            
            for pr_data in test_prs:
                session.execute(text("""
                    INSERT INTO pull_requests 
                    (id, repository_id, number, title, user_login, state, created_at, updated_at, 
                     closed_at, merged_at, body, url, api_url, fetched_at)
                    VALUES (:id, :repository_id, :number, :title, :user_login, :state, :created_at, :updated_at, 
                            :closed_at, :merged_at, :body, :url, :api_url, :fetched_at)
                """), {
                    'id': pr_data[0],
                    'repository_id': pr_data[1],
                    'number': pr_data[2],
                    'title': pr_data[3],
                    'user_login': pr_data[4],
                    'state': pr_data[5],
                    'created_at': pr_data[6],
                    'updated_at': pr_data[7],
                    'closed_at': pr_data[8],
                    'merged_at': pr_data[9],
                    'body': pr_data[10],
                    'url': pr_data[11],
                    'api_url': pr_data[12],
                    'fetched_at': pr_data[13]
                })

    @pytest.fixture
    def data_manager_with_test_db(self, temp_database):
        """テストデータベースを使用するDataManagerを作成"""
        # DataManagerを直接初期化せず、必要な部分のみモック
        from unittest.mock import patch, Mock
        
        with patch('src.gui.data_manager.Settings') as mock_settings:
            mock_settings_instance = Mock()
            mock_settings_instance.sqlite_db_path = temp_database
            mock_settings.return_value = mock_settings_instance
            
            data_manager = DataManager()
            return data_manager

    def test_get_pull_requests_no_filters(self, data_manager_with_test_db):
        """フィルタなしでのPR取得テスト"""
        data_manager = data_manager_with_test_db
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(1)
        
        assert error is None
        assert len(result) == 4
        
        # データが正しく解析されていることを確認
        for pr in result:
            assert pr['created_at_dt'] is not None
            assert pr['updated_at_dt'] is not None
            # closed_at_dt と merged_at_dt は None の場合もある

    def test_get_pull_requests_with_date_filter(self, data_manager_with_test_db):
        """日付フィルタでのPR取得テスト"""
        data_manager = data_manager_with_test_db
        
        start_date = datetime(2023, 2, 1)
        end_date = datetime(2023, 3, 31)
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            start_date=start_date,
            end_date=end_date
        )
        
        assert error is None
        assert len(result) == 2  # user2のPRとuser1のPR
        
        # 日付範囲内のPRのみが取得されていることを確認
        for pr in result:
            created_at = pr['created_at_dt']
            assert start_date <= created_at <= end_date

    def test_get_pull_requests_with_author_filter(self, data_manager_with_test_db):
        """作成者フィルタでのPR取得テスト"""
        data_manager = data_manager_with_test_db
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            author='user1'
        )
        
        assert error is None
        assert len(result) == 2  # user1のPRが2件
        
        # 指定した作成者のPRのみが取得されていることを確認
        for pr in result:
            assert pr['user_login'] == 'user1'

    def test_get_pull_requests_with_combined_filters(self, data_manager_with_test_db):
        """複数フィルタの組み合わせテスト"""
        data_manager = data_manager_with_test_db
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 2, 28)
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            start_date=start_date,
            end_date=end_date,
            author='user1'
        )
        
        assert error is None
        assert len(result) == 1  # user1の1月のPRのみ
        assert result[0]['user_login'] == 'user1'
        assert result[0]['number'] == 1

    def test_get_pull_requests_no_matching_data(self, data_manager_with_test_db):
        """条件に一致するデータがない場合のテスト"""
        data_manager = data_manager_with_test_db
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            author='nonexistent_user'
        )
        
        assert len(result) == 0
        assert error is not None
        assert "指定された条件" in error
        assert "nonexistent_user" in error

    def test_get_authors_for_repository(self, data_manager_with_test_db):
        """作成者一覧取得テスト"""
        data_manager = data_manager_with_test_db
        
        result, error = data_manager.get_authors_for_repository(1)
        
        assert error is None
        assert len(result) == 3
        assert set(result) == {'user1', 'user2', 'user3'}
        assert result == sorted(result)  # アルファベット順にソートされている

    def test_get_authors_for_nonexistent_repository(self, data_manager_with_test_db):
        """存在しないリポジトリの作成者一覧取得テスト"""
        data_manager = data_manager_with_test_db
        
        result, error = data_manager.get_authors_for_repository(999)
        
        assert error is None
        assert len(result) == 0