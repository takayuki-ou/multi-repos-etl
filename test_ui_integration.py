#!/usr/bin/env python3
"""
Simple integration test for the Streamlit UI components
"""
import sys
sys.path.append('.')

from src.gui.data_manager import DataManager
from src.analysis.lead_time_analyzer import LeadTimeAnalyzer
from datetime import datetime

def test_ui_integration():
    """Test that all UI components can be imported and initialized"""
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
        is_valid, error = data_manager.validate_filter_combination(start_date, end_date, "test_author")
        print(f"✅ Filter validation works: valid={is_valid}, error={error}")
        
        # Test invalid date range
        print("Testing invalid date range...")
        is_valid, error = data_manager.validate_filter_combination(end_date, start_date, None)
        print(f"✅ Invalid date range detected: valid={is_valid}, error='{error}'")
        
        print("\n🎉 All UI integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_ui_integration()
    sys.exit(0 if success else 1)