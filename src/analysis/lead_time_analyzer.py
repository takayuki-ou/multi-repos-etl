"""
Lead Time Analyzer for Pull Request Review Analysis.
Calculates and analyzes lead times for pull requests.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from src.gui.data_manager import DataManager, _parse_datetime_string
from src.analysis.statistics_calculator import StatisticsCalculator

logger = logging.getLogger(__name__)


class LeadTimeAnalyzer:
    """
    Analyzes lead times for pull requests.
    Lead time is calculated as the time from PR creation to PR closure (merge or close).
    """
    
    def __init__(self, data_manager: DataManager):
        """
        Initialize the LeadTimeAnalyzer with a DataManager instance.
        
        Args:
            data_manager: DataManager instance for database access
        """
        self.data_manager = data_manager
        self.statistics_calculator = StatisticsCalculator()
        logger.info("LeadTimeAnalyzer initialized")
    
    def calculate_lead_times(self, pull_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate lead times for a list of pull requests.
        
        Args:
            pull_requests: List of pull request dictionaries from database
            
        Returns:
            List of dictionaries with lead time information added
            
        Requirements addressed: 1.1, 1.2, 1.3
        """
        if not pull_requests:
            logger.info("No pull requests provided for lead time calculation")
            return []
        
        lead_time_data = []
        processed_count = 0
        error_count = 0
        
        for pr in pull_requests:
            try:
                # Handle None entries
                if pr is None:
                    logger.warning("Encountered None PR entry, skipping")
                    error_count += 1
                    continue
                
                lead_time_info = self._calculate_single_pr_lead_time(pr)
                if lead_time_info:
                    lead_time_data.append(lead_time_info)
                    processed_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                pr_number = pr.get('number', 'unknown') if pr and isinstance(pr, dict) else 'unknown'
                logger.warning(f"Error calculating lead time for PR #{pr_number}: {e}")
                error_count += 1
                continue
        
        logger.info(f"Lead time calculation completed. Processed: {processed_count}, Errors: {error_count}")
        return lead_time_data
    
    def _calculate_single_pr_lead_time(self, pr: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Calculate lead time for a single pull request.
        
        Args:
            pr: Pull request dictionary from database
            
        Returns:
            Dictionary with lead time information or None if calculation fails
        """
        # Validate required data
        if not self._validate_pr_data(pr):
            return None
        
        # Parse creation time
        created_at = self._parse_pr_datetime(pr.get('created_at'))
        if not created_at:
            logger.warning(f"Could not parse created_at for PR #{pr.get('number')}")
            return None
        
        # Determine end time (merged_at takes precedence over closed_at)
        end_time = None
        end_type = None
        
        # Check if PR was merged
        if pr.get('merged_at'):
            merged_at = self._parse_pr_datetime(pr.get('merged_at'))
            if merged_at:
                end_time = merged_at
                end_type = 'merged'
        
        # If not merged, check if closed
        if not end_time and pr.get('closed_at'):
            closed_at = self._parse_pr_datetime(pr.get('closed_at'))
            if closed_at:
                end_time = closed_at
                end_type = 'closed'
        
        # If still no end time and PR is open, use current time
        if not end_time and pr.get('state') == 'open':
            end_time = datetime.now()
            end_type = 'open'
        
        # If we still don't have an end time, we can't calculate lead time
        if not end_time:
            logger.warning(f"Could not determine end time for PR #{pr.get('number')}")
            return None
        
        # Calculate lead time
        lead_time_delta = end_time - created_at
        lead_time_hours = lead_time_delta.total_seconds() / 3600
        lead_time_days = lead_time_hours / 24
        
        # Create result dictionary
        result = {
            'pr_id': pr.get('id'),
            'pr_number': pr.get('number'),
            'title': pr.get('title', ''),
            'author': pr.get('user_login', ''),
            'repository_id': pr.get('repository_id'),
            'created_at': created_at,
            'end_time': end_time,
            'end_type': end_type,
            'lead_time_hours': round(lead_time_hours, 2),
            'lead_time_days': round(lead_time_days, 2),
            'state': pr.get('state', ''),
            'url': pr.get('url', '')
        }
        
        return result
    
    def _validate_pr_data(self, pr: Dict[str, Any]) -> bool:
        """
        Validate that PR data contains required fields for lead time calculation.
        
        Args:
            pr: Pull request dictionary
            
        Returns:
            True if data is valid, False otherwise
        """
        # Check if pr is None or not a dictionary
        if pr is None or not isinstance(pr, dict):
            logger.warning("PR data is None or not a dictionary")
            return False
        
        required_fields = ['id', 'number', 'created_at', 'state']
        
        for field in required_fields:
            if field not in pr or pr[field] is None:
                logger.warning(f"PR missing required field '{field}': {pr.get('number', 'unknown')}")
                return False
        
        # Check that created_at is not empty
        created_at = pr.get('created_at')
        if not created_at or not str(created_at).strip():
            logger.warning(f"PR has empty created_at: {pr.get('number')}")
            return False
        
        return True
    
    def _parse_pr_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """
        Parse datetime string from PR data.
        
        Args:
            datetime_str: Datetime string from database
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not datetime_str:
            return None
        
        try:
            # Use the existing parsing function from data_manager
            return _parse_datetime_string(datetime_str)
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{datetime_str}': {e}")
            return None
    
    def format_lead_time_human_readable(self, hours: float) -> str:
        """
        Format lead time in human-readable format (days, hours, minutes).
        
        Args:
            hours: Lead time in hours
            
        Returns:
            Human-readable string representation
            
        Requirements addressed: 1.3
        """
        if hours < 0:
            return "Invalid lead time"
        
        if hours < 1:
            minutes = int(hours * 60)
            return f"{minutes} minutes"
        elif hours < 24:
            return f"{hours:.1f} hours"
        else:
            days = int(hours // 24)
            remaining_hours = hours % 24
            if remaining_hours < 1:
                return f"{days} days"
            else:
                return f"{days} days, {remaining_hours:.1f} hours"
    
    def get_lead_times_only(self, lead_time_data: List[Dict[str, Any]]) -> List[float]:
        """
        Extract just the lead time values in hours from lead time data.
        
        Args:
            lead_time_data: List of lead time dictionaries
            
        Returns:
            List of lead time values in hours
        """
        return [item['lead_time_hours'] for item in lead_time_data if 'lead_time_hours' in item]
    
    def calculate_basic_statistics(self, lead_times: List[float]) -> Dict[str, Any]:
        """
        Calculate basic statistical metrics for lead times.
        
        Args:
            lead_times: List of lead time values in hours
            
        Returns:
            Dictionary containing basic statistics
            
        Requirements addressed: 2.1, 2.4
        """
        return self.statistics_calculator.calculate_basic_statistics(lead_times)
    
    def calculate_percentiles(self, lead_times: List[float]) -> Dict[str, float]:
        """
        Calculate percentile distribution for lead times.
        
        Args:
            lead_times: List of lead time values in hours
            
        Returns:
            Dictionary containing percentile values
            
        Requirements addressed: 2.2
        """
        return self.statistics_calculator.calculate_percentiles(lead_times)
    
    def remove_outliers(self, lead_times: List[float], method: str = 'iqr') -> List[float]:
        """
        Remove outliers from lead times using specified method.
        
        Args:
            lead_times: List of lead time values in hours
            method: Method for outlier detection ('iqr', 'zscore', or 'percentile')
                   
        Returns:
            List of lead times with outliers removed
            
        Requirements addressed: 2.3
        """
        return self.statistics_calculator.remove_outliers(lead_times, method)
    
    def get_statistics_with_outlier_removal(self, lead_times: List[float], 
                                          outlier_method: str = 'iqr') -> Dict[str, Any]:
        """
        Calculate statistics after removing outliers and provide comparison.
        
        Args:
            lead_times: List of lead time values in hours
            outlier_method: Method for outlier removal ('iqr', 'zscore', 'percentile')
            
        Returns:
            Dictionary containing comparison of original and filtered statistics
            
        Requirements addressed: 2.3
        """
        return self.statistics_calculator.get_statistics_with_outlier_removal(lead_times, outlier_method)
    
    def group_by_period(self, lead_time_data: List[Dict[str, Any]], period: str = 'weekly') -> Dict[str, List[Dict[str, Any]]]:
        """
        Group pull requests by time periods (weekly or monthly).
        
        Args:
            lead_time_data: List of lead time dictionaries with created_at dates
            period: Grouping period ('weekly' or 'monthly')
            
        Returns:
            Dictionary with period keys and lists of PRs as values
            
        Requirements addressed: 4.1
        """
        if not lead_time_data:
            logger.info("No lead time data provided for period grouping")
            return {}
        
        if period not in ['weekly', 'monthly']:
            logger.warning(f"Invalid period '{period}'. Using 'weekly' as default.")
            period = 'weekly'
        
        grouped_data = defaultdict(list)
        processed_count = 0
        error_count = 0
        
        for pr_data in lead_time_data:
            try:
                created_at = pr_data.get('created_at')
                if not created_at:
                    logger.warning(f"PR #{pr_data.get('pr_number', 'unknown')} missing created_at")
                    error_count += 1
                    continue
                
                # Ensure created_at is a datetime object
                if isinstance(created_at, str):
                    created_at = self._parse_pr_datetime(created_at)
                    if not created_at:
                        error_count += 1
                        continue
                
                # Generate period key
                period_key = self._get_period_key(created_at, period)
                grouped_data[period_key].append(pr_data)
                processed_count += 1
                
            except Exception as e:
                pr_number = pr_data.get('pr_number', 'unknown')
                logger.warning(f"Error grouping PR #{pr_number} by period: {e}")
                error_count += 1
                continue
        
        logger.info(f"Period grouping completed. Processed: {processed_count}, Errors: {error_count}, Groups: {len(grouped_data)}")
        return dict(grouped_data)
    
    def _get_period_key(self, date: datetime, period: str) -> str:
        """
        Generate a period key for grouping based on the date and period type.
        
        Args:
            date: Datetime object
            period: Period type ('weekly' or 'monthly')
            
        Returns:
            String key representing the period
        """
        if period == 'weekly':
            # Get the Monday of the week containing this date
            monday = date - timedelta(days=date.weekday())
            return monday.strftime('%Y-W%U')  # Year-Week format
        elif period == 'monthly':
            return date.strftime('%Y-%m')  # Year-Month format
        else:
            raise ValueError(f"Unsupported period type: {period}")
    
    def calculate_period_statistics(self, grouped_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate average lead time and statistics for each period.
        
        Args:
            grouped_data: Dictionary with period keys and lists of PR data
            
        Returns:
            Dictionary with period keys and their statistics
            
        Requirements addressed: 4.2
        """
        if not grouped_data:
            logger.info("No grouped data provided for period statistics calculation")
            return {}
        
        period_stats = {}
        
        for period_key, pr_list in grouped_data.items():
            try:
                if not pr_list:
                    # Handle empty periods
                    period_stats[period_key] = {
                        'count': 0,
                        'average_lead_time_hours': 0.0,
                        'average_lead_time_days': 0.0,
                        'total_lead_time_hours': 0.0,
                        'period_start': None,
                        'period_end': None
                    }
                    continue
                
                # Extract lead times for this period
                lead_times = [pr['lead_time_hours'] for pr in pr_list if 'lead_time_hours' in pr]
                
                if not lead_times:
                    logger.warning(f"No valid lead times found for period {period_key}")
                    period_stats[period_key] = {
                        'count': len(pr_list),
                        'average_lead_time_hours': 0.0,
                        'average_lead_time_days': 0.0,
                        'total_lead_time_hours': 0.0,
                        'period_start': None,
                        'period_end': None
                    }
                    continue
                
                # Calculate statistics for this period
                avg_hours = sum(lead_times) / len(lead_times)
                avg_days = avg_hours / 24
                total_hours = sum(lead_times)
                
                # Get period boundaries
                dates = [pr['created_at'] for pr in pr_list if pr.get('created_at')]
                period_start = min(dates) if dates else None
                period_end = max(dates) if dates else None
                
                period_stats[period_key] = {
                    'count': len(pr_list),
                    'average_lead_time_hours': round(avg_hours, 2),
                    'average_lead_time_days': round(avg_days, 2),
                    'total_lead_time_hours': round(total_hours, 2),
                    'period_start': period_start,
                    'period_end': period_end,
                    'lead_times': lead_times  # Include raw data for further analysis
                }
                
            except Exception as e:
                logger.error(f"Error calculating statistics for period {period_key}: {e}")
                period_stats[period_key] = {
                    'count': len(pr_list) if pr_list else 0,
                    'average_lead_time_hours': 0.0,
                    'average_lead_time_days': 0.0,
                    'total_lead_time_hours': 0.0,
                    'period_start': None,
                    'period_end': None,
                    'error': str(e)
                }
        
        logger.info(f"Period statistics calculated for {len(period_stats)} periods")
        return period_stats
    
    def get_trend_data(self, lead_time_data: List[Dict[str, Any]], period: str = 'weekly') -> Dict[str, Any]:
        """
        Generate trend data by grouping PRs by period and calculating statistics.
        
        Args:
            lead_time_data: List of lead time dictionaries
            period: Grouping period ('weekly' or 'monthly')
            
        Returns:
            Dictionary containing grouped data and period statistics
            
        Requirements addressed: 4.1, 4.2
        """
        if not lead_time_data:
            logger.info("No lead time data provided for trend analysis")
            return {
                'grouped_data': {},
                'period_statistics': {},
                'period_type': period,
                'total_periods': 0,
                'total_prs': 0
            }
        
        # Group data by period
        grouped_data = self.group_by_period(lead_time_data, period)
        
        # Calculate statistics for each period
        period_statistics = self.calculate_period_statistics(grouped_data)
        
        # Calculate summary information
        total_periods = len(grouped_data)
        total_prs = sum(len(pr_list) for pr_list in grouped_data.values())
        
        result = {
            'grouped_data': grouped_data,
            'period_statistics': period_statistics,
            'period_type': period,
            'total_periods': total_periods,
            'total_prs': total_prs
        }
        
        logger.info(f"Trend data generated: {total_periods} periods, {total_prs} PRs")
        return result