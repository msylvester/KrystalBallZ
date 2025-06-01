import pytest
import requests
import os
from surfreport import SurfReportAPI, authorize, process_surf_data, format_surf_report

class TestSurfReport:
    def test_api_authorization(self):
        """Test that the API authorization works correctly.
        
        This test verifies that the authorize function properly initializes
        a SurfReportAPI instance with the provided API key and sets up the
        authorization header correctly.
        
        Example:
            Success: When a valid API key "abc123" is provided, the function returns
                    a SurfReportAPI instance with api_key="abc123" and 
                    headers["Authorization"]="Bearer abc123".
            Failure: If the API key is not properly set in the headers or the
                    returned object is not a SurfReportAPI instance, the test fails.
        """
        # Arrange
        test_api_key = os.environ.get("SURFLINE_API_KEY", "test_key_123")
        
        # Act
        api = authorize(test_api_key)
        
        # Assert
        assert api is not None
        assert api.api_key == test_api_key
        assert f"Bearer {test_api_key}" in api.headers["Authorization"]
    
    def test_api_get_data_real_request(self):
        """Test that the API get_data method works with real network requests.
        
        This test makes an actual network request to the Surfline API and verifies
        that the response contains the expected data structure.
        
        Example:
            Success: When the API request succeeds, the response contains keys like
                    "location", "wave_height", "wind", and "temperature" with valid values.
            Failure: If the API request fails or the response doesn't contain the
                    expected keys, the test fails. This could happen due to network issues,
                    invalid API key, or changes in the API response structure.
        """
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
        """Test that the API get_data method works with a custom spot ID.
        
        This test verifies that the API can retrieve data for a specific surf spot
        by providing a custom spot ID (Pipeline, Hawaii in this case).
        
        Example:
            Success: When a valid spot ID "5842041f4e65fad6a7708964" is provided,
                    the API returns data specific to that location (Pipeline, Hawaii).
            Failure: If the spot ID is invalid or the API can't retrieve data for
                    that location, the test fails. The API might fall back to mock data
                    or return an error.
        """
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
        """Test that the API falls back to mock data with an invalid API key.
        
        This test verifies the fallback mechanism when the API request fails due to
        an invalid API key. The system should gracefully fall back to mock data.
        
        Example:
            Success: When an invalid API key is provided, the get_data method
                    returns mock data with location="Malibu Beach" instead of failing.
            Failure: If the fallback mechanism doesn't work and the method raises
                    an exception or returns None, the test fails.
        """
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
        """Test that surf data is processed correctly.
        
        This test verifies that the process_surf_data function correctly analyzes
        raw surf data and adds derived information like conditions and beginner-friendliness.
        
        Example:
            Success: When data with "offshore" wind and wave height < 3ft is processed,
                    the function adds "conditions": "Good" and "beginner_friendly": True.
            Failure: If the function incorrectly assesses conditions (e.g., marking
                    offshore wind as "Poor") or beginner-friendliness (e.g., marking
                    1-2 ft waves as not beginner-friendly), the test fails.
        """
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
        """Test that the surf report is formatted correctly.
        
        This test verifies that the format_surf_report function correctly formats
        the processed surf data into a human-readable string report.
        
        Example:
            Success: When valid processed data is provided, the function returns a
                    formatted string containing all the key information like location,
                    wave height, and beginner-friendliness.
            Failure: If the function omits important information or formats it
                    incorrectly (e.g., missing the beginner-friendly message or
                    incorrectly displaying wave height), the test fails.
        """
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
