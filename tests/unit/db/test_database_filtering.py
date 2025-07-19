"""
Databaseクラスのフィルタリング機能のテスト
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from src.db.database import Database


class TestDatabaseFiltering:
    """Databaseクラスのフィルタリング機能のテストクラス"""

    @pytest.fixture
    def mock_database(self):
        """モックされたDatabaseを作成"""
        with patch('src.db.database.create_engine'), \
             patch('src.db.database.scoped_session'):
            
            db = Database({'db_path': 'test.db'})
            return db

    def test_get_pull_requests_with_filters_no_filters(self, mock_database):
        """フィルタなしでのクエリ構築テスト"""
        db = mock_database
        
        # モックセッションの設定
        mock_session = Mock()
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = 1
        mock_row.number = 1
        mock_row.title = 'Test PR'
        mock_row.user_login = 'user1'
        mock_row.state = 'closed'
        mock_row.created_at = '2023-01-01T10:00:00Z'
        mock_row.updated_at = '2023-01-02T10:00:00Z'
        mock_row.closed_at = '2023-01-02T10:00:00Z'
        mock_row.merged_at = '2023-01-02T10:00:00Z'
        mock_row.url = 'https://github.com/test/repo/pull/1'
        mock_row.body = 'Test body'
        
        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        mock_session.execute.return_value = mock_result
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # テスト実行
            result = db.get_pull_requests_with_filters(repository_id=1)
            
            # 検証
            assert len(result) == 1
            assert result[0]['id'] == 1
            assert result[0]['title'] == 'Test PR'
            
            # 正しいクエリが実行されたことを確認
            mock_session.execute.assert_called_once()
            call_args = mock_session.execute.call_args
            query_text = str(call_args[0][0])
            params = call_args[0][1]
            
            assert 'repository_id = :repo_id' in query_text
            assert 'ORDER BY created_at DESC' in query_text
            assert params['repo_id'] == 1

    def test_get_pull_requests_with_filters_with_date_range(self, mock_database):
        """日付範囲フィルタのテスト"""
        db = mock_database
        
        mock_session = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.execute.return_value = mock_result
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # テスト実行
            result = db.get_pull_requests_with_filters(
                repository_id=1,
                start_date=start_date,
                end_date=end_date
            )
            
            # 検証
            assert result == []
            
            # 正しいクエリが実行されたことを確認
            call_args = mock_session.execute.call_args
            query_text = str(call_args[0][0])
            params = call_args[0][1]
            
            assert 'created_at >= :start_date' in query_text
            assert 'created_at <= :end_date' in query_text
            assert params['start_date'] == start_date.isoformat()
            assert params['end_date'] == end_date.isoformat()

    def test_get_pull_requests_with_filters_with_author(self, mock_database):
        """作成者フィルタのテスト"""
        db = mock_database
        
        mock_session = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.execute.return_value = mock_result
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # テスト実行
            result = db.get_pull_requests_with_filters(
                repository_id=1,
                author='testuser'
            )
            
            # 検証
            assert result == []
            
            # 正しいクエリが実行されたことを確認
            call_args = mock_session.execute.call_args
            query_text = str(call_args[0][0])
            params = call_args[0][1]
            
            assert 'user_login = :author' in query_text
            assert params['author'] == 'testuser'

    def test_get_pull_requests_with_filters_all_filters(self, mock_database):
        """すべてのフィルタを適用したテスト"""
        db = mock_database
        
        mock_session = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.execute.return_value = mock_result
        
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        author = 'testuser'
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # テスト実行
            result = db.get_pull_requests_with_filters(
                repository_id=1,
                start_date=start_date,
                end_date=end_date,
                author=author
            )
            
            # 検証
            assert result == []
            
            # 正しいクエリが実行されたことを確認
            call_args = mock_session.execute.call_args
            query_text = str(call_args[0][0])
            params = call_args[0][1]
            
            assert 'repository_id = :repo_id' in query_text
            assert 'created_at >= :start_date' in query_text
            assert 'created_at <= :end_date' in query_text
            assert 'user_login = :author' in query_text
            assert params['repo_id'] == 1
            assert params['start_date'] == start_date.isoformat()
            assert params['end_date'] == end_date.isoformat()
            assert params['author'] == author

    def test_get_authors_for_repository_success(self, mock_database):
        """作成者一覧取得の成功テスト"""
        db = mock_database
        
        mock_session = Mock()
        mock_result = Mock()
        
        # モック行データ
        mock_rows = [Mock(user_login='user1'), Mock(user_login='user2'), Mock(user_login='user3')]
        mock_result.__iter__ = Mock(return_value=iter(mock_rows))
        mock_session.execute.return_value = mock_result
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # テスト実行
            result = db.get_authors_for_repository(1)
            
            # 検証
            assert result == ['user1', 'user2', 'user3']
            
            # 正しいクエリが実行されたことを確認
            call_args = mock_session.execute.call_args
            query_text = str(call_args[0][0])
            params = call_args[0][1]
            
            assert 'DISTINCT user_login' in query_text
            assert 'repository_id = :repo_id' in query_text
            assert 'ORDER BY user_login' in query_text
            assert params['repo_id'] == 1

    def test_get_pull_requests_with_filters_invalid_date_range(self, mock_database):
        """無効な日付範囲のテスト"""
        db = mock_database
        
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)  # 開始日が終了日より後
        
        # テスト実行
        result = db.get_pull_requests_with_filters(
            repository_id=1,
            start_date=start_date,
            end_date=end_date
        )
        
        # 検証
        assert result == []

    def test_get_pull_requests_with_filters_empty_result_with_filters(self, mock_database):
        """フィルタ適用時の空結果テスト"""
        db = mock_database
        
        mock_session = Mock()
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.execute.return_value = mock_result
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            # テスト実行
            result = db.get_pull_requests_with_filters(
                repository_id=1,
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                author='nonexistent_user'
            )
            
            # 検証
            assert result == []
            
            # 正しいクエリが実行されたことを確認（ANDロジック）
            call_args = mock_session.execute.call_args
            query_text = str(call_args[0][0])
            params = call_args[0][1]
            
            assert 'repository_id = :repo_id' in query_text
            assert 'created_at >= :start_date' in query_text
            assert 'created_at <= :end_date' in query_text
            assert 'user_login = :author' in query_text
            assert params['author'] == 'nonexistent_user'

    def test_get_pull_requests_with_filters_database_error(self, mock_database):
        """データベースエラー時のテスト"""
        db = mock_database
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection error")
            
            # テスト実行
            result = db.get_pull_requests_with_filters(repository_id=1)
            
            # 検証
            assert result == []

    def test_get_authors_for_repository_database_error(self, mock_database):
        """作成者一覧取得のエラーテスト"""
        db = mock_database
        
        with patch.object(db, 'get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection error")
            
            # テスト実行
            result = db.get_authors_for_repository(1)
            
            # 検証
            assert result == []