class SurfReportAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        
    def get_data(self):
        # This would normally make an API call with the key
        # For now, just returning that we're using the API
        return {
            "api_key_used": self.api_key,
            "status": "authorized"
        }

def authorize(api_key):
    """Authorize with the surf report API"""
    return SurfReportAPI(api_key)
