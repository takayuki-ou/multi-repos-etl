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
            author=None,
            status=None
        )

    def test_get_pull_requests_with_lead_time_data_with_filters_success(self, mock_data_manager):
        """フィルタありでのPR取得成功テスト"""
        data_manager, mock_db = mock_data_manager
        
        # 結果があるケース
        mock_pr_data = [
            {
                'id': 1,
                'number': 1,
                'title': 'Test PR',
                'user_login': 'testuser',
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
        assert len(result) == 1
        assert result[0]['id'] == 1
        
        # DBメソッドが正しい引数で呼ばれたことを確認
        mock_db.get_pull_requests_with_filters.assert_called_once_with(
            repository_id=1,
            start_date=start_date,
            end_date=end_date,
            author=author,
            status=None
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

    def test_validate_filter_combination_valid_filters(self, mock_data_manager):
        """有効なフィルタ組み合わせのテスト"""
        data_manager, _ = mock_data_manager
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        author = 'testuser'
        
        # テスト実行
        is_valid, error = data_manager.validate_filter_combination(start_date, end_date, author)
        
        # 検証
        assert is_valid is True
        assert error is None

    def test_validate_filter_combination_invalid_date_range(self, mock_data_manager):
        """無効な日付範囲のテスト"""
        data_manager, _ = mock_data_manager
        
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)  # 開始日が終了日より後
        
        # テスト実行
        is_valid, error = data_manager.validate_filter_combination(start_date, end_date)
        
        # 検証
        assert is_valid is False
        assert error is not None
        assert "開始日は終了日より前の日付を指定してください" in error

    def test_validate_filter_combination_empty_author(self, mock_data_manager):
        """空の作成者名のテスト"""
        data_manager, _ = mock_data_manager
        
        # テスト実行
        is_valid, error = data_manager.validate_filter_combination(author='   ')
        
        # 検証
        assert is_valid is False
        assert error is not None
        assert "作成者名が空です" in error

    def test_validate_filter_combination_long_author_name(self, mock_data_manager):
        """長すぎる作成者名のテスト"""
        data_manager, _ = mock_data_manager
        
        long_author = 'a' * 101  # 101文字
        
        # テスト実行
        is_valid, error = data_manager.validate_filter_combination(author=long_author)
        
        # 検証
        assert is_valid is False
        assert error is not None
        assert "作成者名が長すぎます" in error

    def test_get_pull_requests_with_lead_time_data_empty_result_with_message(self, mock_data_manager):
        """フィルタ結果が空の場合のメッセージテスト"""
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
        assert result == []
        assert error is not None
        assert "指定された条件" in error
        assert "開始日: 2023-01-01" in error
        assert "終了日: 2023-12-31" in error
        assert "作成者: testuser" in error
        assert "に一致するプルリクエストが見つかりませんでした" in error

    def test_get_pull_requests_with_lead_time_data_with_status_filter(self, mock_data_manager):
        """ステータスフィルタでのPR取得テスト"""
        data_manager, mock_db = mock_data_manager
        
        mock_pr_data = [
            {
                'id': 1,
                'number': 1,
                'title': 'Closed PR',
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
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            status='closed'
        )
        
        # 検証
        assert error is None
        assert len(result) == 1
        assert result[0]['state'] == 'closed'
        
        # DBメソッドが正しい引数で呼ばれたことを確認
        mock_db.get_pull_requests_with_filters.assert_called_once_with(
            repository_id=1,
            start_date=None,
            end_date=None,
            author=None,
            status='closed'
        )

    def test_validate_filter_combination_invalid_status(self, mock_data_manager):
        """無効なステータスのテスト"""
        data_manager, _ = mock_data_manager
        
        # テスト実行
        is_valid, error = data_manager.validate_filter_combination(status='invalid_status')
        
        # 検証
        assert is_valid is False
        assert error is not None
        assert "無効なステータスです" in error
        assert "open, closed" in error

    def test_validate_filter_combination_valid_status(self, mock_data_manager):
        """有効なステータスのテスト"""
        data_manager, _ = mock_data_manager
        
        for valid_status in ['open', 'closed']:
            # テスト実行
            is_valid, error = data_manager.validate_filter_combination(status=valid_status)
            
            # 検証
            assert is_valid is True
            assert error is None

    def test_get_pull_requests_with_lead_time_data_invalid_filters(self, mock_data_manager):
        """無効なフィルタでのテスト"""
        data_manager, mock_db = mock_data_manager
        
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)  # 無効な日付範囲
        
        # テスト実行
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            start_date=start_date,
            end_date=end_date
        )
        
        # 検証
        assert result == []
        assert error is not None
        assert "開始日は終了日より前の日付を指定してください" in error
        
        # DBメソッドが呼ばれていないことを確認
        mock_db.get_pull_requests_with_filters.assert_not_called()