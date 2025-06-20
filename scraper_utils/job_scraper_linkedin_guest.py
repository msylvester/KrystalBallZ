# Ensure you run "pip install playwright" and then "playwright install" to install Playwright dependencies.
import requests
import random
try:
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:
    import sys
    sys.exit("ModuleNotFoundError: No module named 'playwright'. Please install it using 'pip install playwright' and then run 'playwright install'.")
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import json
from scraper_utils.data_processor import (
    standardize_job_data,
    prepare_for_vector_db,
    validate_job_data
)
import time
import re

def time_diff_from_now(time_str):
    """
    Converts a time string like "1 hour ago", "2 days ago", etc.
    to a Unix timestamp representing the posted time.
    If the time string is invalid, raises a ValueError.
    """
    now = int(time.time())
    match = re.match(r'(\d+)\s*(second|minute|hour|day|week|month|year)s?\s+ago', time_str.lower())
    if not match:
        raise ValueError("Invalid time format. Expected formats like '1 hour ago', '2 weeks ago', etc.")
    quantity = int(match.group(1))
    unit = match.group(2)
    unit_seconds = {
        'second': 1,
        'minute': 60,
        'hour': 3600,
        'day': 86400,
        'week': 604800,
        'month': 2629800,  # Approximate: 30.44 days
        'year': 31557600,  # Approximate: 365.25 days
    }
    diff_seconds = quantity * unit_seconds[unit]
    return now - diff_seconds

