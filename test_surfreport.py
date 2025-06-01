import pytest
import json
import requests
import os
from country_report import CountryReportAPI, authorize, process_surf_data, format_surf_report

class TestCountryReport:
    def test_api_authorization(self):
        """Test that the API authorization works correctly"""
        # Arrange
        test_api_key = "test_key_123"  # Not needed but kept for compatibility
        
        # Act
        api = authorize(test_api_key)
        
        # Assert
        assert api is not None
        assert api.api_key == test_api_key
        assert "Content-Type" in api.headers
    
    def test_api_get_data_real_request(self):
        """Test that the API get_data method works with real network requests"""
        print('\n[TEST] Starting real API request test')
        # Arrange
        api = authorize()
        
        # Act
        print(f'[TEST] Making API request to countries API')
        response = api.get_data()  # This will make a real network request

        print(f'[TEST] Response received: {json.dumps(response, indent=2)}')
        
        # Assert
        assert response is not None
        assert "location" in response
        assert "population" in response
        assert "region" in response
        assert "capital" in response
        assert "languages" in response
        
    def test_api_get_data_with_region(self):
        """Test that the API get_data method works with a specific region"""
        # Arrange
        api = authorize()
        
        # Act - use a specific region
        response = api.get_data(region="europe")
        
        # Assert
        assert response is not None
        assert "location" in response
        assert response["region"] == "Europe"
    
    def test_api_with_invalid_region(self):
        """Test that the API handles invalid regions appropriately"""
        # Arrange
        api = authorize()
        
        # Act & Assert
        with pytest.raises(requests.exceptions.RequestException):
            api.get_data(region="invalid_region_name")
        
    def test_process_country_data(self):
        """Test that country data is processed correctly"""
        # Arrange
        test_data = {
            "location": "Test Country",
            "population": "15,000,000",
            "region": "Europe",
            "subregion": "Western Europe",
            "capital": "Test City",
            "languages": "English, French",
            "timestamp": "2025-05-31 12:00"
        }
        
        # Act
        processed = process_surf_data(test_data)
        
        # Assert
        assert processed["size_category"] == "Medium"
        assert processed["tourist_friendly"] == True
        
    def test_format_country_report(self):
        """Test that the country report is formatted correctly"""
        # Arrange
        test_data = {
            "location": "Test Country",
            "population": "15,000,000",
            "region": "Europe",
            "subregion": "Western Europe",
            "capital": "Test City",
            "languages": "English, French",
            "timestamp": "2025-05-31 12:00",
            "size_category": "Medium",
            "tourist_friendly": True
        }
        
        # Act
        report = format_surf_report(test_data)
        
        # Assert
        assert "COUNTRY REPORT - Test Country" in report
        assert "Population: 15,000,000" in report
        assert "Popular tourist destination" in report
