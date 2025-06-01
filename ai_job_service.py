import logging

logger = logging.getLogger("ai_job_service")

class AIJobSearchService:
    def __init__(self, api_key=""):
        self.api_key = api_key

    def get_ai_jobs(self, location="", limit=10):
        """
        Returns a dummy job report string.
        In production, this would connect to the Jooble API or use internal logic.
        """
        # If San Francisco data is requested, simulate special behavior.
        if "san francisco" in location.lower():
            location = "San Francisco, CA"
        return f"🤖 AI ENGINEERING JOBS REPORT: Found {limit} jobs in {location}"

    def _fetch_job_data(self, location, limit):
        """
        Simulate fetching job data.
        """
        logger.info(f"Fetching job data for location: {location}, limit: {limit}")
        # The dummy data mimics the real structure expected by the API layer.
        return {
            "jobs": [{"title": "Mock Job", "company": "Mock Company"}],
            "total_results": 1,
            "timestamp": "2025-06-01T12:00:00Z"
        }

    def _process_job_data(self, job_data):
        """
        Process fetched job data.
        """
        return job_data
