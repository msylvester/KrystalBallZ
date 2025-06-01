import argparse
import requests
from datetime import datetime
import logging
import random

# Configure logging
logger = logging.getLogger("countryreport")

class CountryReportAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key  # Not needed for countries API but kept for compatibility
        self.base_url = "https://restcountries.com/v3.1"
        self.headers = {
            "Content-Type": "application/json"
        }
        
    def get_data(self, region=None):
        """
        Get country data from the API
        
        Args:
            region (str): Optional region to filter countries by
            
        Returns:
            dict: Processed country report data
        """
        # Make the actual API request
        url = f"{self.base_url}/all"
        if region:
            url = f"{self.base_url}/region/{region}"
            
        logger.info(f"Making API request to {url}")
        
        response = requests.get(
            url,
            headers=self.headers,
            timeout=10
        )
        
        # Check if request was successful
        response.raise_for_status()
        data = response.json()
        
        # Select a random country from the response
        country = random.choice(data)
        
        # Process the API response into our expected format
        return {
            "api_key_used": self.api_key or "Not required",
            "status": "success",
            "location": country.get("name", {}).get("common", "Unknown Country"),
            "population": f"{country.get('population', 0):,}",
            "region": country.get("region", "Unknown"),
            "subregion": country.get("subregion", "Unknown"),
            "capital": ", ".join(country.get("capital", ["Unknown"])),
            "languages": ", ".join(country.get("languages", {}).values()),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

def authorize(api_key=None):
    """Authorize with the country report API"""
    return CountryReportAPI(api_key)

def process_surf_data(data):
    """Process the country data"""
    # Add derived information based on raw data
    population = int(data["population"].replace(",", ""))
    
    if population > 100000000:
        data["size_category"] = "Large"
    elif population > 10000000:
        data["size_category"] = "Medium"
    else:
        data["size_category"] = "Small"
        
    # Calculate if it's suitable for tourism
    if data["region"] in ["Europe", "Oceania", "Americas"]:
        data["tourist_friendly"] = True
    else:
        data["tourist_friendly"] = False
        
    return data

def format_surf_report(data):
    """Format the country report for display"""
    tourist_msg = "Popular tourist destination!" if data.get("tourist_friendly") else "Less common tourist destination"
    
    return f"🌍 COUNTRY REPORT - {data['location']} ({data['timestamp']})\n\n" \
           f"Population: {data['population']}\n" \
           f"Region: {data['region']}\n" \
           f"Subregion: {data['subregion']}\n" \
           f"Capital: {data['capital']}\n" \
           f"Languages: {data['languages']}\n" \
           f"Size Category: {data['size_category']}\n" \
           f"Note: {tourist_msg}"

def main():
    parser = argparse.ArgumentParser(description='Get country report')
    parser.add_argument('--region', help='Optional region to filter by (Africa, Americas, Asia, Europe, Oceania)', default=None)
    args = parser.parse_args()
    
    # Initialize API (no key needed)
    api = authorize()
    
    # Get country data
    country_data = api.get_data(region=args.region)
    
    # Process data
    processed_data = process_surf_data(country_data)
    
    # Format and print report
    report = format_surf_report(processed_data)
    print(report)

if __name__ == "__main__":
    main()
