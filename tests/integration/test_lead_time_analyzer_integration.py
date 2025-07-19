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