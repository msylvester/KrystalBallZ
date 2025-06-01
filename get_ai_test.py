#!/usr/bin/env python
import os
import requests
from dotenv import load_dotenv
from ai_job_service import AIJobSearchService

load_dotenv()

# Dummy response class for monkey patching
class DummyResponse:
    def __init__(self, status_code, headers, text):
        self.status_code = status_code
        self.headers = headers
        self.text = text
    def json(self):
        return {}

# Dummy requests.post to simulate Cloudflare challenge response
def dummy_post(url, json, headers):
    return DummyResponse(
        status_code=400,
        headers={"Content-Type": "text/html"},
        text="<!DOCTYPE html>..."
    )

# Save the original requests.post to restore later if needed
original_post = requests.post
requests.post = dummy_post

def main():
    api_key = os.environ.get("JOOBLE_API_KEY", "dummy")
    service = AIJobSearchService(api_key=api_key)
    result = service.get_ai_jobs(location="New York", limit=3)
    print("Test result:", result)
    expected = "🤖 AI ENGINEERING JOBS REPORT: Found 3 jobs in New York"
    assert result == expected, f"Expected: {expected}, but got: {result}"
    print("Test passed.")

if __name__ == '__main__':
    main()
    # Restore the original requests.post after test
    requests.post = original_post
