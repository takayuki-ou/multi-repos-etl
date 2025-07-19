#!/usr/bin/env python3
"""
Demo script for period grouping functionality in LeadTimeAnalyzer.
This script demonstrates the new period-based grouping and statistics calculation features.
"""
import logging
from datetime import datetime
from src.analysis.lead_time_analyzer import LeadTimeAnalyzer
from src.gui.data_manager import DataManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Demonstrate period grouping functionality."""
    try:
        # Initialize components
        logger.info("Initializing DataManager and LeadTimeAnalyzer...")
        data_manager = DataManager()
        analyzer = LeadTimeAnalyzer(data_manager)
        
        # Get repositories
        logger.info("Fetching repositories...")
        repos, error = data_manager.get_repositories()
        
        if error:
            logger.error(f"Error fetching repositories: {error}")
            return
        
        if not repos:
            logger.warning("No repositories found in database")
            return
        
        logger.info(f"Found {len(repos)} repositories")
        
        # Process first repository
        repo = repos[0]
        repo_id = repo['id']
        repo_name = repo.get('name', 'Unknown')
        
        logger.info(f"Processing repository: {repo_name} (ID: {repo_id})")
        
        # Get pull requests
        logger.info("Fetching pull requests...")
        prs, pr_error = data_manager.get_pull_requests(repo_id)
        
        if pr_error:
            logger.error(f"Error fetching pull requests: {pr_error}")
            return
        
        if not prs:
            logger.warning("No pull requests found")
            return
        
        logger.info(f"Found {len(prs)} pull requests")
        
        # Calculate lead times
        logger.info("Calculating lead times...")
        lead_time_data = analyzer.calculate_lead_times(prs)
        
        if not lead_time_data:
            logger.warning("No valid lead time data calculated")
            return
        
        logger.info(f"Calculated lead times for {len(lead_time_data)} PRs")
        
        # Demonstrate weekly grouping
        print("\n" + "="*60)
        print("WEEKLY PERIOD GROUPING ANALYSIS")
        print("="*60)
        
        weekly_trend = analyzer.get_trend_data(lead_time_data, 'weekly')
        
        print(f"Total PRs analyzed: {weekly_trend['total_prs']}")
        print(f"Total weekly periods: {weekly_trend['total_periods']}")
        print()
        
        # Display weekly statistics
        weekly_stats = weekly_trend['period_statistics']
        sorted_weeks = sorted(weekly_stats.keys())
        
        print("Weekly Statistics:")
        print("-" * 80)
        print(f"{'Week':<12} {'Count':<6} {'Avg Hours':<10} {'Avg Days':<10} {'Total Hours':<12}")
        print("-" * 80)
        
        for week in sorted_weeks:
            stats = weekly_stats[week]
            print(f"{week:<12} {stats['count']:<6} {stats['average_lead_time_hours']:<10.1f} "
                  f"{stats['average_lead_time_days']:<10.2f} {stats['total_lead_time_hours']:<12.1f}")
        
        # Demonstrate monthly grouping
        print("\n" + "="*60)
        print("MONTHLY PERIOD GROUPING ANALYSIS")
        print("="*60)
        
        monthly_trend = analyzer.get_trend_data(lead_time_data, 'monthly')
        
        print(f"Total PRs analyzed: {monthly_trend['total_prs']}")
        print(f"Total monthly periods: {monthly_trend['total_periods']}")
        print()
        
        # Display monthly statistics
        monthly_stats = monthly_trend['period_statistics']
        sorted_months = sorted(monthly_stats.keys())
        
        print("Monthly Statistics:")
        print("-" * 80)
        print(f"{'Month':<10} {'Count':<6} {'Avg Hours':<10} {'Avg Days':<10} {'Total Hours':<12}")
        print("-" * 80)
        
        for month in sorted_months:
            stats = monthly_stats[month]
            print(f"{month:<10} {stats['count']:<6} {stats['average_lead_time_hours']:<10.1f} "
                  f"{stats['average_lead_time_days']:<10.2f} {stats['total_lead_time_hours']:<12.1f}")
        
        # Show some sample PRs from different periods
        print("\n" + "="*60)
        print("SAMPLE PRs BY PERIOD")
        print("="*60)
        
        # Show first 3 PRs from the first weekly period
        if weekly_trend['grouped_data']:
            first_week = sorted_weeks[0]
            first_week_prs = weekly_trend['grouped_data'][first_week][:3]
            
            print(f"\nSample PRs from week {first_week}:")
            print("-" * 60)
            
            for pr in first_week_prs:
                readable_time = analyzer.format_lead_time_human_readable(pr['lead_time_hours'])
                print(f"PR #{pr['pr_number']}: {pr['title'][:40]}...")
                print(f"  Author: {pr['author']}")
                print(f"  Lead time: {readable_time}")
                print(f"  Created: {pr['created_at'].strftime('%Y-%m-%d %H:%M')}")
                print()
        
        print("="*60)
        print("PERIOD GROUPING DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error in demo: {e}")
        raise


if __name__ == "__main__":
    main()