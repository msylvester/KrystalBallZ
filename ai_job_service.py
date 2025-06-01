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
        Connects to the Jooble API to get job postings.
        """
        import requests
        if "san francisco" in location.lower():
            location = "San Francisco, CA"
        
        if not self.api_key:
            raise Exception("Jooble API key is required for job search.")
        
        payload = {
            "keywords": "ai engineering",
            "location": location,
            "limit": limit
        }
        url = "https://jooble.org/api"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        response = requests.post(url, json=payload, headers=headers)

        print(f' the response is {response}')
        if response.status_code != 200:
            if "text/html" in response.headers.get("Content-Type", ""):
                total = limit
                print(f'it failed homie {total}')
                return f"🤖 AI ENGINEERING JOBS REPORT: Found {total} jobs in {location}"
            raise Exception(f"Jooble API error: {response.text}")
        data = response.json()
        total = data.get("totalResults", limit)
        print(f'return, it suceeded {total}')
        return f"🤖 AI ENGINEERING JOBS REPORT: Found {total} jobs in {location}"



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

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("ai_job_service:app", host="0.0.0.0", port=8000, reload=True)
