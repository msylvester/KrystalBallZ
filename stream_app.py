import streamlit as st
from openai import OpenAI
import os
import requests
import json
import logging
from datetime import datetime
from ai_job_service import AIJobSearchService

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
        jooble_api_key = os.environ.get("JOOBLE_API_KEY", "")
        self.job_service = AIJobSearchService(api_key=jooble_api_key)
        self.tools = {
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
        if "ai jobs" in event.lower() or "job search" in event.lower() or "jobs" in event.lower():
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

    # Initialize session state for form submission if not exists
    if 'last_submitted' not in st.session_state:
        st.session_state.last_submitted = ""
    
    # Create a form for more reliable input handling
    with st.form(key="input_form", clear_on_submit=True):
        user_input = st.text_input("Enter event data", key="user_input_field")
        submit_button = st.form_submit_button("Submit Event")
        
        if submit_button and user_input:
            # Store the input in session state to process after form submission
            st.session_state.last_submitted = user_input
    
    # Process the submission outside the form
    if st.session_state.last_submitted:
        current_input = st.session_state.last_submitted
        logger.info(f"Processing submission: '{current_input}'")
        
        # Get response from agent
        response = st.session_state.agent.process_event(current_input)
        
        # Determine which service was used
        service_used = None
        if "AI ENGINEERING JOBS REPORT" in response:
            service_used = "AI Job Search Service"
            logger.info("Response identified as coming from AI Job Search Service")
        else:
            logger.info("Response identified as coming from GPT-3.5")
        
        # Display the response with service indicator if applicable
        if service_used:
            st.markdown(f"<div style='background-color: #e6f3ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>🔧 Using {service_used}</strong></div>", unsafe_allow_html=True)
        
        st.success(response)
        logger.info("Response displayed to user")
        
        # Clear the last submitted value to prevent re-processing
        st.session_state.last_submitted = ""

if __name__ == '__main__':
    main()
