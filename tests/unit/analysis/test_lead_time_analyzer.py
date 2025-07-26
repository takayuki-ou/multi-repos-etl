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
    
    def test_group_by_period_weekly(self):
        """Test grouping PRs by weekly periods."""
        # Create test data spanning multiple weeks
        lead_time_data = [
            {
                'pr_id': 1,
                'pr_number': 101,
                'created_at': datetime(2024, 1, 1),  # Monday
                'lead_time_hours': 10.0
            },
            {
                'pr_id': 2,
                'pr_number': 102,
                'created_at': datetime(2024, 1, 3),  # Wednesday same week
                'lead_time_hours': 15.0
            },
            {
                'pr_id': 3,
                'pr_number': 103,
                'created_at': datetime(2024, 1, 8),  # Monday next week
                'lead_time_hours': 20.0
            }
        ]
        
        result = self.analyzer.group_by_period(lead_time_data, 'weekly')
        
        # Should have 2 groups (2 different weeks)
        assert len(result) == 2
        
        # Check that PRs are grouped correctly
        week_keys = list(result.keys())
        assert len(result[week_keys[0]]) == 2  # First week has 2 PRs
        assert len(result[week_keys[1]]) == 1  # Second week has 1 PR
    
    def test_group_by_period_monthly(self):
        """Test grouping PRs by monthly periods."""
        lead_time_data = [
            {
                'pr_id': 1,
                'pr_number': 101,
                'created_at': datetime(2024, 1, 15),
                'lead_time_hours': 10.0
            },
            {
                'pr_id': 2,
                'pr_number': 102,
                'created_at': datetime(2024, 1, 25),
                'lead_time_hours': 15.0
            },
            {
                'pr_id': 3,
                'pr_number': 103,
                'created_at': datetime(2024, 2, 5),
                'lead_time_hours': 20.0
            }
        ]
        
        result = self.analyzer.group_by_period(lead_time_data, 'monthly')
        
        # Should have 2 groups (January and February)
        assert len(result) == 2
        assert '2024-01' in result
        assert '2024-02' in result
        assert len(result['2024-01']) == 2
        assert len(result['2024-02']) == 1
    
    def test_group_by_period_empty_data(self):
        """Test grouping with empty data."""
        result = self.analyzer.group_by_period([], 'weekly')
        assert result == {}
    
    def test_group_by_period_invalid_period(self):
        """Test grouping with invalid period type."""
        lead_time_data = [
            {
                'pr_id': 1,
                'pr_number': 101,
                'created_at': datetime(2024, 1, 1),
                'lead_time_hours': 10.0
            }
        ]
        
        # Should default to weekly for invalid period
        result = self.analyzer.group_by_period(lead_time_data, 'invalid')
        assert len(result) == 1  # Should still group the data
    
    def test_get_period_key_weekly(self):
        """Test weekly period key generation."""
        # Test various days of the week
        monday = datetime(2024, 1, 1)  # Monday
        wednesday = datetime(2024, 1, 3)  # Wednesday same week
        sunday = datetime(2024, 1, 7)  # Sunday same week
        
        key1 = self.analyzer._get_period_key(monday, 'weekly')
        key2 = self.analyzer._get_period_key(wednesday, 'weekly')
        key3 = self.analyzer._get_period_key(sunday, 'weekly')
        
        # All should have the same week key
        assert key1 == key2 == key3
        assert key1.startswith('2024-W')
    
    def test_get_period_key_monthly(self):
        """Test monthly period key generation."""
        date1 = datetime(2024, 1, 1)
        date2 = datetime(2024, 1, 31)
        date3 = datetime(2024, 2, 1)
        
        key1 = self.analyzer._get_period_key(date1, 'monthly')
        key2 = self.analyzer._get_period_key(date2, 'monthly')
        key3 = self.analyzer._get_period_key(date3, 'monthly')
        
        assert key1 == key2 == '2024-01'
        assert key3 == '2024-02'
    
    def test_calculate_period_statistics(self):
        """Test calculation of statistics for grouped periods."""
        grouped_data = {
            '2024-01': [
                {'pr_id': 1, 'lead_time_hours': 10.0, 'created_at': datetime(2024, 1, 1)},
                {'pr_id': 2, 'lead_time_hours': 20.0, 'created_at': datetime(2024, 1, 2)}
            ],
            '2024-02': [
                {'pr_id': 3, 'lead_time_hours': 30.0, 'created_at': datetime(2024, 2, 1)}
            ]
        }
        
        result = self.analyzer.calculate_period_statistics(grouped_data)
        
        assert len(result) == 2
        
        # Check January statistics
        jan_stats = result['2024-01']
        assert jan_stats['count'] == 2
        assert jan_stats['average_lead_time_hours'] == 15.0  # (10 + 20) / 2
        assert jan_stats['average_lead_time_days'] == pytest.approx(0.625, rel=1e-2)  # 15/24
        assert jan_stats['total_lead_time_hours'] == 30.0
        
        # Check February statistics
        feb_stats = result['2024-02']
        assert feb_stats['count'] == 1
        assert feb_stats['average_lead_time_hours'] == 30.0
        assert feb_stats['average_lead_time_days'] == 1.25  # 30/24
    
    def test_calculate_period_statistics_empty_period(self):
        """Test statistics calculation with empty periods."""
        grouped_data = {
            '2024-01': [],
            '2024-02': [
                {'pr_id': 1, 'lead_time_hours': 10.0, 'created_at': datetime(2024, 2, 1)}
            ]
        }
        
        result = self.analyzer.calculate_period_statistics(grouped_data)
        
        # Empty period should have zero statistics
        jan_stats = result['2024-01']
        assert jan_stats['count'] == 0
        assert jan_stats['average_lead_time_hours'] == 0.0
        assert jan_stats['total_lead_time_hours'] == 0.0
        
        # Non-empty period should have normal statistics
        feb_stats = result['2024-02']
        assert feb_stats['count'] == 1
        assert feb_stats['average_lead_time_hours'] == 10.0
    
    def test_get_trend_data(self):
        """Test comprehensive trend data generation."""
        lead_time_data = [
            {
                'pr_id': 1,
                'pr_number': 101,
                'created_at': datetime(2024, 1, 1),
                'lead_time_hours': 10.0
            },
            {
                'pr_id': 2,
                'pr_number': 102,
                'created_at': datetime(2024, 1, 3),
                'lead_time_hours': 20.0
            },
            {
                'pr_id': 3,
                'pr_number': 103,
                'created_at': datetime(2024, 1, 8),
                'lead_time_hours': 30.0
            }
        ]
        
        result = self.analyzer.get_trend_data(lead_time_data, 'weekly')
        
        # Check structure
        assert 'grouped_data' in result
        assert 'period_statistics' in result
        assert 'period_type' in result
        assert 'total_periods' in result
        assert 'total_prs' in result
        
        # Check values
        assert result['period_type'] == 'weekly'
        assert result['total_prs'] == 3
        assert result['total_periods'] >= 1  # At least one period
        
        # Check that statistics are calculated
        assert len(result['period_statistics']) == len(result['grouped_data'])
    
    def test_get_trend_data_empty(self):
        """Test trend data generation with empty input."""
        result = self.analyzer.get_trend_data([], 'weekly')
        
        assert result['grouped_data'] == {}
        assert result['period_statistics'] == {}
        assert result['total_periods'] == 0
        assert result['total_prs'] == 0
    
    def test_calculate_trend_statistics(self):
        """Test calculate_trend_statistics with multiple periods."""
        # Create grouped data for multiple periods
        grouped_data = {
            '2024-01': [
                {'lead_time_hours': 24.0, 'created_at': datetime(2024, 1, 15)},
                {'lead_time_hours': 48.0, 'created_at': datetime(2024, 1, 20)}
            ],
            '2024-02': [
                {'lead_time_hours': 36.0, 'created_at': datetime(2024, 2, 10)},
                {'lead_time_hours': 60.0, 'created_at': datetime(2024, 2, 25)}
            ],
            '2024-03': [
                {'lead_time_hours': 30.0, 'created_at': datetime(2024, 3, 5)}
            ]
        }
        
        result = self.analyzer.calculate_trend_statistics(grouped_data)
        
        # Check that all periods are present
        assert '2024-01' in result
        assert '2024-02' in result
        assert '2024-03' in result
        
        # Check first period (no change rate)
        period1 = result['2024-01']
        assert period1['average'] == 36.0  # (24 + 48) / 2
        assert period1['count'] == 2
        assert period1['change_rate'] == 0.0
        assert period1['trend_direction'] == 'stable'
        
        # Check second period (change rate calculation)
        period2 = result['2024-02']
        assert period2['average'] == 48.0  # (36 + 60) / 2
        assert period2['count'] == 2
        expected_change = ((48.0 - 36.0) / 36.0) * 100  # 33.33%
        assert abs(period2['change_rate'] - expected_change) < 0.01
        assert period2['trend_direction'] == 'worsening'
        
        # Check third period
        period3 = result['2024-03']
        assert period3['average'] == 30.0
        assert period3['count'] == 1
        expected_change = ((30.0 - 48.0) / 48.0) * 100  # -37.5%
        assert abs(period3['change_rate'] - expected_change) < 0.01
        assert period3['trend_direction'] == 'improving'
    
    def test_calculate_trend_statistics_empty_data(self):
        """Test calculate_trend_statistics with empty data."""
        result = self.analyzer.calculate_trend_statistics({})
        assert result == {}
    
    def test_determine_trend_direction(self):
        """Test _determine_trend_direction method."""
        # Test improving trend (decrease in lead time)
        assert self.analyzer._determine_trend_direction(-10.0) == 'improving'
        assert self.analyzer._determine_trend_direction(-5.1) == 'improving'
        
        # Test worsening trend (increase in lead time)
        assert self.analyzer._determine_trend_direction(10.0) == 'worsening'
        assert self.analyzer._determine_trend_direction(5.1) == 'worsening'
        
        # Test stable trend
        assert self.analyzer._determine_trend_direction(0.0) == 'stable'
        assert self.analyzer._determine_trend_direction(2.0) == 'stable'
        assert self.analyzer._determine_trend_direction(-3.0) == 'stable'
        assert self.analyzer._determine_trend_direction(5.0) == 'stable'
        assert self.analyzer._determine_trend_direction(-5.0) == 'stable'
    
    def test_calculate_moving_averages(self):
        """Test calculate_moving_averages method."""
        trend_data = {
            '2024-01': {'average': 20.0},
            '2024-02': {'average': 30.0},
            '2024-03': {'average': 40.0},
            '2024-04': {'average': 50.0},
            '2024-05': {'average': 60.0}
        }
        
        result = self.analyzer.calculate_moving_averages(trend_data, [3])
        
        # First two periods should have None for 3-period moving average
        assert result['2024-01']['moving_avg_3'] is None
        assert result['2024-02']['moving_avg_3'] is None
        
        # Third period should have moving average of first 3 periods
        assert result['2024-03']['moving_avg_3'] == 30.0  # (20 + 30 + 40) / 3
        assert result['2024-04']['moving_avg_3'] == 40.0  # (30 + 40 + 50) / 3
        assert result['2024-05']['moving_avg_3'] == 50.0  # (40 + 50 + 60) / 3
    
    def test_get_multi_repository_trend_data(self):
        """Test get_multi_repository_trend_data method."""
        # Create sample data for multiple repositories
        repo1_data = [
            {
                'lead_time_hours': 24.0,
                'created_at': datetime(2024, 1, 15),
                'pr_number': 1,
                'repository_id': 1
            },
            {
                'lead_time_hours': 48.0,
                'created_at': datetime(2024, 2, 10),
                'pr_number': 2,
                'repository_id': 1
            }
        ]
        
        repo2_data = [
            {
                'lead_time_hours': 36.0,
                'created_at': datetime(2024, 1, 20),
                'pr_number': 3,
                'repository_id': 2
            }
        ]
        
        repository_data = {1: repo1_data, 2: repo2_data}
        
        result = self.analyzer.get_multi_repository_trend_data(repository_data, 'monthly')
        
        # Check structure
        assert 'combined_trend' in result
        assert 'individual_trends' in result
        assert 'repository_summary' in result
        assert result['period_type'] == 'monthly'
        
        # Check individual trends
        assert 1 in result['individual_trends']
        assert 2 in result['individual_trends']
        
        # Check repository summary
        assert 1 in result['repository_summary']
        assert 2 in result['repository_summary']
        assert result['repository_summary'][1]['total_prs'] == 2
        assert result['repository_summary'][2]['total_prs'] == 1
        
        # Check combined trend
        assert 'trend_data' in result['combined_trend']
        assert result['combined_trend']['total_prs'] == 3
        assert result['combined_trend']['total_repositories'] == 2
    
    def test_handle_empty_periods(self):
        """Test handle_empty_periods method."""
        trend_statistics = {
            '2024-01': {'average': 30.0, 'count': 2},
            '2024-03': {'average': 40.0, 'count': 1}  # Missing 2024-02
        }
        
        result = self.analyzer.handle_empty_periods(trend_statistics, 'monthly', fill_gaps=True)
        
        # Should have all three periods
        assert '2024-01' in result
        assert '2024-02' in result
        assert '2024-03' in result
        
        # Check filled period
        assert result['2024-02']['average'] == 0.0
        assert result['2024-02']['count'] == 0
        assert result['2024-02']['trend_direction'] == 'no_data'
        assert result['2024-02']['is_empty_period'] is True
        
        # Check that original data is preserved
        assert result['2024-01']['average'] == 30.0
        assert result['2024-03']['average'] == 40.0
    
    def test_handle_empty_periods_no_fill(self):
        """Test handle_empty_periods with fill_gaps=False."""
        trend_statistics = {
            '2024-01': {'average': 30.0, 'count': 2},
            '2024-03': {'average': 40.0, 'count': 1}
        }
        
        result = self.analyzer.handle_empty_periods(trend_statistics, 'monthly', fill_gaps=False)
        
        # Should only have original periods
        assert '2024-01' in result
        assert '2024-02' not in result
        assert '2024-03' in result
        
        # Original data should be preserved
        assert result['2024-01']['average'] == 30.0
        assert result['2024-03']['average'] == 40.0
    
    def test_parse_weekly_period(self):
        """Test _parse_weekly_period method."""
        year, week = self.analyzer._parse_weekly_period('2024-W15')
        assert year == 2024
        assert week == 15
        
        # Test invalid format
        with pytest.raises(ValueError):
            self.analyzer._parse_weekly_period('invalid-format')
    
    def test_generate_period_range_monthly(self):
        """Test _generate_period_range for monthly periods."""
        periods = self.analyzer._generate_period_range('2024-01', '2024-03', 'monthly')
        expected = ['2024-01', '2024-02', '2024-03']
        assert periods == expected
    
    def test_generate_period_range_weekly(self):
        """Test _generate_period_range for weekly periods."""
        periods = self.analyzer._generate_period_range('2024-W01', '2024-W03', 'weekly')
        expected = ['2024-W01', '2024-W02', '2024-W03']
        assert periods == expected