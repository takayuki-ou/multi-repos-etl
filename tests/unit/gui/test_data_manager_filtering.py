"""
DataManagerのフィルタリング機能のテスト
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.gui.data_manager import DataManager


class TestDataManagerFiltering:
    """DataManagerのフィルタリング機能のテストクラス"""

    @pytest.fixture
    def mock_data_manager(self):
        """モックされたDataManagerを作成"""
        with patch('src.gui.data_manager.Settings'), \
             patch('src.gui.data_manager.Database') as mock_db_class:
            
            mock_db = Mock()
            mock_db_class.return_value = mock_db
            
            data_manager = DataManager()
            data_manager.db = mock_db
            
            return data_manager, mock_db

    def test_get_pull_requests_with_lead_time_data_no_filters(self, mock_data_manager):
        """フィルタなしでのPR取得テスト"""
        data_manager, mock_db = mock_data_manager
        
        # モックデータの設定
        mock_pr_data = [
            {
                'id': 1,
                'number': 1,
                'title': 'Test PR 1',
                'user_login': 'user1',
                'state': 'closed',
                'created_at': '2023-01-01T10:00:00Z',
                'updated_at': '2023-01-02T10:00:00Z',
                'closed_at': '2023-01-02T10:00:00Z',
                'merged_at': '2023-01-02T10:00:00Z',
                'url': 'https://github.com/test/repo/pull/1',
                'body': 'Test PR body'
            }
        ]
        
        mock_db.get_pull_requests_with_filters.return_value = mock_pr_data
        
        # テスト実行
        result, error = data_manager.get_pull_requests_with_lead_time_data(1)
        
        # 検証
        assert error is None
        assert len(result) == 1
        assert result[0]['id'] == 1
        assert result[0]['created_at_dt'] is not None
        assert result[0]['closed_at_dt'] is not None
        assert result[0]['merged_at_dt'] is not None
        
        # DBメソッドが正しい引数で呼ばれたことを確認
        mock_db.get_pull_requests_with_filters.assert_called_once_with(
            repository_id=1,
            start_date=None,
            end_date=None,
            author=None
        )

    def test_get_pull_requests_with_lead_time_data_with_filters(self, mock_data_manager):
        """フィルタありでのPR取得テスト"""
        data_manager, mock_db = mock_data_manager
        
        mock_db.get_pull_requests_with_filters.return_value = []
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        author = 'testuser'
        
        # テスト実行
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            start_date=start_date,
            end_date=end_date,
            author=author
        )
        
        # 検証
        assert error is None
        assert result == []
        
        # DBメソッドが正しい引数で呼ばれたことを確認
        mock_db.get_pull_requests_with_filters.assert_called_once_with(
            repository_id=1,
            start_date=start_date,
            end_date=end_date,
            author=author
        )

    def test_get_pull_requests_with_lead_time_data_database_error(self, mock_data_manager):
        """データベースエラー時のテスト"""
        data_manager, mock_db = mock_data_manager
        
        mock_db.get_pull_requests_with_filters.side_effect = Exception("Database error")
        
        # テスト実行
        result, error = data_manager.get_pull_requests_with_lead_time_data(1)
        
        # 検証
        assert result is None
        assert error is not None
        assert "Database error while fetching filtered pull requests" in error

    def test_get_authors_for_repository_success(self, mock_data_manager):
        """作成者一覧取得の成功テスト"""
        data_manager, mock_db = mock_data_manager
        
        mock_authors = ['user1', 'user2', 'user3']
        mock_db.get_authors_for_repository.return_value = mock_authors
        
        # テスト実行
        result, error = data_manager.get_authors_for_repository(1)
        
        # 検証
        assert error is None
        assert result == mock_authors
        mock_db.get_authors_for_repository.assert_called_once_with(1)

    def test_get_authors_for_repository_database_error(self, mock_data_manager):
        """作成者一覧取得のエラーテスト"""
        data_manager, mock_db = mock_data_manager
        
        mock_db.get_authors_for_repository.side_effect = Exception("Database error")
        
        # テスト実行
        result, error = data_manager.get_authors_for_repository(1)
        
        # 検証
        assert result == []
        assert error is not None
        assert "Database error while fetching authors" in error

    def test_datetime_parsing_with_various_formats(self, mock_data_manager):
        """様々な日時形式の解析テスト"""
        data_manager, mock_db = mock_data_manager
        
        mock_pr_data = [
            {
                'id': 1,
                'number': 1,
                'title': 'Test PR',
                'user_login': 'user1',
                'state': 'closed',
                'created_at': '2023-01-01T10:00:00Z',  # ISO format
                'updated_at': '2023-01-02 10:00:00',   # SQLite format
                'closed_at': None,                      # None value
                'merged_at': '2023-01-02T10:00:00Z',
                'url': 'https://github.com/test/repo/pull/1',
                'body': 'Test PR body'
            }
        ]
        
        mock_db.get_pull_requests_with_filters.return_value = mock_pr_data
        
        # テスト実行
        result, error = data_manager.get_pull_requests_with_lead_time_data(1)
        
        # 検証
        assert error is None
        assert len(result) == 1
        assert result[0]['created_at_dt'] is not None
        assert result[0]['updated_at_dt'] is not None
        assert result[0]['closed_at_dt'] is None  # None should remain None
        assert result[0]['merged_at_dt'] is not None