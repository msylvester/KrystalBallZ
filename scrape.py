from job_scraper import scrape_ai_jobs_for_rag
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

if __name__ == '__main__':
    try:
        # Get SCRAPFLY environment variable
        scrapfly_key = os.environ.get("SCRAPFLY")
        if not scrapfly_key:
            print("Warning: SCRAPFLY environment variable not found in .env file")
        else:
            print(f"Using SCRAPFLY key: {scrapfly_key[:10]}..." if len(scrapfly_key) > 10 else scrapfly_key)
        
        results = scrape_ai_jobs_for_rag()
        print(json.dumps(results, indent=2, default=str))
    except Exception as e:
        print(f"An error occurred: {e}")
