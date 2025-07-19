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
    
    def calculate_trend_statistics(self, grouped_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate trend statistics with change rates and trend direction.
        
        Args:
            grouped_data: Dictionary with period keys and lists of PR data
            
        Returns:
            Dictionary with period keys and their trend statistics including change rates
            
        Requirements addressed: 4.3, 4.4
        """
        if not grouped_data:
            logger.info("No grouped data provided for trend statistics calculation")
            return {}
        
        trend_data = {}
        periods = sorted(grouped_data.keys())
        
        for i, period in enumerate(periods):
            pr_list = grouped_data[period]
            
            try:
                # Extract lead times for this period
                lead_times = [pr['lead_time_hours'] for pr in pr_list if 'lead_time_hours' in pr]
                current_avg = sum(lead_times) / len(lead_times) if lead_times else 0.0
                
                # Calculate change rate compared to previous period
                change_rate = 0.0
                prev_period_key = None
                if i > 0:
                    prev_period_key = periods[i-1]
                    if prev_period_key in trend_data:
                        prev_avg = trend_data[prev_period_key]['average']
                        if prev_avg > 0:
                            change_rate = ((current_avg - prev_avg) / prev_avg) * 100
                
                # Determine trend direction
                trend_direction = self._determine_trend_direction(change_rate)
                
                # Calculate additional statistics
                median_time = 0.0
                min_time = 0.0
                max_time = 0.0
                if lead_times:
                    sorted_times = sorted(lead_times)
                    median_time = sorted_times[len(sorted_times) // 2]
                    min_time = min(lead_times)
                    max_time = max(lead_times)
                
                # Get period boundaries
                dates = [pr['created_at'] for pr in pr_list if pr.get('created_at')]
                period_start = min(dates) if dates else None
                period_end = max(dates) if dates else None
                
                trend_data[period] = {
                    'average': round(current_avg, 2),
                    'median': round(median_time, 2),
                    'min': round(min_time, 2),
                    'max': round(max_time, 2),
                    'count': len(pr_list),
                    'change_rate': round(change_rate, 2),
                    'trend_direction': trend_direction,
                    'previous_period': prev_period_key,
                    'period_start': period_start,
                    'period_end': period_end,
                    'lead_times': lead_times  # Raw data for further analysis
                }
                
            except Exception as e:
                logger.error(f"Error calculating trend statistics for period {period}: {e}")
                trend_data[period] = {
                    'average': 0.0,
                    'median': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'count': len(pr_list) if pr_list else 0,
                    'change_rate': 0.0,
                    'trend_direction': 'unknown',
                    'previous_period': None,
                    'period_start': None,
                    'period_end': None,
                    'error': str(e)
                }
        
        logger.info(f"Trend statistics calculated for {len(trend_data)} periods")
        return trend_data
    
    def _determine_trend_direction(self, change_rate: float) -> str:
        """
        Determine trend direction based on change rate.
        
        Args:
            change_rate: Percentage change from previous period
            
        Returns:
            String indicating trend direction ('improving', 'worsening', 'stable', 'unknown')
        """
        if change_rate == 0.0:
            return 'stable'
        elif change_rate < -5.0:  # More than 5% improvement (decrease in lead time)
            return 'improving'
        elif change_rate > 5.0:   # More than 5% worsening (increase in lead time)
            return 'worsening'
        elif -5.0 <= change_rate <= 5.0:  # Within 5% range
            return 'stable'
        else:
            return 'unknown'
    
    def calculate_moving_averages(self, trend_data: Dict[str, Dict[str, Any]], 
                                window_sizes: List[int] = [3, 7]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate moving averages for trend data.
        
        Args:
            trend_data: Dictionary with period trend statistics
            window_sizes: List of window sizes for moving averages (default: [3, 7])
            
        Returns:
            Enhanced trend data with moving averages
        """
        if not trend_data or not window_sizes:
            return trend_data
        
        periods = sorted(trend_data.keys())
        averages = [trend_data[period]['average'] for period in periods]
        
        enhanced_data = trend_data.copy()
        
        for window_size in window_sizes:
            if window_size <= 0 or window_size > len(periods):
                continue
                
            moving_avg_key = f'moving_avg_{window_size}'
            
            for i, period in enumerate(periods):
                if i >= window_size - 1:
                    # Calculate moving average for current window
                    window_values = averages[i - window_size + 1:i + 1]
                    moving_avg = sum(window_values) / len(window_values)
                    enhanced_data[period][moving_avg_key] = round(moving_avg, 2)
                else:
                    # Not enough data for moving average
                    enhanced_data[period][moving_avg_key] = None
        
        return enhanced_data
    
    def get_multi_repository_trend_data(self, repository_data: Dict[int, List[Dict[str, Any]]], 
                                      period: str = 'weekly') -> Dict[str, Any]:
        """
        Generate trend data for multiple repositories with combined and individual analysis.
        
        Args:
            repository_data: Dictionary with repository_id as key and list of lead time data as value
            period: Grouping period ('weekly' or 'monthly')
            
        Returns:
            Dictionary containing combined and individual repository trend data
            
        Requirements addressed: 4.3
        """
        if not repository_data:
            logger.info("No repository data provided for multi-repository trend analysis")
            return {
                'combined_trend': {},
                'individual_trends': {},
                'repository_summary': {},
                'period_type': period
            }
        
        result = {
            'combined_trend': {},
            'individual_trends': {},
            'repository_summary': {},
            'period_type': period
        }
        
        # Calculate individual repository trends
        for repo_id, lead_time_data in repository_data.items():
            if not lead_time_data:
                continue
                
            try:
                # Get trend data for this repository
                repo_trend = self.get_trend_data(lead_time_data, period)
                
                # Calculate trend statistics
                trend_stats = self.calculate_trend_statistics(repo_trend['grouped_data'])
                
                # Add moving averages
                enhanced_stats = self.calculate_moving_averages(trend_stats)
                
                result['individual_trends'][repo_id] = {
                    'trend_data': repo_trend,
                    'trend_statistics': enhanced_stats,
                    'total_prs': len(lead_time_data),
                    'total_periods': len(repo_trend['grouped_data'])
                }
                
                # Calculate repository summary
                all_lead_times = [pr['lead_time_hours'] for pr in lead_time_data]
                if all_lead_times:
                    result['repository_summary'][repo_id] = {
                        'total_prs': len(all_lead_times),
                        'average_lead_time': round(sum(all_lead_times) / len(all_lead_times), 2),
                        'median_lead_time': round(sorted(all_lead_times)[len(all_lead_times) // 2], 2),
                        'min_lead_time': round(min(all_lead_times), 2),
                        'max_lead_time': round(max(all_lead_times), 2)
                    }
                
            except Exception as e:
                logger.error(f"Error processing repository {repo_id} trend data: {e}")
                result['individual_trends'][repo_id] = {
                    'error': str(e),
                    'total_prs': len(lead_time_data) if lead_time_data else 0,
                    'total_periods': 0
                }
        
        # Calculate combined trend (all repositories together)
        try:
            all_lead_time_data = []
            for repo_data in repository_data.values():
                all_lead_time_data.extend(repo_data)
            
            if all_lead_time_data:
                combined_trend_data = self.get_trend_data(all_lead_time_data, period)
                combined_trend_stats = self.calculate_trend_statistics(combined_trend_data['grouped_data'])
                enhanced_combined_stats = self.calculate_moving_averages(combined_trend_stats)
                
                result['combined_trend'] = {
                    'trend_data': combined_trend_data,
                    'trend_statistics': enhanced_combined_stats,
                    'total_prs': len(all_lead_time_data),
                    'total_periods': len(combined_trend_data['grouped_data']),
                    'total_repositories': len([repo_id for repo_id, data in repository_data.items() if data])
                }
            
        except Exception as e:
            logger.error(f"Error calculating combined trend data: {e}")
            result['combined_trend'] = {'error': str(e)}
        
        logger.info(f"Multi-repository trend analysis completed for {len(repository_data)} repositories")
        return result
    
    def handle_empty_periods(self, trend_statistics: Dict[str, Dict[str, Any]], 
                           period_type: str = 'weekly', 
                           fill_gaps: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Handle periods with no pull requests by filling gaps or marking them appropriately.
        
        Args:
            trend_statistics: Dictionary with period trend statistics
            period_type: Type of period ('weekly' or 'monthly')
            fill_gaps: Whether to fill empty periods with zero values
            
        Returns:
            Enhanced trend statistics with empty periods handled
            
        Requirements addressed: 4.4
        """
        if not trend_statistics:
            return trend_statistics
        
        periods = sorted(trend_statistics.keys())
        if len(periods) < 2:
            return trend_statistics
        
        # Generate all expected periods between first and last
        first_period = periods[0]
        last_period = periods[-1]
        
        try:
            expected_periods = self._generate_period_range(first_period, last_period, period_type)
        except Exception as e:
            logger.warning(f"Could not generate period range: {e}")
            return trend_statistics
        
        enhanced_statistics = {}
        
        for period in expected_periods:
            if period in trend_statistics:
                # Period has data
                enhanced_statistics[period] = trend_statistics[period]
            elif fill_gaps:
                # Period has no data, fill with zeros
                enhanced_statistics[period] = {
                    'average': 0.0,
                    'median': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'count': 0,
                    'change_rate': 0.0,
                    'trend_direction': 'no_data',
                    'previous_period': None,
                    'period_start': None,
                    'period_end': None,
                    'lead_times': [],
                    'is_empty_period': True
                }
            # If fill_gaps is False, we skip empty periods
        
        # Recalculate change rates for filled periods
        if fill_gaps:
            enhanced_periods = sorted(enhanced_statistics.keys())
            for i, period in enumerate(enhanced_periods):
                if i > 0:
                    prev_period = enhanced_periods[i-1]
                    current_avg = enhanced_statistics[period]['average']
                    prev_avg = enhanced_statistics[prev_period]['average']
                    
                    if prev_avg > 0:
                        change_rate = ((current_avg - prev_avg) / prev_avg) * 100
                        enhanced_statistics[period]['change_rate'] = round(change_rate, 2)
                        # Only update trend direction if it's not already marked as no_data
                        if not enhanced_statistics[period].get('is_empty_period', False):
                            enhanced_statistics[period]['trend_direction'] = self._determine_trend_direction(change_rate)
                    
                    enhanced_statistics[period]['previous_period'] = prev_period
        
        logger.info(f"Empty periods handled: {len(enhanced_statistics)} total periods, {len(expected_periods) - len(periods)} gaps filled")
        return enhanced_statistics
    
    def _generate_period_range(self, start_period: str, end_period: str, period_type: str) -> List[str]:
        """
        Generate a list of all periods between start and end periods.
        
        Args:
            start_period: Starting period string
            end_period: Ending period string
            period_type: Type of period ('weekly' or 'monthly')
            
        Returns:
            List of period strings
        """
        periods = []
        
        if period_type == 'weekly':
            # Parse weekly periods (format: YYYY-WXX)
            start_year, start_week = self._parse_weekly_period(start_period)
            end_year, end_week = self._parse_weekly_period(end_period)
            
            current_year, current_week = start_year, start_week
            
            while (current_year, current_week) <= (end_year, end_week):
                periods.append(f"{current_year}-W{current_week:02d}")
                current_week += 1
                if current_week > 52:  # Simplified - doesn't handle leap years perfectly
                    current_week = 1
                    current_year += 1
                    
        elif period_type == 'monthly':
            # Parse monthly periods (format: YYYY-MM)
            start_year, start_month = map(int, start_period.split('-'))
            end_year, end_month = map(int, end_period.split('-'))
            
            current_year, current_month = start_year, start_month
            
            while (current_year, current_month) <= (end_year, end_month):
                periods.append(f"{current_year}-{current_month:02d}")
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1
        
        return periods
    
    def _parse_weekly_period(self, period_str: str) -> tuple:
        """
        Parse weekly period string to extract year and week number.
        
        Args:
            period_str: Weekly period string (format: YYYY-WXX)
            
        Returns:
            Tuple of (year, week_number)
        """
        try:
            parts = period_str.split('-W')
            year = int(parts[0])
            week = int(parts[1])
            return year, week
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid weekly period format '{period_str}': {e}")