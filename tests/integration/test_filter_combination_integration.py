"""
フィルタ条件組み合わせ処理の統合テスト
"""
import pytest
import tempfile
import os
from datetime import datetime
from src.gui.data_manager import DataManager
from src.db.database import Database


class TestFilterCombinationIntegration:
    """フィルタ条件組み合わせ処理の統合テストクラス"""

    @pytest.fixture
    def temp_db_path(self):
        """一時的なデータベースファイルを作成"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
            temp_path = temp_file.name
        yield temp_path
        # クリーンアップ
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def test_database(self, temp_db_path):
        """テスト用データベースを作成"""
        db = Database({'db_path': temp_db_path})
        db.create_tables()
        
        # テストデータの挿入
        from sqlalchemy import text
        with db.get_session() as session:
            # リポジトリの挿入
            session.execute(text("""
                INSERT INTO repositories (id, owner_login, name, url, created_at, updated_at, fetched_at)
                VALUES (1, 'testowner', 'testrepo', 'https://github.com/testowner/testrepo', 
                        '2023-01-01T00:00:00Z', '2023-01-01T00:00:00Z', '2023-01-01T00:00:00Z')
            """))
            
            # プルリクエストの挿入
            test_prs = [
                (1, 1, 'PR 1', 'user1', 'closed', '2023-01-15T10:00:00Z', '2023-01-16T10:00:00Z', 
                 '2023-01-16T10:00:00Z', '2023-01-16T10:00:00Z', 'Test PR 1'),
                (2, 2, 'PR 2', 'user2', 'closed', '2023-02-15T10:00:00Z', '2023-02-16T10:00:00Z', 
                 '2023-02-16T10:00:00Z', '2023-02-16T10:00:00Z', 'Test PR 2'),
                (3, 3, 'PR 3', 'user1', 'closed', '2023-03-15T10:00:00Z', '2023-03-16T10:00:00Z', 
                 '2023-03-16T10:00:00Z', '2023-03-16T10:00:00Z', 'Test PR 3'),
                (4, 4, 'PR 4', 'user3', 'closed', '2023-06-15T10:00:00Z', '2023-06-16T10:00:00Z', 
                 '2023-06-16T10:00:00Z', '2023-06-16T10:00:00Z', 'Test PR 4'),
            ]
            
            for pr_data in test_prs:
                session.execute(text("""
                    INSERT INTO pull_requests 
                    (id, repository_id, number, title, user_login, state, created_at, updated_at, 
                     closed_at, merged_at, body, url, api_url, fetched_at)
                    VALUES (:id, 1, :number, :title, :user_login, :state, :created_at, :updated_at, 
                            :closed_at, :merged_at, :body, 
                            'https://github.com/testowner/testrepo/pull/' || :number, 
                            'https://api.github.com/repos/testowner/testrepo/pulls/' || :number, 
                            '2023-01-01T00:00:00Z')
                """), {
                    'id': pr_data[0],
                    'number': pr_data[1],
                    'title': pr_data[2],
                    'user_login': pr_data[3],
                    'state': pr_data[4],
                    'created_at': pr_data[5],
                    'updated_at': pr_data[6],
                    'closed_at': pr_data[7],
                    'merged_at': pr_data[8],
                    'body': pr_data[9]
                })
            
            session.commit()
        
        return db

    def test_filter_combination_and_logic(self, test_database):
        """複数フィルタのANDロジックテスト"""
        # 日付範囲とユーザーの組み合わせ
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)
        author = 'user1'
        
        result = test_database.get_pull_requests_with_filters(
            repository_id=1,
            start_date=start_date,
            end_date=end_date,
            author=author
        )
        
        # user1かつ2023年1-3月のPRは2件（PR1とPR3）
        assert len(result) == 2
        assert all(pr['user_login'] == 'user1' for pr in result)
        assert all('2023-01' in pr['created_at'] or '2023-03' in pr['created_at'] for pr in result)

    def test_filter_combination_empty_result(self, test_database):
        """フィルタ結果が空の場合のテスト"""
        # 存在しないユーザーでフィルタ
        result = test_database.get_pull_requests_with_filters(
            repository_id=1,
            author='nonexistent_user'
        )
        
        assert len(result) == 0

    def test_filter_combination_date_range_only(self, test_database):
        """日付範囲のみのフィルタテスト"""
        start_date = datetime(2023, 2, 1)
        end_date = datetime(2023, 3, 31)
        
        result = test_database.get_pull_requests_with_filters(
            repository_id=1,
            start_date=start_date,
            end_date=end_date
        )
        
        # 2023年2-3月のPRは2件（PR2とPR3）
        assert len(result) == 2
        assert all('2023-02' in pr['created_at'] or '2023-03' in pr['created_at'] for pr in result)

    def test_filter_combination_author_only(self, test_database):
        """作成者のみのフィルタテスト"""
        result = test_database.get_pull_requests_with_filters(
            repository_id=1,
            author='user1'
        )
        
        # user1のPRは2件（PR1とPR3）
        assert len(result) == 2
        assert all(pr['user_login'] == 'user1' for pr in result)

    def test_filter_combination_invalid_date_range(self, test_database):
        """無効な日付範囲のテスト"""
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)  # 開始日が終了日より後
        
        result = test_database.get_pull_requests_with_filters(
            repository_id=1,
            start_date=start_date,
            end_date=end_date
        )
        
        # 無効な日付範囲の場合は空の結果
        assert len(result) == 0

    def test_data_manager_filter_combination_with_validation(self, test_database, monkeypatch):
        """DataManagerでのフィルタ組み合わせと検証のテスト"""
        # DataManagerのDBを差し替え
        def mock_init(self):
            self.db = test_database
        
        monkeypatch.setattr(DataManager, '__init__', mock_init)
        
        data_manager = DataManager()
        
        # 有効なフィルタ組み合わせ
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)
        author = 'user1'
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            start_date=start_date,
            end_date=end_date,
            author=author
        )
        
        assert error is None
        assert len(result) == 2
        assert all(pr['user_login'] == 'user1' for pr in result)

    def test_data_manager_filter_combination_empty_result_message(self, test_database, monkeypatch):
        """DataManagerでの空結果メッセージテスト"""
        # DataManagerのDBを差し替え
        def mock_init(self):
            self.db = test_database
        
        monkeypatch.setattr(DataManager, '__init__', mock_init)
        
        data_manager = DataManager()
        
        # 結果が空になるフィルタ組み合わせ
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)
        author = 'nonexistent_user'
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            start_date=start_date,
            end_date=end_date,
            author=author
        )
        
        assert len(result) == 0
        assert error is not None
        assert "指定された条件" in error
        assert "nonexistent_user" in error
        assert "に一致するプルリクエストが見つかりませんでした" in error

    def test_data_manager_filter_validation_error(self, test_database, monkeypatch):
        """DataManagerでのフィルタ検証エラーテスト"""
        # DataManagerのDBを差し替え
        def mock_init(self):
            self.db = test_database
        
        monkeypatch.setattr(DataManager, '__init__', mock_init)
        
        data_manager = DataManager()
        
        # 無効な日付範囲
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)
        
        result, error = data_manager.get_pull_requests_with_lead_time_data(
            repository_id=1,
            start_date=start_date,
            end_date=end_date
        )
        
        assert len(result) == 0
        assert error is not None
        assert "開始日は終了日より前の日付を指定してください" in error