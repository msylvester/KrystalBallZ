#!/usr/bin/env python
import os
import requests
from dotenv import load_dotenv
from ai_job_service import AIJobSearchService

load_dotenv()


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
