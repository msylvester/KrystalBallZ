import pytest
from fastapi.testclient import TestClient
from ai_job_service import AIJobSearchService, app

def test_get_ai_jobs():
    service = AIJobSearchService(api_key="dummy")
    result = service.get_ai_jobs(location="New York", limit=3)
    expected = "🤖 AI ENGINEERING JOBS REPORT: Found 3 jobs in New York"
    assert result == expected

def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
