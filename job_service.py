from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import logging
import os
from ai_job_service import AIJobSearchService

# Configure logging for the API
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_jobs_api")

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
