"""
Unit tests for LeadTimeAnalyzer class.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock
from src.analysis.lead_time_analyzer import LeadTimeAnalyzer


class TestLeadTimeAnalyzer:
    """Test cases for LeadTimeAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock()
        self.analyzer = LeadTimeAnalyzer(self.mock_data_manager)
    
    def test_init(self):
        """Test LeadTimeAnalyzer initialization."""
        assert self.analyzer.data_manager == self.mock_data_manager
    
    def test_calculate_lead_times_empty_list(self):
        """Test lead time calculation with empty PR list."""
        result = self.analyzer.calculate_lead_times([])
        assert result == []
    
    def test_calculate_lead_times_merged_pr(self):
        """Test lead time calculation for merged PR."""
        # Create test data for a merged PR
        created_time = "2024-01-01T10:00:00Z"
        merged_time = "2024-01-02T14:00:00Z"  # 28 hours later
        
        pr_data = {
            'id': 1,
            'number': 123,
            'title': 'Test PR',
            'user_login': 'testuser',
            'repository_id': 1,
            'created_at': created_time,
            'merged_at': merged_time,
            'closed_at': None,
            'state': 'closed',
            'url': 'https://github.com/test/repo/pull/123'
        }
        
        result = self.analyzer.calculate_lead_times([pr_data])
        
        assert len(result) == 1
        lead_time_info = result[0]
        
        assert lead_time_info['pr_id'] == 1
        assert lead_time_info['pr_number'] == 123
        assert lead_time_info['title'] == 'Test PR'
        assert lead_time_info['author'] == 'testuser'
        assert lead_time_info['end_type'] == 'merged'
        assert lead_time_info['lead_time_hours'] == 28.0
        assert lead_time_info['lead_time_days'] == pytest.approx(1.17, rel=1e-2)
    
    def test_calculate_lead_times_closed_pr(self):
        """Test lead time calculation for closed (not merged) PR."""
        created_time = "2024-01-01T10:00:00Z"
        closed_time = "2024-01-01T18:00:00Z"  # 8 hours later
        
        pr_data = {
            'id': 2,
            'number': 124,
            'title': 'Closed PR',
            'user_login': 'testuser2',
            'repository_id': 1,
            'created_at': created_time,
            'merged_at': None,
            'closed_at': closed_time,
            'state': 'closed',
            'url': 'https://github.com/test/repo/pull/124'
        }
        
        result = self.analyzer.calculate_lead_times([pr_data])
        
        assert len(result) == 1
        lead_time_info = result[0]
        
        assert lead_time_info['pr_number'] == 124
        assert lead_time_info['end_type'] == 'closed'
        assert lead_time_info['lead_time_hours'] == 8.0
        assert lead_time_info['lead_time_days'] == pytest.approx(0.33, rel=1e-2)
    
    def test_calculate_lead_times_open_pr(self):
        """Test lead time calculation for open PR (uses current time)."""
        created_time = "2024-01-01T10:00:00Z"
        
        pr_data = {
            'id': 3,
            'number': 125,
            'title': 'Open PR',
            'user_login': 'testuser3',
            'repository_id': 1,
            'created_at': created_time,
            'merged_at': None,
            'closed_at': None,
            'state': 'open',
            'url': 'https://github.com/test/repo/pull/125'
        }
        
        result = self.analyzer.calculate_lead_times([pr_data])
        
        assert len(result) == 1
        lead_time_info = result[0]
        
        assert lead_time_info['pr_number'] == 125
        assert lead_time_info['end_type'] == 'open'
        assert lead_time_info['lead_time_hours'] > 0  # Should be positive
    
    def test_calculate_lead_times_invalid_data(self):
        """Test lead time calculation with invalid PR data."""
        # PR missing required fields
        invalid_pr = {
            'title': 'Invalid PR',
            # Missing id, number, created_at, state
        }
        
        result = self.analyzer.calculate_lead_times([invalid_pr])
        assert result == []
    
    def test_calculate_lead_times_mixed_data(self):
        """Test lead time calculation with mix of valid and invalid data."""
        valid_pr = {
            'id': 1,
            'number': 123,
            'title': 'Valid PR',
            'user_login': 'testuser',
            'repository_id': 1,
            'created_at': "2024-01-01T10:00:00Z",
            'merged_at': "2024-01-01T18:00:00Z",
            'closed_at': None,
            'state': 'closed',
            'url': 'https://github.com/test/repo/pull/123'
        }
        
        invalid_pr = {
            'title': 'Invalid PR',
            # Missing required fields
        }
        
        result = self.analyzer.calculate_lead_times([valid_pr, invalid_pr])
        
        # Should only return the valid PR
        assert len(result) == 1
        assert result[0]['pr_number'] == 123
    
    def test_validate_pr_data_valid(self):
        """Test PR data validation with valid data."""
        valid_pr = {
            'id': 1,
            'number': 123,
            'created_at': '2024-01-01T10:00:00Z',
            'state': 'closed'
        }
        
        assert self.analyzer._validate_pr_data(valid_pr) is True
    
    def test_validate_pr_data_missing_fields(self):
        """Test PR data validation with missing required fields."""
        # Missing 'id'
        invalid_pr1 = {
            'number': 123,
            'created_at': '2024-01-01T10:00:00Z',
            'state': 'closed'
        }
        
        # Missing 'created_at'
        invalid_pr2 = {
            'id': 1,
            'number': 123,
            'state': 'closed'
        }
        
        # Empty 'created_at'
        invalid_pr3 = {
            'id': 1,
            'number': 123,
            'created_at': '   ',
            'state': 'closed'
        }
        
        assert self.analyzer._validate_pr_data(invalid_pr1) is False
        assert self.analyzer._validate_pr_data(invalid_pr2) is False
        assert self.analyzer._validate_pr_data(invalid_pr3) is False
    
    def test_format_lead_time_human_readable(self):
        """Test human-readable lead time formatting."""
        # Test minutes
        assert self.analyzer.format_lead_time_human_readable(0.5) == "30 minutes"
        
        # Test hours
        assert self.analyzer.format_lead_time_human_readable(2.5) == "2.5 hours"
        
        # Test days only
        assert self.analyzer.format_lead_time_human_readable(48.0) == "2 days"
        
        # Test days and hours
        assert self.analyzer.format_lead_time_human_readable(50.5) == "2 days, 2.5 hours"
        
        # Test invalid (negative)
        assert self.analyzer.format_lead_time_human_readable(-1.0) == "Invalid lead time"
    
    def test_get_lead_times_only(self):
        """Test extraction of lead time values only."""
        lead_time_data = [
            {'pr_id': 1, 'lead_time_hours': 10.5},
            {'pr_id': 2, 'lead_time_hours': 24.0},
            {'pr_id': 3, 'lead_time_hours': 5.25}
        ]
        
        result = self.analyzer.get_lead_times_only(lead_time_data)
        
        assert result == [10.5, 24.0, 5.25]
    
    def test_get_lead_times_only_empty(self):
        """Test extraction of lead time values from empty list."""
        result = self.analyzer.get_lead_times_only([])
        assert result == []
    
    def test_statistics_calculator_integration(self):
        """Test that LeadTimeAnalyzer properly delegates to StatisticsCalculator."""
        # Test that the statistics calculator is initialized
        assert self.analyzer.statistics_calculator is not None
        
        # Test basic statistics delegation
        lead_times = [10.0, 15.0, 20.0, 25.0, 30.0]
        result = self.analyzer.calculate_basic_statistics(lead_times)
        assert result['count'] == 5
        assert result['mean'] == 20.0
        
        # Test percentiles delegation
        percentiles = self.analyzer.calculate_percentiles(lead_times)
        assert 'p25' in percentiles
        assert 'p75' in percentiles
        assert 'iqr' in percentiles
        
        # Test outlier removal delegation
        outlier_data = [10, 12, 11, 13, 12, 11, 10, 13, 100]
        filtered = self.analyzer.remove_outliers(outlier_data, method='iqr')
        assert len(filtered) < len(outlier_data)
        
        # Test comprehensive statistics delegation
        comprehensive = self.analyzer.get_statistics_with_outlier_removal(outlier_data, 'iqr')
        assert 'original_stats' in comprehensive
        assert 'filtered_stats' in comprehensive