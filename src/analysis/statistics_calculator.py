"""
Statistics Calculator for numerical data analysis.
Provides statistical calculations and outlier detection functionality.
"""
import logging
import numpy as np
from scipy import stats
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StatisticsCalculator:
    """
    A utility class for performing statistical calculations on numerical data.
    Provides basic statistics, percentile analysis, and outlier detection.
    """
    
    def __init__(self):
        """Initialize the StatisticsCalculator."""
        logger.info("StatisticsCalculator initialized")
    
    def calculate_basic_statistics(self, values: List[float]) -> Dict[str, Any]:
        """
        Calculate basic statistical metrics for numerical values.
        
        Args:
            values: List of numerical values
            
        Returns:
            Dictionary containing basic statistics:
            - count: Number of data points
            - mean: Average value
            - median: Median value
            - min: Minimum value
            - max: Maximum value
            - std_dev: Standard deviation
        """
        if not values:
            logger.warning("No values provided for statistics calculation")
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
        
        # Convert to numpy array for efficient calculation
        values_array = np.array(values)
        
        # Remove any NaN or infinite values
        clean_values = values_array[np.isfinite(values_array)]
        
        if len(clean_values) == 0:
            logger.warning("No valid values after cleaning data")
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
        
        try:
            statistics = {
                'count': len(clean_values),
                'mean': float(np.mean(clean_values)),
                'median': float(np.median(clean_values)),
                'min': float(np.min(clean_values)),
                'max': float(np.max(clean_values)),
                'std_dev': float(np.std(clean_values, ddof=1)) if len(clean_values) > 1 else 0.0
            }
            
            logger.info(f"Basic statistics calculated for {statistics['count']} values")
            return statistics
            
        except Exception as e:
            logger.error(f"Error calculating basic statistics: {e}")
            return {
                'count': len(clean_values),
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
    
    def calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """
        Calculate percentile distribution for numerical values.
        
        Args:
            values: List of numerical values
            
        Returns:
            Dictionary containing percentile values:
            - p25: 25th percentile (Q1)
            - p75: 75th percentile (Q3)
            - p90: 90th percentile
            - p95: 95th percentile
            - iqr: Interquartile Range (Q3 - Q1)
        """
        if not values:
            logger.warning("No values provided for percentile calculation")
            return {
                'p25': 0.0,
                'p75': 0.0,
                'p90': 0.0,
                'p95': 0.0,
                'iqr': 0.0
            }
        
        # Convert to numpy array for efficient calculation
        values_array = np.array(values)
        
        # Remove any NaN or infinite values
        clean_values = values_array[np.isfinite(values_array)]
        
        if len(clean_values) == 0:
            logger.warning("No valid values after cleaning data for percentiles")
            return {
                'p25': 0.0,
                'p75': 0.0,
                'p90': 0.0,
                'p95': 0.0,
                'iqr': 0.0
            }
        
        try:
            # Calculate percentiles
            p25 = float(np.percentile(clean_values, 25))
            p75 = float(np.percentile(clean_values, 75))
            p90 = float(np.percentile(clean_values, 90))
            p95 = float(np.percentile(clean_values, 95))
            iqr = p75 - p25
            
            percentiles = {
                'p25': p25,
                'p75': p75,
                'p90': p90,
                'p95': p95,
                'iqr': iqr
            }
            
            logger.info(f"Percentiles calculated for {len(clean_values)} values")
            return percentiles
            
        except Exception as e:
            logger.error(f"Error calculating percentiles: {e}")
            return {
                'p25': 0.0,
                'p75': 0.0,
                'p90': 0.0,
                'p95': 0.0,
                'iqr': 0.0
            }
    
    def remove_outliers(self, values: List[float], method: str = 'iqr') -> List[float]:
        """
        Remove outliers from numerical values using specified method.
        
        Args:
            values: List of numerical values
            method: Method for outlier detection ('iqr', 'zscore', or 'percentile')
                   - 'iqr': Values outside Q1 - 1.5*IQR or Q3 + 1.5*IQR
                   - 'zscore': Values with |z-score| > 3
                   - 'percentile': Values above 95th percentile
                   
        Returns:
            List of values with outliers removed
        """
        if not values:
            logger.warning("No values provided for outlier removal")
            return []
        
        # Convert to numpy array for efficient calculation
        values_array = np.array(values)
        
        # Remove any NaN or infinite values first
        clean_values = values_array[np.isfinite(values_array)]
        
        if len(clean_values) == 0:
            logger.warning("No valid values after initial cleaning")
            return []
        
        try:
            if method == 'iqr':
                return self._remove_outliers_iqr(clean_values)
            elif method == 'zscore':
                return self._remove_outliers_zscore(clean_values)
            elif method == 'percentile':
                return self._remove_outliers_percentile(clean_values)
            else:
                logger.warning(f"Unknown outlier removal method: {method}. Using IQR method.")
                return self._remove_outliers_iqr(clean_values)
                
        except Exception as e:
            logger.error(f"Error removing outliers using {method} method: {e}")
            return clean_values.tolist()
    
    def _remove_outliers_iqr(self, values: np.ndarray) -> List[float]:
        """
        Remove outliers using IQR (Interquartile Range) method.
        
        Args:
            values: NumPy array of numerical values
            
        Returns:
            List of values with outliers removed
        """
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Keep values within bounds
        filtered_values = values[(values >= lower_bound) & (values <= upper_bound)]
        
        outliers_removed = len(values) - len(filtered_values)
        if outliers_removed > 0:
            logger.info(f"Removed {outliers_removed} outliers using IQR method")
        
        return filtered_values.tolist()
    
    def _remove_outliers_zscore(self, values: np.ndarray) -> List[float]:
        """
        Remove outliers using Z-score method.
        
        Args:
            values: NumPy array of numerical values
            
        Returns:
            List of values with outliers removed
        """
        if len(values) < 2:
            return values.tolist()
        
        z_scores = np.abs(stats.zscore(values))
        
        # Keep values with |z-score| <= 3
        filtered_values = values[z_scores <= 3]
        
        outliers_removed = len(values) - len(filtered_values)
        if outliers_removed > 0:
            logger.info(f"Removed {outliers_removed} outliers using Z-score method")
        
        return filtered_values.tolist()
    
    def _remove_outliers_percentile(self, values: np.ndarray) -> List[float]:
        """
        Remove outliers using percentile method (removes values above 95th percentile).
        
        Args:
            values: NumPy array of numerical values
            
        Returns:
            List of values with outliers removed
        """
        p95 = np.percentile(values, 95)
        
        # Keep values at or below 95th percentile
        filtered_values = values[values <= p95]
        
        outliers_removed = len(values) - len(filtered_values)
        if outliers_removed > 0:
            logger.info(f"Removed {outliers_removed} outliers using percentile method")
        
        return filtered_values.tolist()
    
    def get_statistics_with_outlier_removal(self, values: List[float], 
                                          outlier_method: str = 'iqr') -> Dict[str, Any]:
        """
        Calculate statistics after removing outliers and provide comparison.
        
        Args:
            values: List of numerical values
            outlier_method: Method for outlier removal ('iqr', 'zscore', 'percentile')
            
        Returns:
            Dictionary containing:
            - original_stats: Statistics before outlier removal
            - filtered_stats: Statistics after outlier removal
            - outliers_removed: Number of outliers removed
            - outlier_method: Method used for outlier removal
        """
        if not values:
            logger.warning("No values provided for statistics with outlier removal")
            return {
                'original_stats': self.calculate_basic_statistics([]),
                'filtered_stats': self.calculate_basic_statistics([]),
                'outliers_removed': 0,
                'outlier_method': outlier_method
            }
        
        # Calculate original statistics
        original_stats = self.calculate_basic_statistics(values)
        
        # Remove outliers
        filtered_values = self.remove_outliers(values, method=outlier_method)
        
        # Calculate filtered statistics
        filtered_stats = self.calculate_basic_statistics(filtered_values)
        
        outliers_removed = len(values) - len(filtered_values)
        
        result = {
            'original_stats': original_stats,
            'filtered_stats': filtered_stats,
            'outliers_removed': outliers_removed,
            'outlier_method': outlier_method
        }
        
        logger.info(f"Statistics calculated with {outliers_removed} outliers removed using {outlier_method} method")
        return result