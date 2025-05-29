import streamlit as st
from openai import OpenAI
import os
import requests
import json
from datetime import datetime

class Agent:
    def __init__(self):
        self.event_history = []
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.tools = {
            "surf_report": self.get_surf_report
        }
    
    def process_event(self, event):
        """Process an incoming event using GPT-3.5 and return a response"""
        self.event_history.append(event)
        
        if not self.api_key:
            return "Error: OpenAI API key not set"
        
        # Check if this is a tool request
        if "surf report" in event.lower():
            return self.tools["surf_report"]()
        
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": event}
                ],
                max_tokens=150,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            ai_response = response.choices[0].message.content.strip()
            return ai_response
        except Exception as e:
            return f"Error processing with GPT-3.5: {str(e)}"
            
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
    
    def get_event_history(self):
        return self.event_history

def main():
    st.title("GPT-3.5 Powered Agent App")

    if 'agent' not in st.session_state:
        st.session_state.agent = Agent()
    
    api_key = st.sidebar.text_input(
        "OpenAI API Key", 
        value=st.session_state.agent.api_key, 
        type="password"
    )
    if api_key:
        st.session_state.agent.api_key = api_key

    if st.session_state.agent.get_event_history():
        st.subheader("Event History")
        for i, event in enumerate(st.session_state.agent.get_event_history()):
            st.text(f"{i + 1}. {event}")

    user_input = st.text_input("Enter event data", "")
    if st.button("Submit Event"):
        if user_input:
            response = st.session_state.agent.process_event(user_input)
            st.success(response)
        else:
            st.warning("Please enter event data")

if __name__ == '__main__':
    main()
