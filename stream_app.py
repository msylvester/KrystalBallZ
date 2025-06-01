import streamlit as st
from openai import OpenAI
import os
import requests
import json
import logging
from datetime import datetime
from country_report import CountryReportAPI, authorize, process_country_data, format_country_report
from job_service import AIJobSearchService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("agent_app")

class Agent:
    def __init__(self):
        self.event_history = []
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.country_service = CountryReportAPI()
        self.job_service = AIJobSearchService()
        self.tools = {
            "country_report": self.country_service.get_data,
            "ai_jobs": self.job_service.get_ai_jobs
        }
        self.logger = logging.getLogger("agent_app.Agent")
    
    def process_event(self, event):
        """Process an incoming event using GPT-3.5 and return a response"""
        self.event_history.append(event)
        self.logger.info(f"Processing event: '{event}'")
        
        if not self.api_key:
            self.logger.error("OpenAI API key not set")
            return "Error: OpenAI API key not set"
        
        # Check if this is a tool request
        if "country" in event.lower() or "nation" in event.lower():
            self.logger.info("Routing to country report service")
            
            # Extract region if provided
            region = None
            if "in " in event.lower():
                region_parts = event.lower().split("in ")
                if len(region_parts) > 1:
                    region = region_parts[1].strip()
                    self.logger.info(f"Extracted region: '{region}'")
            
            return self.tools["country_report"](region=region)
        elif "ai jobs" in event.lower() or "job search" in event.lower():
            self.logger.info("Routing to AI job search service")
            
            # Extract location if provided
            location = ""
            if "in " in event.lower():
                location_parts = event.lower().split("in ")
                if len(location_parts) > 1:
                    location = location_parts[1].strip()
                    self.logger.info(f"Extracted location: '{location}'")
            
            # Special handling for San Francisco
            if "san francisco" in event.lower() or (location and "san francisco" in location.lower()):
                self.logger.info("Detected request for San Francisco jobs")
                location = "San Francisco, CA"
            
            # Default limit is 5, but can be customized
            limit = 5
            if "show" in event.lower() and "jobs" in event.lower():
                # Try to extract a number
                import re
                num_match = re.search(r'show (\d+) jobs', event.lower())
                if num_match:
                    limit = int(num_match.group(1))
                    self.logger.info(f"Extracted job limit: {limit}")
            
            self.logger.info(f"Calling job service with location='{location}', limit={limit}")
            return self.tools["ai_jobs"](location=location, limit=limit)
        
        try:
            self.logger.info("Routing to GPT-3.5")
            client = OpenAI(api_key=self.api_key)
            
            self.logger.info("Sending request to OpenAI API")
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
            self.logger.info(f"Received response from GPT-3.5 ({len(ai_response)} chars)")
            return ai_response
        except Exception as e:
            self.logger.error(f"Error processing with GPT-3.5: {str(e)}")
            return f"Error processing with GPT-3.5: {str(e)}"
    
    def get_event_history(self):
        return self.event_history

# Custom log handler class - moved outside main() for better organization
class StreamlitLogHandler(logging.Handler):
    def emit(self, record):
        # Defensive check - initialize if not exists
        if 'log_messages' not in st.session_state:
            st.session_state.log_messages = []
        
        log_entry = self.format(record)
        if len(st.session_state.log_messages) > 100:  # Limit to last 100 logs
            st.session_state.log_messages.pop(0)
        st.session_state.log_messages.append(log_entry)

def main():
    st.title("GPT-3.5 Powered Agent App")

    # Initialize session state variables FIRST - before creating any objects
    if 'show_logs' not in st.session_state:
        st.session_state.show_logs = False
    
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = []
    
    # Add the custom log handler early, before creating Agent
    if not any(isinstance(h, StreamlitLogHandler) for h in logging.getLogger().handlers):
        streamlit_handler = StreamlitLogHandler()
        streamlit_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(streamlit_handler)
        logger.info("Streamlit log handler added")

    # NOW initialize the agent (after log_messages is ready)
    if 'agent' not in st.session_state:
        st.session_state.agent = Agent()
        logger.info("Agent initialized in session state")
    
    # Sidebar controls
    api_key = st.sidebar.text_input(
        "OpenAI API Key", 
        value=st.session_state.agent.api_key, 
        type="password"
    )
    if api_key:
        st.session_state.agent.api_key = api_key
        logger.info("API key updated")
    
    # Add log viewer toggle in sidebar
    st.sidebar.divider()
    st.sidebar.subheader("Debug Options")
    show_logs = st.sidebar.checkbox("Show Debug Logs", value=st.session_state.show_logs)
    if show_logs != st.session_state.show_logs:
        st.session_state.show_logs = show_logs
        if show_logs:
            logger.info("Debug logs enabled in UI")
        else:
            logger.info("Debug logs disabled in UI")

    # Display event history
    if st.session_state.agent.get_event_history():
        st.subheader("Event History")
        for i, event in enumerate(st.session_state.agent.get_event_history()):
            st.text(f"{i + 1}. {event}")
    
    # Display logs if enabled
    if st.session_state.show_logs and st.session_state.log_messages:
        st.subheader("Debug Logs")
        log_container = st.container(height=300)
        with log_container:
            for log in st.session_state.log_messages:
                st.text(log)

    # User input section
    user_input = st.text_input("Enter event data", key="user_input_field")
    
    # Use a unique key for the button to ensure it refreshes properly
    if st.button("Submit Event", key="submit_event_button"):
        print(f'here we are')
        if user_input:

            logger.info(f"User submitted: '{user_input}'")
            response = st.session_state.agent.process_event(user_input)
            
            # Determine which service was used
            service_used = None
            if "AI ENGINEERING JOBS REPORT" in response:
                service_used = "AI Job Search Service"
                logger.info("Response identified as coming from AI Job Search Service")
            elif "COUNTRY REPORT" in response:
                service_used = "Country Report Service"
                logger.info("Response identified as coming from Country Report Service")
            else:
                logger.info("Response identified as coming from GPT-3.5")
            
            # Display the response with service indicator if applicable
            if service_used:
                st.markdown(f"<div style='background-color: #e6f3ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>🔧 Using {service_used}</strong></div>", unsafe_allow_html=True)
            
            st.success(response)
            logger.info("Response displayed to user")
            
            # We can't directly modify session state after the button is clicked
            # The field will be cleared on the next rerun automatically
        else:
            st.warning("Please enter event data")
            logger.warning("User attempted to submit empty input")

if __name__ == '__main__':
    main()