def scrape_ai_jobs_for_rag(max_jobs=100):
    """
    Scrape AI engineering job postings from various job boards and return structured data.
    Uses pagination and multiple search terms to get more comprehensive results.
    """
    search_terms = [
        "ai+engineering",
        "machine+learning+engineer", 
        "data+scientist",
        "artificial+intelligence",
        "deep+learning"
    ]
    
    all_results = []
    print(f"Launching Playwright browser for scraping LinkedIn jobs (guest API) - targeting {max_jobs} jobs")
    import sys
    headful_mode = "--headful" in sys.argv
    if headful_mode:
         print("Running in headful mode!")
    storage_file = "playwright_storage.json"
    
    with sync_playwright() as p:
         browser = p.chromium.launch(
             headless=not headful_mode,
             args=[
                 '--disable-blink-features=AutomationControlled',
                 '--disable-web-security'
             ]
         )
         context_kwargs = {
             "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
             "locale": "en-US"
         }
         if os.path.exists(storage_file):
             context_kwargs["storage_state"] = storage_file
         context = browser.new_context(**context_kwargs)
         page = context.new_page()
         
         # Set random viewport dimensions
         page.set_viewport_size({
             "width": 1920 + random.randint(0,100), 
             "height": 1080 + random.randint(0,100)
         })
         
         # Loop through search terms and pagination
         for search_term in search_terms:
             if len(all_results) >= max_jobs:
                 break
                 
             print(f"Searching for: {search_term}")
             start = 0
             jobs_per_page = 25  # LinkedIn typically returns 25 jobs per page
             
             while len(all_results) < max_jobs:
                 url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={search_term}&location=&start={start}"
                 print(f"Fetching page starting at position {start}")
                 
                 page.goto(url, timeout=90000)
                 # Improved waiting strategy
                 page.wait_for_load_state('networkidle', timeout=90000)
                 page.wait_for_function('''() => {
                     return document.querySelectorAll('li').length > 0
                 }''', timeout=90000)
                 content = page.content()
                 
                 soup = BeautifulSoup(content, "html.parser")
                 job_cards = soup.select("li")
                 print(f'Found {len(job_cards)} job cards on this page')
                 
                 page_results = []
                 # Process more jobs per page (up to 50 instead of 10)
                 for card in job_cards[:50]:
                     link_elem = card.find("a", class_="base-card__full-link")
                     if link_elem:
                         title_elem = card.find("h3", class_="base-search-card__title")
                         title_text = title_elem.get_text(strip=True) if title_elem else None
                         apply_link = link_elem.get('href', '')
                     else:
                         title_text = None
                         apply_link = ""
                     
                     # Skip if no title (likely not a valid job posting)
                     if not title_text:
                         continue
                         
                     company_elem = card.find("h4", class_="base-search-card__subtitle")
                     company_text = company_elem.get_text(strip=True) if company_elem else "LinkedIn"
                     location_elem = card.find("span", class_="job-search-card__location")
                     location_text = location_elem.get_text(strip=True) if location_elem else "N/A"
                     posted_elem = card.find("time")
                     posted_raw = posted_elem.get_text(strip=True) if posted_elem else "N/A"
                     try:
                         posted_date = time_diff_from_now(posted_raw)
                     except Exception:
                         posted_date = "N/A"
                     
                     job = {
                         "job_title": title_text,
                         "company": company_text,
                         "location": location_text,
                         "employment_type": "N/A",
                         "remote": False,
                         "salary_range": "N/A",
                         "tech_stack": [],
                         "description": "",
                         "apply_link": apply_link,
                         "source": "LinkedIn",
                         "search_term": search_term.replace('+', ' '),
                         "posted_date": posted_date
                     }
                     page_results.append(job)
                 
                 # Add page results to overall results
                 all_results.extend(page_results)
                 print(f"Total jobs collected so far: {len(all_results)}")
                 
                 # Break if no more jobs found on this page or we have enough
                 if not page_results or len(all_results) >= max_jobs:
                     break
                     
                 start += jobs_per_page
                 
                 # Add a small delay between requests to be respectful
                 page.wait_for_timeout(2000)
         
         # Save debugging information for the last page
         page.screenshot(path='debug.png')
         with open('page_dump.html', 'w') as f:
             f.write(content)
         context.storage_state(path=storage_file)
         browser.close()
    
    # Remove duplicates based on job title and company
    seen = set()
    unique_results = []
    for job in all_results:
        job_key = (job['job_title'], job['company'])
        if job_key not in seen:
            seen.add(job_key)
            unique_results.append(job)
    
    print(f"Unique jobs before processing: {len(unique_results)}")
    
    # Process and standardize the data
    processed_results = []
    vector_ready_results = []
    
    for job in unique_results:
        # Validate job data quality
        if not validate_job_data(job):
            print(f"Skipping invalid job: {job.get('job_title', 'Unknown')}")
            continue
            
        # Standardize the data
        try:
            standardized_job = standardize_job_data(job)
            processed_results.append(standardized_job)
            
            # Prepare for vector database
            vector_ready_job = prepare_for_vector_db(standardized_job)
            vector_ready_results.append(vector_ready_job)
            
        except Exception as e:
            print(f"Error processing job {job.get('job_title', 'Unknown')}: {str(e)}")
            continue
    
    # Limit to requested number of jobs
    processed_results = processed_results[:max_jobs]
    vector_ready_results = vector_ready_results[:max_jobs]
    
    print(f"Final processed job count: {len(processed_results)}")
    print(f"Vector-ready job count: {len(vector_ready_results)}")
    
    # Save results to files
    os.makedirs("./data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save raw data
    raw_filename = f"./data/raw_jobs_{timestamp}.json"
    with open(raw_filename, 'w', encoding='utf-8') as f:
        json.dump(unique_results, f, indent=2, default=str, ensure_ascii=False)
    
    # Save processed/standardized data
    processed_filename = f"./data/processed_jobs_{timestamp}.json"
    with open(processed_filename, 'w', encoding='utf-8') as f:
        json.dump(processed_results, f, indent=2, default=str, ensure_ascii=False)
    
    # Save vector-ready data
    vector_filename = f"./data/vector_ready_jobs_{timestamp}.json"
    with open(vector_filename, 'w', encoding='utf-8') as f:
        json.dump(vector_ready_results, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"Raw data saved to: {raw_filename}")
    print(f"Processed data saved to: {processed_filename}")
    print(f"Vector-ready data saved to: {vector_filename}")
    
    return vector_ready_results

if __name__ == '__main__':
    try:
        jobs = scrape_ai_jobs_for_rag()
        import json
        print("Scraped Jobs:")
        print(json.dumps(jobs, indent=2, default=str))
    except Exception as e:
        print(f"An error occurred: {e}")
