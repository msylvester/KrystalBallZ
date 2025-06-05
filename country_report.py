import requests
import json
import random
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("country_report")

class CountryReportAPI:
    """API client for fetching country data from restcountries.com"""
    
    def __init__(self, api_key=None):
        """Initialize the API client
        
        Args:
            api_key: Not required for restcountries.com but kept for compatibility
        """
        self.api_key = api_key
        self.base_url = "https://restcountries.com/v3.1"
        self.headers = {
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger("country_report.CountryReportAPI")
    
    def get_data(self, region=None):
        """Fetch country data from the API
        
        Args:
            region: Optional region filter (e.g., 'europe', 'asia')
            
        Returns:
            Dictionary with country information
        """
        try:
            # Determine the endpoint based on whether a region is specified
            if region:
                region = region.lower()
                self.logger.info(f"Fetching countries in region: {region}")
                endpoint = f"{self.base_url}/region/{region}"
            else:
                self.logger.info("Fetching all countries")
                endpoint = f"{self.base_url}/all"
            
            # Make the API request
            self.logger.info(f"Making request to: {endpoint}")
            response = requests.get(endpoint, headers=self.headers)
            
            # Check if the request was successful
            if response.status_code != 200:
                self.logger.error(f"API request failed with status code: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                raise requests.exceptions.RequestException(f"API request failed with status code: {response.status_code}")
            
            # Parse the response
            countries = response.json()
            self.logger.info(f"Received data for {len(countries)} countries")
            
            # Select a random country
            if not countries:
                self.logger.error("No countries found in the response")
                raise ValueError("No countries found in the response")
            
            country = random.choice(countries)
            self.logger.info(f"Selected country: {country.get('name', {}).get('common', 'Unknown')}")
            
            # Format the country data
            return self._format_country_data(country)
            
        except Exception as e:
            self.logger.error(f"Error fetching country data: {str(e)}")
            raise
    
    def _format_country_data(self, country):
        """Format the country data into a standardized structure
        
        Args:
            country: Raw country data from the API
            
        Returns:
            Dictionary with formatted country information
        """
        # Extract country name
        country_name = country.get('name', {}).get('common', 'Unknown')
        
        # Extract population and format it
        population = country.get('population', 0)
        formatted_population = f"{population:,}" if population else "Unknown"
        
        # Extract region and subregion
        region = country.get('region', 'Unknown')
        subregion = country.get('subregion', 'Unknown')
        
        # Extract capital
        capitals = country.get('capital', ['Unknown'])
        capital = capitals[0] if capitals else 'Unknown'
        
        # Extract languages
        languages_dict = country.get('languages', {})
        languages = ", ".join(languages_dict.values()) if languages_dict else "Unknown"
        
        # Current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Return formatted data
        return {
            "location": country_name,
            "population": formatted_population,
            "region": region,
            "subregion": subregion,
            "capital": capital,
            "languages": languages,
            "timestamp": timestamp
        }

def authorize(api_key=None):
    """Create and return an authorized API client
    
    Args:
        api_key: Optional API key (not required for restcountries.com)
        
    Returns:
        CountryReportAPI instance
    """
    return CountryReportAPI(api_key)

def process_surf_data(data):
    """Process the country data (legacy function name)"""
    return process_country_data(data)

def process_country_data(data):
    """Process country data to add derived metrics
    
    Args:
        data: Dictionary with country information
        
    Returns:
        Dictionary with additional derived metrics
    """
    # Make a copy of the data to avoid modifying the original
    processed_data = data.copy()
    
    # Determine population size category
    population_str = data.get('population', '0')
    # Remove commas from the population string
    population_num = int(population_str.replace(',', '')) if isinstance(population_str, str) else int(population_str)
    
    if population_num < 1_000_000:
        processed_data['size_category'] = 'Small'
    elif population_num < 50_000_000:
        processed_data['size_category'] = 'Medium'
    else:
        processed_data['size_category'] = 'Large'
    
    # Determine if the country is likely tourist-friendly
    # This is a simplified heuristic - in reality, many more factors would be considered
    languages = data.get('languages', '').lower()
    region = data.get('region', '').lower()
    
    tourist_friendly = (
        'english' in languages or
        region in ['europe', 'oceania'] or
        len(languages.split(',')) > 2  # Countries with multiple languages tend to be more tourist-friendly
    )
    
    processed_data['tourist_friendly'] = tourist_friendly
    
    return processed_data

def format_surf_report(data):
    """Format the country report for display (legacy function name)"""
    return format_country_report(data)

def format_country_report(data):
    """Format the country data into a human-readable report
    
    Args:
        data: Dictionary with country information and derived metrics
        
    Returns:
        String with formatted country report
    """
    # Extract data
    country = data.get('location', 'Unknown')
    population = data.get('population', 'Unknown')
    region = data.get('region', 'Unknown')
    subregion = data.get('subregion', 'Unknown')
    capital = data.get('capital', 'Unknown')
    languages = data.get('languages', 'Unknown')
    size_category = data.get('size_category', 'Unknown')
    tourist_friendly = data.get('tourist_friendly', False)
    timestamp = data.get('timestamp', 'Unknown')
    
    # Build the report
    report = f"""
===========================================
COUNTRY REPORT - {country}
===========================================
Generated on: {timestamp}

LOCATION INFORMATION:
---------------------
Region: {region}
Subregion: {subregion}
Capital: {capital}

DEMOGRAPHICS:
------------
Population: {population}
Size Category: {size_category}
Languages: {languages}

TRAVEL ADVISORY:
---------------
{country} is a {"popular tourist destination" if tourist_friendly else "less common tourist destination"}.
{"Multiple languages are spoken, which may make it easier for tourists." if "," in languages else ""}

===========================================
"""
    
    return report

def main():
    parser = argparse.ArgumentParser(description='Get country report')
    parser.add_argument('--region', help='Optional region to filter by (Africa, Americas, Asia, Europe, Oceania)', default=None)
    args = parser.parse_args()
    
    # Initialize API (no key needed)
    api = authorize()
    
    # Get country data
    country_data = api.get_data(region=args.region)
    
    # Process data
    processed_data = process_country_data(country_data)
    
    # Format and print report
    report = format_country_report(processed_data)
    print(report)

if __name__ == "__main__":
    main()
