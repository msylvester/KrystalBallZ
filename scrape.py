from job_scraper import scrape_ai_jobs_for_rag
import json

if __name__ == '__main__':
    try:
        results = scrape_ai_jobs_for_rag()
        print(json.dumps(results, indent=2, default=str))
    except Exception as e:
        print(f"An error occurred: {e}")
