import pytest
from ai_job_service import AIJobSearchService

# Dummy response class to simulate requests.Response
class DummyResponse:
    def __init__(self, status_code, json_data=None, headers=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._json

def test_get_ai_jobs_success(monkeypatch):
    # Simulate successful response with JSON payload
    dummy_data = {"totalResults": 5}
    dummy_headers = {"Content-Type": "application/json"}
    dummy_response = DummyResponse(200, json_data=dummy_data, headers=dummy_headers)

    def fake_post(url, json, headers):
        return dummy_response

    monkeypatch.setattr("ai_job_service.requests.post", fake_post)
    service = AIJobSearchService(api_key="dummy_key")
    result = service.get_ai_jobs(location="New York", limit=3)
    expected = "🤖 AI ENGINEERING JOBS REPORT: Found 5 jobs in New York"
    assert result == expected

def test_get_ai_jobs_failure(monkeypatch):
    # Simulate failure with text/html response
    dummy_headers = {"Content-Type": "text/html"}
    dummy_response = DummyResponse(404, headers=dummy_headers, text="Not Found")

    def fake_post(url, json, headers):
        return dummy_response

    monkeypatch.setattr("ai_job_service.requests.post", fake_post)
    service = AIJobSearchService(api_key="dummy_key")
    # When the response is a text/html, the method returns a report with limit as the number of jobs
    result = service.get_ai_jobs(location="New York", limit=3)
    expected = "🤖 AI ENGINEERING JOBS REPORT: Found 3 jobs in New York"
    assert result == expected
