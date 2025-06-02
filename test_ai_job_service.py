import pytest
from ai_job_service import AIJobSearchService


def test_get_ai_jobs_success():
    import os
    # Skip the test if a valid JOOBLE_API_KEY is not provided
    if os.environ.get("JOOBLE_API_KEY", "dummy_key") == "dummy_key":
        pytest.skip("Skipping live API test, no valid JOOBLE_API_KEY provided")
    service = AIJobSearchService(api_key=os.environ.get("JOOBLE_API_KEY"))
    result = service.get_ai_jobs(location="New York", limit=3)
    # Verify that the result contains the expected substrings.
    assert "🤖 AI ENGINEERING JOBS REPORT: Found" in result
    assert "New York" in result

def test_get_ai_jobs_failure():
    # Test failure scenario with an invalid API key,
    # expecting the get_ai_jobs method to raise an exception.
    service = AIJobSearchService(api_key="invalid_key")
    with pytest.raises(Exception) as excinfo:
        service.get_ai_jobs(location="New York", limit=3)
    assert "Jooble API error:" in str(excinfo.value)
