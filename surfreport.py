import argparse
from datetime import datetime

class SurfReportAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def get_data(self):
        # This would normally make an API call with the key
        # For now, just returning that we're using the API
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
