"""
Integration tests for LeadTimeAnalyzer with DataManager.
"""
import pytest
import logging
from src.analysis.lead_time_analyzer import LeadTimeAnalyzer
from src.gui.data_manager import DataManager

logger = logging.getLogger(__name__)


class TestLeadTimeAnalyzerIntegration:
    """Integration tests for LeadTimeAnalyzer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        try:
            self.data_manager = DataManager()
            self.analyzer = LeadTimeAnalyzer(self.data_manager)
        except Exception as e:
            pytest.skip(f"Could not initialize DataManager: {e}")
    
    def test_analyzer_with_real_data(self):
        """Test analyzer with real data from database."""
        # Get repositories
        repos, error = self.data_manager.get_repositories()
        
        if error:
            pytest.skip(f"Could not get repositories: {error}")
        
        if not repos:
            pytest.skip("No repositories found in database")
        
        # Get pull requests for first repository
        repo_id = repos[0]['id']
        prs, pr_error = self.data_manager.get_pull_requests(repo_id)
        
        if pr_error:
            pytest.skip(f"Could not get pull requests: {pr_error}")
        
        if not prs:
            pytest.skip("No pull requests found")
        
        # Calculate lead times
        lead_time_data = self.analyzer.calculate_lead_times(prs)
        
        # Verify results
        assert isinstance(lead_time_data, list)
        
        if lead_time_data:
            # Check first result structure
            first_result = lead_time_data[0]
            required_fields = [
                'pr_id', 'pr_number', 'title', 'author', 'repository_id',
                'created_at', 'end_time', 'end_type', 'lead_time_hours',
                'lead_time_days', 'state', 'url'
            ]
            
            for field in required_fields:
                assert field in first_result, f"Missing field: {field}"
            
            # Verify lead time is positive
            assert first_result['lead_time_hours'] >= 0
            assert first_result['lead_time_days'] >= 0
            
            # Verify end_type is valid
            assert first_result['end_type'] in ['merged', 'closed', 'open']
            
            logger.info(f"Successfully processed {len(lead_time_data)} PRs with lead times")
            
            # Test human-readable formatting
            for item in lead_time_data[:3]:  # Test first 3 items
                readable = self.analyzer.format_lead_time_human_readable(item['lead_time_hours'])
                assert isinstance(readable, str)
                assert len(readable) > 0
                logger.info(f"PR #{item['pr_number']}: {readable}")
        
        else:
            logger.info("No valid lead time data calculated (possibly due to data quality issues)")
    
    def test_analyzer_error_handling(self):
        """Test analyzer error handling with malformed data."""
        # Test with malformed PR data
        malformed_prs = [
            {'id': 1, 'number': 123},  # Missing required fields
            {'created_at': 'invalid-date'},  # Invalid date format
            None,  # Null entry
        ]
        
        # Should not raise exception, should handle gracefully
        result = self.analyzer.calculate_lead_times(malformed_prs)
        
        # Should return empty list or filtered results
        assert isinstance(result, list)
        # All entries should be filtered out due to validation failures
        assert len(result) == 0
    
    def test_period_grouping_with_real_data(self):
        """Test period grouping functionality with real data."""
        # Get repositories
        repos, error = self.data_manager.get_repositories()
        
        if error:
            pytest.skip(f"Could not get repositories: {error}")
        
        if not repos:
            pytest.skip("No repositories found in database")
        
        # Get pull requests for first repository
        repo_id = repos[0]['id']
        prs, pr_error = self.data_manager.get_pull_requests(repo_id)
        
        if pr_error:
            pytest.skip(f"Could not get pull requests: {pr_error}")
        
        if not prs:
            pytest.skip("No pull requests found")
        
        # Calculate lead times
        lead_time_data = self.analyzer.calculate_lead_times(prs)
        
        if not lead_time_data:
            pytest.skip("No valid lead time data calculated")
        
        # Test weekly grouping
        weekly_groups = self.analyzer.group_by_period(lead_time_data, 'weekly')
        assert isinstance(weekly_groups, dict)
        
        if weekly_groups:
            logger.info(f"Weekly grouping created {len(weekly_groups)} groups")
            
            # Verify group structure
            for period_key, pr_list in weekly_groups.items():
                assert isinstance(period_key, str)
                assert isinstance(pr_list, list)
                assert len(pr_list) > 0
                
                # Verify period key format (should be YYYY-WXX)
                assert '-W' in period_key or period_key.startswith('2024-W')
                
                logger.info(f"Period {period_key}: {len(pr_list)} PRs")
        
        # Test monthly grouping
        monthly_groups = self.analyzer.group_by_period(lead_time_data, 'monthly')
        assert isinstance(monthly_groups, dict)
        
        if monthly_groups:
            logger.info(f"Monthly grouping created {len(monthly_groups)} groups")
            
            # Verify group structure
            for period_key, pr_list in monthly_groups.items():
                assert isinstance(period_key, str)
                assert isinstance(pr_list, list)
                assert len(pr_list) > 0
                
                # Verify period key format (should be YYYY-MM)
                assert len(period_key) == 7  # YYYY-MM format
                assert period_key[4] == '-'
                
                logger.info(f"Period {period_key}: {len(pr_list)} PRs")
    
    def test_period_statistics_with_real_data(self):
        """Test period statistics calculation with real data."""
        # Get repositories
        repos, error = self.data_manager.get_repositories()
        
        if error:
            pytest.skip(f"Could not get repositories: {error}")
        
        if not repos:
            pytest.skip("No repositories found in database")
        
        # Get pull requests for first repository
        repo_id = repos[0]['id']
        prs, pr_error = self.data_manager.get_pull_requests(repo_id)
        
        if pr_error:
            pytest.skip(f"Could not get pull requests: {pr_error}")
        
        if not prs:
            pytest.skip("No pull requests found")
        
        # Calculate lead times
        lead_time_data = self.analyzer.calculate_lead_times(prs)
        
        if not lead_time_data:
            pytest.skip("No valid lead time data calculated")
        
        # Group by period
        grouped_data = self.analyzer.group_by_period(lead_time_data, 'monthly')
        
        if not grouped_data:
            pytest.skip("No grouped data available")
        
        # Calculate period statistics
        period_stats = self.analyzer.calculate_period_statistics(grouped_data)
        
        assert isinstance(period_stats, dict)
        assert len(period_stats) == len(grouped_data)
        
        # Verify statistics structure
        for period_key, stats in period_stats.items():
            assert isinstance(stats, dict)
            
            required_fields = [
                'count', 'average_lead_time_hours', 'average_lead_time_days',
                'total_lead_time_hours', 'period_start', 'period_end'
            ]
            
            for field in required_fields:
                assert field in stats, f"Missing field {field} in period {period_key}"
            
            # Verify values are reasonable
            assert stats['count'] >= 0
            assert stats['average_lead_time_hours'] >= 0
            assert stats['average_lead_time_days'] >= 0
            assert stats['total_lead_time_hours'] >= 0
            
            logger.info(f"Period {period_key}: {stats['count']} PRs, "
                       f"avg {stats['average_lead_time_hours']:.1f}h")
    
    def test_trend_data_generation_with_real_data(self):
        """Test comprehensive trend data generation with real data."""
        # Get repositories
        repos, error = self.data_manager.get_repositories()
        
        if error:
            pytest.skip(f"Could not get repositories: {error}")
        
        if not repos:
            pytest.skip("No repositories found in database")
        
        # Get pull requests for first repository
        repo_id = repos[0]['id']
        prs, pr_error = self.data_manager.get_pull_requests(repo_id)
        
        if pr_error:
            pytest.skip(f"Could not get pull requests: {pr_error}")
        
        if not prs:
            pytest.skip("No pull requests found")
        
        # Calculate lead times
        lead_time_data = self.analyzer.calculate_lead_times(prs)
        
        if not lead_time_data:
            pytest.skip("No valid lead time data calculated")
        
        # Generate trend data
        trend_data = self.analyzer.get_trend_data(lead_time_data, 'weekly')
        
        # Verify structure
        required_fields = [
            'grouped_data', 'period_statistics', 'period_type',
            'total_periods', 'total_prs'
        ]
        
        for field in required_fields:
            assert field in trend_data, f"Missing field: {field}"
        
        # Verify values
        assert trend_data['period_type'] == 'weekly'
        assert trend_data['total_prs'] == len(lead_time_data)
        assert trend_data['total_periods'] >= 0
        
        # Verify consistency between grouped data and statistics
        assert len(trend_data['grouped_data']) == len(trend_data['period_statistics'])
        assert len(trend_data['grouped_data']) == trend_data['total_periods']
        
        logger.info(f"Trend data: {trend_data['total_periods']} periods, "
                   f"{trend_data['total_prs']} PRs total")
        
        # Test monthly trend data as well
        monthly_trend = self.analyzer.get_trend_data(lead_time_data, 'monthly')
        assert monthly_trend['period_type'] == 'monthly'
        assert monthly_trend['total_prs'] == len(lead_time_data)