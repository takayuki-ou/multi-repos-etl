#!/usr/bin/env python3
"""
Demonstration script for LeadTimeAnalyzer.
Shows how to use the analyzer with real data from the database.
"""
import logging
from src.analysis.lead_time_analyzer import LeadTimeAnalyzer
from src.gui.data_manager import DataManager

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Demonstrate LeadTimeAnalyzer functionality."""
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
        
        # Process each repository
        for repo in repos[:2]:  # Limit to first 2 repositories for demo
            repo_name = f"{repo['owner_login']}/{repo['name']}"
            logger.info(f"\n--- Analyzing repository: {repo_name} ---")
            
            # Get pull requests
            prs, pr_error = data_manager.get_pull_requests(repo['id'])
            
            if pr_error:
                logger.error(f"Error fetching PRs for {repo_name}: {pr_error}")
                continue
            
            if not prs:
                logger.info(f"No pull requests found for {repo_name}")
                continue
            
            logger.info(f"Found {len(prs)} pull requests")
            
            # Calculate lead times
            lead_time_data = analyzer.calculate_lead_times(prs)
            
            if not lead_time_data:
                logger.info("No valid lead time data calculated")
                continue
            
            logger.info(f"Successfully calculated lead times for {len(lead_time_data)} PRs")
            
            # Show some statistics
            lead_times = analyzer.get_lead_times_only(lead_time_data)
            
            if lead_times:
                avg_hours = sum(lead_times) / len(lead_times)
                min_hours = min(lead_times)
                max_hours = max(lead_times)
                
                logger.info(f"Lead Time Statistics:")
                logger.info(f"  Average: {analyzer.format_lead_time_human_readable(avg_hours)}")
                logger.info(f"  Minimum: {analyzer.format_lead_time_human_readable(min_hours)}")
                logger.info(f"  Maximum: {analyzer.format_lead_time_human_readable(max_hours)}")
            
            # Show details for first few PRs
            logger.info(f"\nFirst {min(3, len(lead_time_data))} PRs:")
            for i, pr_data in enumerate(lead_time_data[:3]):
                logger.info(f"  {i+1}. PR #{pr_data['pr_number']}: {pr_data['title'][:50]}...")
                logger.info(f"     Author: {pr_data['author']}")
                logger.info(f"     Lead Time: {analyzer.format_lead_time_human_readable(pr_data['lead_time_hours'])}")
                logger.info(f"     Status: {pr_data['end_type']} ({pr_data['state']})")
        
        logger.info("\n--- Demo completed successfully ---")
        
    except Exception as e:
        logger.error(f"Error during demo: {e}", exc_info=True)


if __name__ == "__main__":
    main()