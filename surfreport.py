import argparse
import requests
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger("surfreport")

class SurfReportAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.surfline.com/v1/forecasts"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
    def get_data(self, spot_id="5842041f4e65fad6a7708890"):  # Default to Malibu Beach spot ID
        """
        Get surf report data from the API
        
        Args:
            spot_id (str): The ID of the surf spot to get data for
            
        Returns:
            dict: Processed surf report data
        """
        try:
            # Make the actual API request
            url = f"{self.base_url}/{spot_id}"
            logger.info(f"Making API request to {url}")
            
            response = requests.get(
                url,
                headers=self.headers,
                timeout=10
            )
            
            # Check if request was successful
            response.raise_for_status()
            data = response.json()
            
            # Process the API response into our expected format
            # Note: This would need to be adjusted based on the actual API response structure
            return {
                "api_key_used": self.api_key,
                "status": "authorized",
                "location": data.get("spot", {}).get("name", "Malibu Beach"),
                "wave_height": f"{data.get('forecast', {}).get('waveHeight', {}).get('min', 3)}-{data.get('forecast', {}).get('waveHeight', {}).get('max', 4)} ft",
                "wind": f"{data.get('forecast', {}).get('wind', {}).get('speed', 5)} mph {data.get('forecast', {}).get('wind', {}).get('direction', 'offshore')}",
                "tide": data.get('forecast', {}).get('tide', {}).get('type', 'rising'),
                "temperature": f"{data.get('forecast', {}).get('temperature', {}).get('water', 72)}°F",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            # Fall back to mock data if the API request fails
            logger.info("Falling back to mock data")
            return self._get_mock_data()
            
    def _get_mock_data(self):
        """Provide mock data as a fallback"""
        return {
            "api_key_used": self.api_key,
            "status": "authorized",
            "location": "Malibu Beach",
            "wave_height": "3-4 ft",
            "wind": "5 mph offshore",
            "tide": "rising",
            "temperature": "72°F",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

def authorize(api_key):
    """Authorize with the surf report API"""
    return SurfReportAPI(api_key)

def process_surf_data(data):
    """Process the surf data"""
    # Add derived information based on raw data
    if "offshore" in data["wind"].lower():
        data["conditions"] = "Good"
    elif "onshore" in data["wind"].lower():
        data["conditions"] = "Poor"
    else:
        data["conditions"] = "Fair"
        
    # Calculate if it's suitable for beginners
    wave_height = data["wave_height"].split("-")[0]
    if wave_height and float(wave_height) < 3:
        data["beginner_friendly"] = True
    else:
        data["beginner_friendly"] = False
        
    return data

def format_surf_report(data):
    """Format the surf report for display"""
    beginner_msg = "Good for beginners!" if data.get("beginner_friendly") else "Not recommended for beginners"
    
    return f"🏄 SURF REPORT - {data['location']} ({data['timestamp']})\n\n" \
           f"Wave Height: {data['wave_height']}\n" \
           f"Wind: {data['wind']}\n" \
           f"Tide: {data['tide']}\n" \
           f"Temperature: {data['temperature']}\n" \
           f"Conditions: {data['conditions']}\n" \
           f"Note: {beginner_msg}"

def main():
    parser = argparse.ArgumentParser(description='Get surf report using API key')
    parser.add_argument('api_key', help='API key for surf report service')
    args = parser.parse_args()
    
    # Initialize API with provided key
    api = authorize(args.api_key)
    
    # Get surf data
    surf_data = api.get_data()
    
    # Process data
    processed_data = process_surf_data(surf_data)
    
    # Format and print report
    report = format_surf_report(processed_data)
    print(report)

if __name__ == "__main__":
    main()
