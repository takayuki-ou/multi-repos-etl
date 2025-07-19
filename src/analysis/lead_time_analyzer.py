"""
Lead Time Analyzer for Pull Request Review Analysis.
Calculates and analyzes lead times for pull requests.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.gui.data_manager import DataManager, _parse_datetime_string

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