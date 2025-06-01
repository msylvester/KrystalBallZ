import logging
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

# Configure logging for the API
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_jobs_api")

# AIJobSearchService implementation
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

# Setup FastAPI app
app = FastAPI(title="AI Job Search API", version="1.0")

# Inject the Jooble API key securely from environment variables
jooble_api_key = os.environ.get("JOOBLE_API_KEY", "")
service = AIJobSearchService(api_key=jooble_api_key)

@app.get("/jobs")
def get_jobs(location: str = Query("", title="Job location filter"),
             limit: int = Query(10, gt=0, le=100, title="Maximum number of jobs to return")):
    """
    GET /jobs
    Retrieve AI/ML job postings filtered by location and limit.

    Response JSON Structure:
      - jobs: List of job listings (each a dict with title, company, etc.)
      - totalCount: The total number of jobs (from the processed data)
      - locationUsed: The location filter provided
      - timestampQueried: Timestamp from the processed data
    """
    logger.info(f"Received /jobs request with location='{location}' and limit={limit}")
    try:
        # Instead of the formatted text report, call internal workflow to get raw data.
        job_data = service._fetch_job_data(location, limit)
        processed_data = service._process_job_data(job_data)
        response_payload = {
            "jobs": processed_data.get("jobs", []),
            "totalCount": processed_data.get("total_results", 0),
            "locationUsed": location,
            "timestampQueried": processed_data.get("timestamp", "")
        }
        logger.info(f"Returning response: {response_payload}")
        return JSONResponse(content=response_payload, status_code=200)
    except Exception as e:
        logger.error(f"Error in /jobs endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching job listings: {str(e)}")

@app.get("/health")
def health_check():
    """
    GET /health
    Simple health-check endpoint.
    """
    return {"status": "ok", "message": "API is up and running"}
