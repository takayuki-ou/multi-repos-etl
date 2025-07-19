"""
Unit tests for StatisticsCalculator class.
"""
import pytest
import numpy as np
from src.analysis.statistics_calculator import StatisticsCalculator


class TestStatisticsCalculator:
    """Test cases for StatisticsCalculator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = StatisticsCalculator()
    
    def test_init(self):
        """Test StatisticsCalculator initialization."""
        assert self.calculator is not None
    
    def test_calculate_basic_statistics_normal_case(self):
        """Test basic statistics calculation with normal data."""
        values = [10.0, 15.0, 20.0, 25.0, 30.0]
        
        result = self.calculator.calculate_basic_statistics(values)
        
        assert result['count'] == 5
        assert result['mean'] == 20.0
        assert result['median'] == 20.0
        assert result['min'] == 10.0
        assert result['max'] == 30.0
        assert result['std_dev'] == pytest.approx(7.91, rel=1e-2)
    
    def test_calculate_basic_statistics_empty_data(self):
        """Test basic statistics calculation with empty data."""
        result = self.calculator.calculate_basic_statistics([])
        
        assert result['count'] == 0
        assert result['mean'] == 0.0
        assert result['median'] == 0.0
        assert result['min'] == 0.0
        assert result['max'] == 0.0
        assert result['std_dev'] == 0.0
    
    def test_calculate_basic_statistics_single_value(self):
        """Test basic statistics calculation with single value."""
        values = [15.5]
        
        result = self.calculator.calculate_basic_statistics(values)
        
        assert result['count'] == 1
        assert result['mean'] == 15.5
        assert result['median'] == 15.5
        assert result['min'] == 15.5
        assert result['max'] == 15.5
        assert result['std_dev'] == 0.0  # Single value has no deviation
    
    def test_calculate_basic_statistics_with_nan_values(self):
        """Test basic statistics calculation with NaN values."""
        values = [10.0, np.nan, 20.0, np.inf, 30.0]
        
        result = self.calculator.calculate_basic_statistics(values)
        
        # Should only process finite values: [10.0, 20.0, 30.0]
        assert result['count'] == 3
        assert result['mean'] == 20.0
        assert result['median'] == 20.0
        assert result['min'] == 10.0
        assert result['max'] == 30.0
    
    def test_calculate_percentiles_normal_case(self):
        """Test percentile calculation with normal data."""
        # Use a larger dataset for better percentile calculation
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        
        result = self.calculator.calculate_percentiles(values)
        
        # Use approximate assertions since percentile calculations can vary slightly
        assert result['p25'] == pytest.approx(5.75, rel=1e-2)  # 25th percentile
        assert result['p75'] == pytest.approx(15.25, rel=1e-2)  # 75th percentile
        assert result['p90'] == pytest.approx(18.1, rel=1e-2)  # 90th percentile
        assert result['p95'] == pytest.approx(19.05, rel=1e-2)  # 95th percentile
        assert result['iqr'] == pytest.approx(9.5, rel=1e-2)  # IQR = Q3 - Q1
    
    def test_calculate_percentiles_empty_data(self):
        """Test percentile calculation with empty data."""
        result = self.calculator.calculate_percentiles([])
        
        assert result['p25'] == 0.0
        assert result['p75'] == 0.0
        assert result['p90'] == 0.0
        assert result['p95'] == 0.0
        assert result['iqr'] == 0.0
    
    def test_calculate_percentiles_small_dataset(self):
        """Test percentile calculation with small dataset."""
        values = [10.0, 20.0, 30.0]
        
        result = self.calculator.calculate_percentiles(values)
        
        # Should still calculate percentiles
        assert result['p25'] == 15.0
        assert result['p75'] == 25.0
        assert result['iqr'] == 10.0
    
    def test_remove_outliers_iqr_method(self):
        """Test outlier removal using IQR method."""
        # Dataset with clear outliers
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100, 200]  # 100, 200 are outliers
        
        result = self.calculator.remove_outliers(values, method='iqr')
        
        # Should remove the extreme outliers
        assert len(result) < len(values)
        assert 100 not in result
        assert 200 not in result
        assert max(result) <= 10  # Normal values should remain
    
    def test_remove_outliers_zscore_method(self):
        """Test outlier removal using Z-score method."""
        # Dataset with very extreme outliers to ensure Z-score detection
        values = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 1000]  # 1000 is a clear outlier
        
        result = self.calculator.remove_outliers(values, method='zscore')
        
        # Should remove the extreme outlier
        assert len(result) < len(values)
        assert 1000 not in result
    
    def test_remove_outliers_percentile_method(self):
        """Test outlier removal using percentile method."""
        values = list(range(1, 101))  # 1 to 100
        
        result = self.calculator.remove_outliers(values, method='percentile')
        
        # Should remove values above 95th percentile
        assert len(result) <= 95  # Should keep ~95% of data
        assert max(result) <= 95  # Values above 95th percentile should be removed
    
    def test_remove_outliers_empty_data(self):
        """Test outlier removal with empty data."""
        result = self.calculator.remove_outliers([], method='iqr')
        assert result == []
    
    def test_remove_outliers_unknown_method(self):
        """Test outlier removal with unknown method."""
        values = [1, 2, 3, 4, 5, 100]
        
        result = self.calculator.remove_outliers(values, method='unknown')
        
        # Should default to IQR method
        assert len(result) < len(values)
        assert 100 not in result
    
    def test_get_statistics_with_outlier_removal(self):
        """Test comprehensive statistics with outlier removal."""
        # Dataset with outliers
        values = [10, 12, 11, 13, 12, 11, 10, 13, 100, 200]
        
        result = self.calculator.get_statistics_with_outlier_removal(values, 'iqr')
        
        assert 'original_stats' in result
        assert 'filtered_stats' in result
        assert 'outliers_removed' in result
        assert 'outlier_method' in result
        
        # Original stats should include outliers
        assert result['original_stats']['count'] == 10
        assert result['original_stats']['max'] == 200
        
        # Filtered stats should have outliers removed
        assert result['filtered_stats']['count'] < 10
        assert result['filtered_stats']['max'] < 100
        
        # Should report number of outliers removed
        assert result['outliers_removed'] > 0
        assert result['outlier_method'] == 'iqr'
    
    def test_get_statistics_with_outlier_removal_empty_data(self):
        """Test statistics with outlier removal on empty data."""
        result = self.calculator.get_statistics_with_outlier_removal([], 'iqr')
        
        assert result['original_stats']['count'] == 0
        assert result['filtered_stats']['count'] == 0
        assert result['outliers_removed'] == 0
        assert result['outlier_method'] == 'iqr'