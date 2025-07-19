#!/usr/bin/env python3
"""
フィルタ条件組み合わせ処理のデモスクリプト
"""
import logging
from datetime import datetime
from src.gui.data_manager import DataManager

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_filter_combination():
    """フィルタ条件組み合わせ処理のデモ"""
    print("=== フィルタ条件組み合わせ処理デモ ===\n")
    
    try:
        # DataManagerの初期化
        data_manager = DataManager()
        
        # リポジトリ一覧を取得
        repos, error = data_manager.get_repositories()
        if error:
            print(f"エラー: {error}")
            return
        
        if not repos:
            print("リポジトリが見つかりません。")
            return
        
        # 最初のリポジトリを使用
        repo = repos[0]
        repo_id = repo['id']
        print(f"使用するリポジトリ: {repo['owner_login']}/{repo['name']} (ID: {repo_id})\n")
        
        # 1. フィルタなしでPRを取得
        print("1. フィルタなしでPRを取得:")
        prs, error = data_manager.get_pull_requests_with_lead_time_data(repo_id)
        if error:
            print(f"   エラー: {error}")
        else:
            print(f"   取得件数: {len(prs)}件")
        print()
        
        # 2. 日付範囲フィルタのみ
        print("2. 日付範囲フィルタのみ (2023年1月-3月):")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)
        prs, error = data_manager.get_pull_requests_with_lead_time_data(
            repo_id, start_date=start_date, end_date=end_date
        )
        if error:
            print(f"   エラー: {error}")
        else:
            print(f"   取得件数: {len(prs)}件")
            for pr in prs[:3]:  # 最初の3件を表示
                print(f"   - PR#{pr['number']}: {pr['title']} ({pr['user_login']})")
        print()
        
        # 3. 作成者フィルタのみ
        print("3. 作成者フィルタのみ:")
        # まず作成者一覧を取得
        authors, error = data_manager.get_authors_for_repository(repo_id)
        if error:
            print(f"   エラー: {error}")
        elif authors:
            author = authors[0]  # 最初の作成者を使用
            print(f"   フィルタ対象作成者: {author}")
            prs, error = data_manager.get_pull_requests_with_lead_time_data(
                repo_id, author=author
            )
            if error:
                print(f"   エラー: {error}")
            else:
                print(f"   取得件数: {len(prs)}件")
        else:
            print("   作成者が見つかりません")
        print()
        
        # 4. 複数フィルタの組み合わせ（ANDロジック）
        print("4. 複数フィルタの組み合わせ（ANDロジック）:")
        if authors:
            author = authors[0]
            print(f"   条件: 日付範囲 (2023年1月-3月) AND 作成者 ({author})")
            prs, error = data_manager.get_pull_requests_with_lead_time_data(
                repo_id, start_date=start_date, end_date=end_date, author=author
            )
            if error:
                print(f"   エラー: {error}")
            else:
                print(f"   取得件数: {len(prs)}件")
                for pr in prs:
                    print(f"   - PR#{pr['number']}: {pr['title']} ({pr['user_login']})")
        print()
        
        # 5. 存在しない条件でのフィルタ（空結果のハンドリング）
        print("5. 存在しない条件でのフィルタ（空結果のハンドリング）:")
        print("   条件: 存在しない作成者 'nonexistent_user'")
        prs, error = data_manager.get_pull_requests_with_lead_time_data(
            repo_id, author='nonexistent_user'
        )
        if error:
            print(f"   メッセージ: {error}")
        else:
            print(f"   取得件数: {len(prs)}件")
        print()
        
        # 6. 無効なフィルタ条件（検証エラー）
        print("6. 無効なフィルタ条件（検証エラー）:")
        print("   条件: 開始日 > 終了日")
        invalid_start = datetime(2023, 12, 31)
        invalid_end = datetime(2023, 1, 1)
        prs, error = data_manager.get_pull_requests_with_lead_time_data(
            repo_id, start_date=invalid_start, end_date=invalid_end
        )
        if error:
            print(f"   検証エラー: {error}")
        else:
            print(f"   取得件数: {len(prs)}件")
        print()
        
        # 7. フィルタ条件の検証テスト
        print("7. フィルタ条件の検証テスト:")
        
        # 有効な条件
        is_valid, error = data_manager.validate_filter_combination(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            author='valid_user'
        )
        print(f"   有効な条件: {is_valid}, エラー: {error}")
        
        # 無効な条件（空の作成者名）
        is_valid, error = data_manager.validate_filter_combination(author='   ')
        print(f"   空の作成者名: {is_valid}, エラー: {error}")
        
        # 無効な条件（長すぎる作成者名）
        long_author = 'a' * 101
        is_valid, error = data_manager.validate_filter_combination(author=long_author)
        print(f"   長すぎる作成者名: {is_valid}, エラー: {error}")
        
        print("\n=== デモ完了 ===")
        
    except Exception as e:
        logger.error(f"デモ実行中にエラーが発生しました: {e}", exc_info=True)
        print(f"エラー: {e}")


if __name__ == '__main__':
    demo_filter_combination()