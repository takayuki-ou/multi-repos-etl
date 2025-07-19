#!/usr/bin/env python3
"""
DataManagerフィルタリング機能のデモスクリプト
"""
import logging
from datetime import datetime
from src.gui.data_manager import DataManager

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_filtering():
    """フィルタリング機能のデモ"""
    try:
        # DataManagerを初期化
        data_manager = DataManager()
        
        # リポジトリ一覧を取得
        repos, error = data_manager.get_repositories()
        if error:
            logger.error(f"リポジトリ取得エラー: {error}")
            return
        
        if not repos:
            logger.info("リポジトリが見つかりません")
            return
        
        # 最初のリポジトリを使用
        repo = repos[0]
        repo_id = repo['id']
        logger.info(f"テスト対象リポジトリ: {repo['owner_login']}/{repo['name']} (ID: {repo_id})")
        
        # 1. フィルタなしでPR取得
        logger.info("\n=== フィルタなしでPR取得 ===")
        prs, error = data_manager.get_pull_requests_with_lead_time_data(repo_id)
        if error:
            logger.error(f"PR取得エラー: {error}")
            return
        
        logger.info(f"総PR数: {len(prs)}")
        if prs:
            for pr in prs[:3]:  # 最初の3件を表示
                logger.info(f"  PR#{pr['number']}: {pr['title']} by {pr['user_login']} ({pr['created_at']})")
        
        # 2. 作成者一覧を取得
        logger.info("\n=== 作成者一覧取得 ===")
        authors, error = data_manager.get_authors_for_repository(repo_id)
        if error:
            logger.error(f"作成者取得エラー: {error}")
            return
        
        logger.info(f"作成者数: {len(authors)}")
        logger.info(f"作成者: {', '.join(authors[:5])}")  # 最初の5人を表示
        
        # 3. 日付範囲フィルタ
        if prs:
            logger.info("\n=== 日付範囲フィルタ ===")
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 12, 31)
            
            filtered_prs, error = data_manager.get_pull_requests_with_lead_time_data(
                repo_id, start_date=start_date, end_date=end_date
            )
            if error:
                logger.error(f"フィルタ済みPR取得エラー: {error}")
                return
            
            logger.info(f"2023年のPR数: {len(filtered_prs)}")
        
        # 4. 作成者フィルタ
        if authors:
            logger.info("\n=== 作成者フィルタ ===")
            target_author = authors[0]
            
            author_prs, error = data_manager.get_pull_requests_with_lead_time_data(
                repo_id, author=target_author
            )
            if error:
                logger.error(f"作成者フィルタPR取得エラー: {error}")
                return
            
            logger.info(f"{target_author}のPR数: {len(author_prs)}")
        
        # 5. 複合フィルタ
        if authors and prs:
            logger.info("\n=== 複合フィルタ（日付範囲 + 作成者） ===")
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 12, 31)
            target_author = authors[0]
            
            combined_prs, error = data_manager.get_pull_requests_with_lead_time_data(
                repo_id, 
                start_date=start_date, 
                end_date=end_date, 
                author=target_author
            )
            if error:
                logger.error(f"複合フィルタPR取得エラー: {error}")
                return
            
            logger.info(f"2023年の{target_author}のPR数: {len(combined_prs)}")
        
        logger.info("\n=== フィルタリング機能デモ完了 ===")
        
    except Exception as e:
        logger.error(f"デモ実行中にエラーが発生しました: {e}", exc_info=True)


if __name__ == '__main__':
    demo_filtering()