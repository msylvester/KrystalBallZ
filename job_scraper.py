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

def scrape_ai_jobs_for_rag():
    """
    Scrape AI engineering job postings from various job boards and return structured data.
    For this example the implementation is a placeholder that returns dummy data.
    In production, you could use requests and BeautifulSoup to scrape sites like LinkedIn, Indeed, etc.,
    and filter out postings older than 30 days.
    """
    url = "https://www.linkedin.com/jobs/search/?keywords=ai+engineering"
    print("Launching Playwright browser for scraping LinkedIn jobs")
    import sys
    headful_mode = "--headful" in sys.argv
    if headful_mode:
         print("Running in headful mode!")
    storage_file = "playwright_storage.json"
    import random
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
         import os
         if os.path.exists(storage_file):
             context_kwargs["storage_state"] = storage_file
         context = browser.new_context(**context_kwargs)
         page = context.new_page()
         page.goto(url, timeout=90000)
         # Set random viewport dimensions
         page.set_viewport_size({
             "width": 1920 + random.randint(0,100), 
             "height": 1080 + random.randint(0,100)
         })
         # Improved waiting strategy
         page.wait_for_load_state('networkidle', timeout=90000)
         page.wait_for_function('''() => {
             return document.querySelectorAll('ul.jobs-search__results-list li').length > 0
         }''', timeout=90000)
         content = page.content()
         # Save debugging information
         page.screenshot(path='debug.png')
         with open('page_dump.html', 'w') as f:
             f.write(content)
         context.storage_state(path=storage_file)
         browser.close()
    soup = BeautifulSoup(content, "html.parser")
    job_cards = soup.select("ul.jobs-search__results-list li")
    print(f'The job cards found: {job_cards}')
    results = []
    for card in job_cards[:10]:
         link_elem = card.find("a", class_="base-card__full-link")
         if link_elem:
             title_elem = card.find("h3", class_="base-search-card__title")
             title_text = title_elem.get_text(strip=True) if title_elem else None
             apply_link = link_elem.get('href', '')
         else:
             title_text = None
             apply_link = ""
         company_elem = card.find("h4", class_="base-search-card__subtitle")
         company_text = company_elem.get_text(strip=True) if company_elem else "LinkedIn"
         location_elem = card.find("span", class_="job-search-card__location")
         location_text = location_elem.get_text(strip=True) if location_elem else "N/A"
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
             "posted_date": datetime.now().strftime("%Y-%m-%d")
         }
         results.append(job)
    return results

if __name__ == '__main__':
    try:
        jobs = scrape_ai_jobs_for_rag()
        import json
        print("Scraped Jobs:")
        print(json.dumps(jobs, indent=2, default=str))
    except Exception as e:
        print(f"An error occurred: {e}")
