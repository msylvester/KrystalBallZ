from datetime import datetime

class SurfReportService:
    def get_surf_report(self):
        """MCP implementation to get surf report data"""
        try:
            # Model: Get data from surf API
            surf_data = self._fetch_surf_data()
            
            # Controller: Process the data
            processed_data = self._process_surf_data(surf_data)
            
            # Processor: Format the response
            return self._format_surf_report(processed_data)
        except Exception as e:
            return f"Error getting surf report: {str(e)}"
    
    def _fetch_surf_data(self):
        """Model component: Fetch surf data from API"""
        # In a real implementation, this would call an actual surf API
        # For demonstration, returning mock data
        return {
            "location": "Malibu Beach",
            "wave_height": "3-4 ft",
            "wind": "5 mph offshore",
            "tide": "rising",
            "temperature": "72°F",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    
    def _process_surf_data(self, data):
        """Controller component: Process the surf data"""
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
    
    def _format_surf_report(self, data):
        """Processor component: Format the surf report for display"""
        beginner_msg = "Good for beginners!" if data.get("beginner_friendly") else "Not recommended for beginners"
        
        return f"🏄 SURF REPORT - {data['location']} ({data['timestamp']})\n\n" \
               f"Wave Height: {data['wave_height']}\n" \
               f"Wind: {data['wind']}\n" \
               f"Tide: {data['tide']}\n" \
               f"Temperature: {data['temperature']}\n" \
               f"Conditions: {data['conditions']}\n" \
               f"Note: {beginner_msg}"
