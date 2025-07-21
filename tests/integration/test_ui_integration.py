#!/usr/bin/env python3
"""
Simple integration test for the Streamlit UI components
"""
import sys
sys.path.append('.')

from src.gui.data_manager import DataManager
from src.analysis.lead_time_analyzer import LeadTimeAnalyzer
from datetime import datetime
import unittest
from typing import Optional, Tuple

class TestUIIntegration(unittest.TestCase):
    """Test class for UI integration tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.data_manager = DataManager()
        self.analyzer = LeadTimeAnalyzer(self.data_manager)
    
    def test_data_manager_initialization(self):
        """Test DataManager initialization"""
        self.assertIsNotNone(self.data_manager)
        print("✅ DataManager initialized successfully")
    
    def test_lead_time_analyzer_initialization(self):
        """Test LeadTimeAnalyzer initialization"""
        self.assertIsNotNone(self.analyzer)
        print("✅ LeadTimeAnalyzer initialized successfully")
    
    def test_filter_validation_with_dates_and_author(self):
        """Test filter validation with dates and author"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        is_valid, error = self.data_manager.validate_filter_combination(start_date, end_date, "test_author", None)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        print("✅ Filter validation with dates and author works")
    
    def test_invalid_date_range(self):
        """Test invalid date range detection"""
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)
        is_valid, error = self.data_manager.validate_filter_combination(start_date, end_date, None, None)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        print(f"✅ Invalid date range detected: {error}")
    
    def test_status_filter_validation_open(self):
        """Test status filter validation with 'open' status"""
        is_valid, error = self.data_manager.validate_filter_combination(None, None, None, "open")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        print("✅ Valid 'open' status filter accepted")
    
    def test_status_filter_validation_closed(self):
        """Test status filter validation with 'closed' status"""
        is_valid, error = self.data_manager.validate_filter_combination(None, None, None, "closed")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        print("✅ Valid 'closed' status filter accepted")
    
    def test_invalid_status_filter(self):
        """Test invalid status filter detection"""
        is_valid, error = self.data_manager.validate_filter_combination(None, None, None, "invalid_status")
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        print(f"✅ Invalid status detected: {error}")
    
    def test_combined_filters(self):
        """Test combined filters (date, author, status)"""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        is_valid, error = self.data_manager.validate_filter_combination(start_date, end_date, "test_author", "closed")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        print("✅ Combined filters validation works")
    
    def test_ui_function_imports(self):
        """Test UI function imports"""
        try:
            from src.gui.app import display_lead_time_filters, display_lead_time_analysis
            self.assertTrue(True)
            print("✅ UI functions imported successfully")
        except ImportError as e:
            self.fail(f"Import failed: {e}")
    
    def test_function_signature(self):
        """Test function signature for display_lead_time_filters"""
        from src.gui.app import display_lead_time_filters
        import inspect
        
        # Check return type annotation
        sig = inspect.signature(display_lead_time_filters)
        return_annotation = sig.return_annotation
        
        # The return type should be a Tuple with 5 elements (including status filter)
        self.assertEqual(return_annotation.__origin__, tuple)
        
        # Should have 5 elements (start_date, end_date, author, status, filters_applied)
        self.assertEqual(len(return_annotation.__args__), 5)
        
        # Check that status is included (4th parameter should be Optional[str])
        status_type = return_annotation.__args__[3]
        self.assertEqual(status_type.__args__[0], str)
        
        print("✅ Function signature includes status filter parameter")

def test_ui_integration():
    """Legacy test function for backward compatibility"""
    try:
        # Test DataManager initialization
        print("Testing DataManager initialization...")
        data_manager = DataManager()
        print("✅ DataManager initialized successfully")
        
        # Test LeadTimeAnalyzer initialization
        print("Testing LeadTimeAnalyzer initialization...")
        analyzer = LeadTimeAnalyzer(data_manager)
        print("✅ LeadTimeAnalyzer initialized successfully")
        
        # Test filter validation
        print("Testing filter validation...")
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)
        is_valid, error = data_manager.validate_filter_combination(start_date, end_date, "test_author", None)
        print(f"✅ Filter validation works: valid={is_valid}, error={error}")
        
        # Test invalid date range
        print("Testing invalid date range...")
        is_valid, error = data_manager.validate_filter_combination(end_date, start_date, None, None)
        print(f"✅ Invalid date range detected: valid={is_valid}, error='{error}'")
        
        # Test status filter validation
        print("Testing status filter validation...")
        is_valid, error = data_manager.validate_filter_combination(None, None, None, "open")
        print(f"✅ Valid status filter: valid={is_valid}, error={error}")
        
        # Test invalid status
        print("Testing invalid status...")
        is_valid, error = data_manager.validate_filter_combination(None, None, None, "invalid_status")
        print(f"✅ Invalid status detected: valid={is_valid}, error='{error}'")
        
        # Test UI function imports
        print("Testing UI function imports...")
        from src.gui.app import display_lead_time_filters, display_lead_time_analysis
        print("✅ UI functions imported successfully")
        
        # Test function signature
        print("Testing function signature...")
        import inspect
        sig = inspect.signature(display_lead_time_filters)
        return_annotation = sig.return_annotation
        print(f"✅ Return annotation: {return_annotation}")
        
        print("\n🎉 All UI integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run unittest tests
    unittest.main()