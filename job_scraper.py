# Ensure you run "pip install playwright" and then "playwright install" to install Playwright dependencies.
import requests
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
    url = "https://www.greenhouse.io/jobs?q=ai+engineer"
    print("Launching Playwright browser for scraping Greenhouse jobs")
    storage_file = "playwright_storage.json"
    with sync_playwright() as p:
         browser = p.chromium.launch(headless=True)
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
         page.wait_for_selector("div.opening", timeout=90000)
         content = page.content()
         context.storage_state(path=storage_file)
         browser.close()
    soup = BeautifulSoup(content, "html.parser")
    job_cards = soup.find_all("div", class_="opening")
    print(f'The job cards found: {job_cards}')
    results = []
    for card in job_cards[:10]:
         link_elem = card.find("a")
         if link_elem:
             title_text = link_elem.get_text(strip=True)
             apply_link = link_elem.get('href', '')
             if apply_link and not apply_link.startswith("http"):
                 apply_link = "https://www.greenhouse.io" + apply_link
         else:
             title_text = None
             apply_link = ""
         location_elem = card.find("span", class_="location")
         location_text = location_elem.get_text(strip=True) if location_elem else "N/A"
         job = {
             "job_title": title_text,
             "company": "Greenhouse",
             "location": location_text,
             "employment_type": "N/A",
             "remote": False,
             "salary_range": "N/A",
             "tech_stack": [],
             "description": "",
             "apply_link": apply_link,
             "source": "Greenhouse",
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
