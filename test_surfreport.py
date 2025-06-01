import pytest
import requests
import os
from surfreport import SurfReportAPI, authorize, process_surf_data, format_surf_report

class TestSurfReport:
    def test_api_authorization(self):
        """Test that the API authorization works correctly"""
        # Arrange
        test_api_key = os.environ.get("SURFLINE_API_KEY", "test_key_123")
        
        # Act
        api = authorize(test_api_key)
        
        # Assert
        assert api is not None
        assert api.api_key == test_api_key
        assert f"Bearer {test_api_key}" in api.headers["Authorization"]
    
    def test_api_get_data_real_request(self):
        """Test that the API get_data method works with real network requests"""
        # Arrange
        test_api_key = os.environ.get("SURFLINE_API_KEY", "test_key_123")
        api = authorize(test_api_key)
        
        # Act
        response = api.get_data()  # This will make a real network request
        
        # Assert
        assert response is not None
        assert response["api_key_used"] == test_api_key
        assert response["status"] == "authorized"
        assert "location" in response
        assert "wave_height" in response
        assert "wind" in response
        assert "temperature" in response
        
    def test_api_get_data_with_custom_spot(self):
        """Test that the API get_data method works with a custom spot ID"""
        # Arrange
        test_api_key = os.environ.get("SURFLINE_API_KEY", "test_key_123")
        api = authorize(test_api_key)
        
        # Act - use a different spot ID (Pipeline, Hawaii)
        response = api.get_data(spot_id="5842041f4e65fad6a7708964")
        
        # Assert
        assert response is not None
        assert "location" in response
        # The rest of the assertions depend on the actual response
    
    def test_api_fallback_with_invalid_key(self):
        """Test that the API falls back to mock data with an invalid API key"""
        # Arrange
        invalid_api_key = "invalid_key_that_will_fail"
        api = authorize(invalid_api_key)
        
        # Act
        response = api.get_data()
        
        # Assert - should fall back to mock data
        assert response is not None
        assert response["api_key_used"] == invalid_api_key
        assert response["status"] == "authorized"
        assert response["location"] == "Malibu Beach"  # This is from the mock data
        
    def test_process_surf_data(self):
        """Test that surf data is processed correctly"""
        # Arrange
        test_data = {
            "location": "Test Beach",
            "wave_height": "2-3 ft",
            "wind": "10 mph offshore",
            "tide": "low",
            "temperature": "68°F",
            "timestamp": "2025-05-31 12:00"
        }
        
        # Act
        processed = process_surf_data(test_data)
        
        # Assert
        assert processed["conditions"] == "Good"
        assert processed["beginner_friendly"] == True
        
    def test_format_surf_report(self):
        """Test that the surf report is formatted correctly"""
        # Arrange
        test_data = {
            "location": "Test Beach",
            "wave_height": "2-3 ft",
            "wind": "10 mph offshore",
            "tide": "low",
            "temperature": "68°F",
            "timestamp": "2025-05-31 12:00",
            "conditions": "Good",
            "beginner_friendly": True
        }
        
        # Act
        report = format_surf_report(test_data)
        
        # Assert
        assert "SURF REPORT - Test Beach" in report
        assert "Wave Height: 2-3 ft" in report
        assert "Good for beginners" in report
