import pytest
from unittest.mock import patch, Mock
from ai_job_service import AIJobSearchService
import os


def test_get_ai_jobs_success_mocked():
    """Test get_ai_jobs with mocked API response"""
    service = AIJobSearchService(api_key="test_key")
    
    # Mock the internal methods
    mock_raw_data = {
        "jobs": [
            {"title": "AI Engineer", "company": "Tech Corp", "location": "New York"},
            {"title": "ML Engineer", "company": "Data Inc", "location": "New York"}
        ],
        "totalCount": 25
    }
    
    with patch.object(service, '_fetch_job_data', return_value=mock_raw_data):
        result = service.get_ai_jobs(location="New York", limit=3)
        
    # Verify that the result contains the expected substrings
    assert "🤖 AI ENGINEERING JOBS REPORT: Found" in result
    assert "25 jobs" in result
    assert "New York" in result


def test_get_ai_jobs_no_api_key():
    """Test that missing API key raises appropriate error"""
    service = AIJobSearchService(api_key="")
    with pytest.raises(Exception) as excinfo:
        service.get_ai_jobs(location="New York", limit=3)
    assert "Jooble API key is required" in str(excinfo.value)


def test_get_ai_jobs_api_forbidden():
    """Test handling of 403 Forbidden response"""
    service = AIJobSearchService(api_key="invalid_key")
    
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    
    with patch('ai_job_service.requests.post', return_value=mock_response):
        with pytest.raises(Exception) as excinfo:
            service.get_ai_jobs(location="New York", limit=3)
        assert "Jooble API access forbidden" in str(excinfo.value)


def test_get_ai_jobs_api_error():
    """Test handling of other API errors"""
    service = AIJobSearchService(api_key="test_key")
    
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch('ai_job_service.requests.post', return_value=mock_response):
        with pytest.raises(Exception) as excinfo:
            service.get_ai_jobs(location="New York", limit=3)
        assert "Jooble API error: Status 500" in str(excinfo.value)


def test_san_francisco_location_mapping():
    """Test that 'san francisco' gets mapped to proper format"""
    service = AIJobSearchService(api_key="test_key")
    
    mock_raw_data = {"jobs": [], "totalCount": 0}
    
    with patch.object(service, '_fetch_job_data', return_value=mock_raw_data) as mock_fetch:
        service.get_ai_jobs(location="san francisco", limit=3)
        mock_fetch.assert_called_with("San Francisco, CA", 3)


@pytest.mark.integration
def test_get_ai_jobs_real_api():
    """Integration test with real API - only runs if JOOBLE_API_KEY is set"""
    api_key = os.environ.get("JOOBLE_API_KEY")
    if not api_key or api_key == "dummy_key":
        pytest.skip("Skipping live API test, no valid JOOBLE_API_KEY provided")
    
    service = AIJobSearchService(api_key=api_key)
    try:
        result = service.get_ai_jobs(location="New York", limit=3)
        assert "🤖 AI ENGINEERING JOBS REPORT: Found" in result
        assert "New York" in result
    except Exception as e:
        if "403" in str(e) or "forbidden" in str(e).lower():
            pytest.skip(f"API key may be invalid or expired: {e}")
        else:
            raise
