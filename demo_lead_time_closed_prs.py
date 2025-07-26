#!/usr/bin/env python3
"""
リードタイム分析でclosedなPRのみを対象とするデモスクリプト
"""
import logging
from datetime import datetime
from src.gui.data_manager import DataManager

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def demo_lead_time_closed_prs():
    """closedなPRのみを対象としたリードタイム分析のデモ"""
    print("=== リードタイム分析（closedなPRのみ）デモ ===\n")
    
    try:
        # DataManagerを初期化
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
        
        # 1. 全PRを取得
        print("1. 全PRを取得:")
        all_prs, error = data_manager.get_pull_requests_with_lead_time_data(repo_id)
        if error:
            print(f"   エラー: {error}")
            return
        
        print(f"   総PR数: {len(all_prs)}件")
        
        # ステータス別の内訳を表示
        status_counts = {}
        for pr in all_prs:
            status = pr.get('state', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("   ステータス別内訳:")
        for status, count in sorted(status_counts.items()):
            print(f"     {status}: {count}件")
        print()
        
        # 2. closedなPRのみを取得（リードタイム分析用）
        print("2. closedなPRのみを取得（リードタイム分析用）:")
        closed_prs, error = data_manager.get_pull_requests_with_lead_time_data(
            repo_id, status='closed'
        )
        if error:
            print(f"   エラー: {error}")
            return
        
        print(f"   closedなPR数: {len(closed_prs)}件")
        
        if closed_prs:
            print("   最新のclosedなPR（最初の3件）:")
            for i, pr in enumerate(closed_prs[:3], 1):
                created_at = pr.get('created_at_dt')
                closed_at = pr.get('closed_at_dt')
                
                if created_at and closed_at:
                    lead_time = closed_at - created_at
                    lead_time_hours = lead_time.total_seconds() / 3600
                    print(f"     {i}. PR#{pr['number']}: {pr['title']}")
                    print(f"        作成: {created_at.strftime('%Y-%m-%d %H:%M')}")
                    print(f"        クローズ: {closed_at.strftime('%Y-%m-%d %H:%M')}")
                    print(f"        リードタイム: {lead_time_hours:.1f}時間 ({lead_time.days}日)")
                else:
                    print(f"     {i}. PR#{pr['number']}: {pr['title']} (日時データ不完全)")
        print()
        
        # 3. 特定期間のclosedなPRを取得
        print("3. 特定期間のclosedなPRを取得（2024年以降）:")
        start_date = datetime(2024, 1, 1)
        recent_closed_prs, error = data_manager.get_pull_requests_with_lead_time_data(
            repo_id, 
            start_date=start_date,
            status='closed'
        )
        if error:
            print(f"   エラー: {error}")
        else:
            print(f"   2024年以降のclosedなPR数: {len(recent_closed_prs)}件")
            
            if recent_closed_prs:
                # 平均リードタイムを計算
                total_lead_time_hours = 0
                valid_prs = 0
                
                for pr in recent_closed_prs:
                    created_at = pr.get('created_at_dt')
                    closed_at = pr.get('closed_at_dt')
                    
                    if created_at and closed_at:
                        lead_time = closed_at - created_at
                        total_lead_time_hours += lead_time.total_seconds() / 3600
                        valid_prs += 1
                
                if valid_prs > 0:
                    avg_lead_time_hours = total_lead_time_hours / valid_prs
                    print(f"   平均リードタイム: {avg_lead_time_hours:.1f}時間 ({avg_lead_time_hours/24:.1f}日)")
        print()
        
        # 4. リードタイム分析に適したPRの条件説明
        print("4. リードタイム分析に適したPRの条件:")
        print("   - ステータス: 'closed' (完了したPRのみ)")
        print("   - created_at と closed_at の両方が存在")
        print("   - リードタイム = closed_at - created_at")
        print("   - openなPRは分析対象外（まだ完了していないため）")
        print("   - GitHubの仕様上、PRステータスはopenとclosedの2択")
        
        print("\n=== デモ完了 ===")
        
    except Exception as e:
        logger.error(f"デモ実行中にエラーが発生しました: {e}", exc_info=True)
        print(f"エラー: {e}")


if __name__ == '__main__':
    demo_lead_time_closed_prs()