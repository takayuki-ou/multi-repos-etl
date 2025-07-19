#!/usr/bin/env python3
"""
Demo script for trend statistics calculation functionality.
Tests the new trend analysis features including change rates, trend direction, 
and multi-repository support.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analysis.lead_time_analyzer import LeadTimeAnalyzer
from gui.data_manager import DataManager


def create_sample_lead_time_data() -> List[Dict[str, Any]]:
    """Create sample lead time data for testing trend statistics."""
    base_date = datetime(2024, 1, 1)
    sample_data = []
    
    # Create data for multiple periods with varying lead times
    periods = [
        # January - high lead times
        {'month': 1, 'lead_times': [48, 72, 96, 60, 84], 'trend': 'high'},
        # February - improving lead times
        {'month': 2, 'lead_times': [36, 48, 60, 42, 54], 'trend': 'improving'},
        # March - further improvement
        {'month': 3, 'lead_times': [24, 36, 48, 30, 42], 'trend': 'better'},
        # April - stable
        {'month': 4, 'lead_times': [30, 36, 42, 33, 39], 'trend': 'stable'},
        # May - worsening
        {'month': 5, 'lead_times': [48, 60, 72, 54, 66], 'trend': 'worse'},
    ]
    
    pr_id = 1
    for period in periods:
        for i, lead_time in enumerate(period['lead_times']):
            # Create PR data for different days in the month
            created_date = base_date.replace(month=period['month'], day=5 + i * 5)
            
            sample_data.append({
                'pr_id': pr_id,
                'pr_number': pr_id,
                'title': f'PR {pr_id} - {period["trend"]} period',
                'author': f'developer{(pr_id % 3) + 1}',
                'repository_id': 1,
                'created_at': created_date,
                'end_time': created_date + timedelta(hours=lead_time),
                'end_type': 'merged',
                'lead_time_hours': lead_time,
                'lead_time_days': lead_time / 24,
                'state': 'closed',
                'url': f'https://github.com/test/repo/pull/{pr_id}'
            })
            pr_id += 1
    
    return sample_data


def create_multi_repo_sample_data() -> Dict[int, List[Dict[str, Any]]]:
    """Create sample data for multiple repositories."""
    base_date = datetime(2024, 1, 1)
    
    # Repository 1: Frontend repo with generally faster reviews
    repo1_data = []
    for month in range(1, 4):
        for day in [5, 15, 25]:
            created_date = base_date.replace(month=month, day=day)
            lead_time = 24 + (month * 6)  # Gradually increasing
            
            repo1_data.append({
                'pr_id': f'repo1_{month}_{day}',
                'pr_number': len(repo1_data) + 1,
                'title': f'Frontend PR {len(repo1_data) + 1}',
                'author': 'frontend_dev',
                'repository_id': 1,
                'created_at': created_date,
                'end_time': created_date + timedelta(hours=lead_time),
                'end_type': 'merged',
                'lead_time_hours': lead_time,
                'lead_time_days': lead_time / 24,
                'state': 'closed',
                'url': f'https://github.com/test/frontend/pull/{len(repo1_data) + 1}'
            })
    
    # Repository 2: Backend repo with slower reviews
    repo2_data = []
    for month in range(1, 4):
        for day in [10, 20]:
            created_date = base_date.replace(month=month, day=day)
            lead_time = 48 + (month * 12)  # Higher base, more increase
            
            repo2_data.append({
                'pr_id': f'repo2_{month}_{day}',
                'pr_number': len(repo2_data) + 1,
                'title': f'Backend PR {len(repo2_data) + 1}',
                'author': 'backend_dev',
                'repository_id': 2,
                'created_at': created_date,
                'end_time': created_date + timedelta(hours=lead_time),
                'end_type': 'merged',
                'lead_time_hours': lead_time,
                'lead_time_days': lead_time / 24,
                'state': 'closed',
                'url': f'https://github.com/test/backend/pull/{len(repo2_data) + 1}'
            })
    
    return {1: repo1_data, 2: repo2_data}


def demo_trend_statistics():
    """Demonstrate trend statistics calculation."""
    print("=== Trend Statistics Calculation Demo ===\n")
    
    # Create mock data manager (we don't need actual DB for this demo)
    data_manager = None
    analyzer = LeadTimeAnalyzer(data_manager)
    
    # Create sample data
    sample_data = create_sample_lead_time_data()
    print(f"Created {len(sample_data)} sample PRs across 5 months")
    
    # Group data by period
    grouped_data = analyzer.group_by_period(sample_data, 'monthly')
    print(f"\nGrouped into {len(grouped_data)} monthly periods:")
    for period, prs in grouped_data.items():
        avg_lead_time = sum(pr['lead_time_hours'] for pr in prs) / len(prs)
        print(f"  {period}: {len(prs)} PRs, avg {avg_lead_time:.1f} hours")
    
    # Calculate trend statistics
    print("\n=== Trend Statistics ===")
    trend_stats = analyzer.calculate_trend_statistics(grouped_data)
    
    for period in sorted(trend_stats.keys()):
        stats = trend_stats[period]
        print(f"\n{period}:")
        print(f"  Average: {stats['average']:.1f} hours")
        print(f"  Count: {stats['count']} PRs")
        print(f"  Change Rate: {stats['change_rate']:+.1f}%")
        print(f"  Trend Direction: {stats['trend_direction']}")
        if stats.get('previous_period'):
            print(f"  Previous Period: {stats['previous_period']}")
    
    # Test moving averages
    print("\n=== Moving Averages ===")
    enhanced_stats = analyzer.calculate_moving_averages(trend_stats, [3])
    
    for period in sorted(enhanced_stats.keys()):
        stats = enhanced_stats[period]
        moving_avg = stats.get('moving_avg_3')
        if moving_avg is not None:
            print(f"{period}: Current {stats['average']:.1f}h, 3-period MA {moving_avg:.1f}h")
        else:
            print(f"{period}: Current {stats['average']:.1f}h, 3-period MA: N/A")


def demo_multi_repository_trends():
    """Demonstrate multi-repository trend analysis."""
    print("\n\n=== Multi-Repository Trend Analysis Demo ===\n")
    
    data_manager = None
    analyzer = LeadTimeAnalyzer(data_manager)
    
    # Create multi-repo sample data
    repo_data = create_multi_repo_sample_data()
    print("Created sample data for multiple repositories:")
    for repo_id, data in repo_data.items():
        avg_lead_time = sum(pr['lead_time_hours'] for pr in data) / len(data)
        print(f"  Repository {repo_id}: {len(data)} PRs, avg {avg_lead_time:.1f} hours")
    
    # Analyze multi-repository trends
    multi_trend = analyzer.get_multi_repository_trend_data(repo_data, 'monthly')
    
    print("\n=== Combined Trend (All Repositories) ===")
    combined = multi_trend['combined_trend']
    if 'trend_statistics' in combined:
        for period in sorted(combined['trend_statistics'].keys()):
            stats = combined['trend_statistics'][period]
            print(f"{period}: {stats['average']:.1f}h avg, {stats['count']} PRs, {stats['change_rate']:+.1f}% change")
    
    print("\n=== Individual Repository Trends ===")
    for repo_id, trend_data in multi_trend['individual_trends'].items():
        print(f"\nRepository {repo_id}:")
        if 'trend_statistics' in trend_data:
            for period in sorted(trend_data['trend_statistics'].keys()):
                stats = trend_data['trend_statistics'][period]
                print(f"  {period}: {stats['average']:.1f}h avg, {stats['count']} PRs, {stats['trend_direction']}")
    
    print("\n=== Repository Summary ===")
    for repo_id, summary in multi_trend['repository_summary'].items():
        print(f"Repository {repo_id}:")
        print(f"  Total PRs: {summary['total_prs']}")
        print(f"  Average Lead Time: {summary['average_lead_time']:.1f} hours")
        print(f"  Median Lead Time: {summary['median_lead_time']:.1f} hours")
        print(f"  Range: {summary['min_lead_time']:.1f} - {summary['max_lead_time']:.1f} hours")


def demo_empty_periods_handling():
    """Demonstrate handling of empty periods."""
    print("\n\n=== Empty Periods Handling Demo ===\n")
    
    data_manager = None
    analyzer = LeadTimeAnalyzer(data_manager)
    
    # Create trend statistics with gaps
    trend_stats_with_gaps = {
        '2024-01': {'average': 30.0, 'count': 5, 'change_rate': 0.0, 'trend_direction': 'stable'},
        '2024-03': {'average': 45.0, 'count': 3, 'change_rate': 50.0, 'trend_direction': 'worsening'},
        '2024-05': {'average': 25.0, 'count': 4, 'change_rate': -44.4, 'trend_direction': 'improving'}
    }
    
    print("Original trend statistics (with gaps):")
    for period, stats in sorted(trend_stats_with_gaps.items()):
        print(f"  {period}: {stats['average']:.1f}h avg, {stats['count']} PRs")
    
    # Fill gaps
    filled_stats = analyzer.handle_empty_periods(trend_stats_with_gaps, 'monthly', fill_gaps=True)
    
    print("\nAfter filling empty periods:")
    for period in sorted(filled_stats.keys()):
        stats = filled_stats[period]
        if stats.get('is_empty_period'):
            print(f"  {period}: [EMPTY] 0.0h avg, 0 PRs, trend: {stats['trend_direction']}")
        else:
            print(f"  {period}: {stats['average']:.1f}h avg, {stats['count']} PRs, trend: {stats['trend_direction']}")
    
    # Don't fill gaps
    no_fill_stats = analyzer.handle_empty_periods(trend_stats_with_gaps, 'monthly', fill_gaps=False)
    
    print("\nWithout filling gaps (original periods only):")
    for period in sorted(no_fill_stats.keys()):
        stats = no_fill_stats[period]
        print(f"  {period}: {stats['average']:.1f}h avg, {stats['count']} PRs")


def demo_trend_direction_logic():
    """Demonstrate trend direction determination logic."""
    print("\n\n=== Trend Direction Logic Demo ===\n")
    
    data_manager = None
    analyzer = LeadTimeAnalyzer(data_manager)
    
    test_cases = [
        (0.0, "No change"),
        (-10.0, "10% improvement (faster reviews)"),
        (15.0, "15% worsening (slower reviews)"),
        (-3.0, "3% improvement (within stable range)"),
        (4.0, "4% worsening (within stable range)"),
        (-5.0, "5% improvement (boundary case)"),
        (5.0, "5% worsening (boundary case)"),
        (-25.0, "25% improvement (significant)"),
        (30.0, "30% worsening (significant)")
    ]
    
    print("Change Rate → Trend Direction:")
    for change_rate, description in test_cases:
        direction = analyzer._determine_trend_direction(change_rate)
        print(f"  {change_rate:+6.1f}% ({description:30s}) → {direction}")


if __name__ == "__main__":
    try:
        demo_trend_statistics()
        demo_multi_repository_trends()
        demo_empty_periods_handling()
        demo_trend_direction_logic()
        
        print("\n=== Demo completed successfully! ===")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)