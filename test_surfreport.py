import pytest
import requests
from unittest.mock import patch, MagicMock
from surfreport import SurfReportAPI, authorize, process_surf_data, format_surf_report

class TestSurfReport:
    def test_api_authorization(self):
        """Test that the API authorization works correctly"""
        # Arrange
        test_api_key = "test_key_123"
        
        # Act
        api = authorize(test_api_key)
        
        # Assert
        assert api is not None
        assert api.api_key == test_api_key
        assert "Bearer test_key_123" in api.headers["Authorization"]
    
    @patch('surfreport.requests.get')
    def test_api_get_data_success(self, mock_get):
        """Test that the API get_data method works correctly with a successful response"""
        # Arrange
        test_api_key = "test_key_123"
        api = authorize(test_api_key)
        
        # Configure the mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "spot": {"name": "Test Beach"},
            "forecast": {
                "waveHeight": {"min": 2, "max": 3},
                "wind": {"speed": 10, "direction": "offshore"},
                "tide": {"type": "low"},
                "temperature": {"water": 68}
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Act
        response = api.get_data()
        
        # Assert
        assert response is not None
        assert response["api_key_used"] == test_api_key
        assert response["status"] == "authorized"
        assert response["location"] == "Test Beach"
        assert response["wave_height"] == "2-3 ft"
        assert "offshore" in response["wind"]
        
        # Verify the API was called with correct parameters
        mock_get.assert_called_once()
        
    @patch('surfreport.requests.get')
    def test_api_get_data_failure(self, mock_get):
        """Test that the API get_data method falls back to mock data when the API call fails"""
        # Arrange
        test_api_key = "test_key_123"
        api = authorize(test_api_key)
        
        # Configure the mock to raise an exception
        mock_get.side_effect = requests.exceptions.RequestException("API is down")
        
        # Act
        response = api.get_data()
        
        # Assert - should fall back to mock data
        assert response is not None
        assert response["api_key_used"] == test_api_key
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
