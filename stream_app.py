import streamlit as st
from openai import OpenAI
import os
import requests
import json
import logging
from datetime import datetime

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
        self.retriever_url = os.environ.get("RETRIEVER_SERVICE_URL", "http://localhost:8001")
        self.tools = {
            "retrieve_jobs": self.retrieve_jobs
        }
        self.logger = logging.getLogger("agent_app.Agent")
    
    def retrieve_jobs(self, query, n_results=5):
        """Retrieve jobs using the vector retrieval service"""
        try:
            self.logger.info(f"Calling retriever service with query='{query}', n_results={n_results}")
            response = requests.get(
                f"{self.retriever_url}/retrieve",
                params={"query": query, "n_results": n_results}
            )
            
            if response.status_code == 200:
                data = response.json()
                total_results = data.get("total_results", 0)
                self.logger.info(f"Retrieved {total_results} jobs from vector service")
                return f"🔍 VECTOR SEARCH RESULTS: Found {total_results} relevant jobs for '{query}'"
            else:
                self.logger.error(f"Retriever service error: {response.status_code}")
                return f"Error retrieving jobs: {response.status_code} - {response.text}"
        except Exception as e:
            self.logger.error(f"Error calling retriever service: {str(e)}")
            return f"Error retrieving jobs: {str(e)}"

    def process_event(self, event):
        """Process an incoming event using vector retrieval or GPT-3.5"""
        self.event_history.append(event)
        self.logger.info(f"Processing event: '{event}'")
        
        # Check if this is a job search request
        if any(keyword in event.lower() for keyword in ["jobs", "job search", "find", "search", "looking for"]) and any(job_term in event.lower() for job_term in ["job", "position", "role", "career"]):
            self.logger.info("Routing to vector retrieval service")
            
            # Extract number of results
            import re
            num_match = re.search(r'(\d+)\s+jobs?', event.lower())
            n_results = int(num_match.group(1)) if num_match else 5
            
            self.logger.info(f"Calling retriever with query='{event}', n_results={n_results}")
            return self.tools["retrieve_jobs"](query=event, n_results=n_results)
        
        # Fall back to GPT-3.5 for non-job queries
        if not self.api_key:
            self.logger.error("OpenAI API key not set")
            return "Error: OpenAI API key not set"
        
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
    st.title("AI Jobs Agent (AIJA)")

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
    if st.sidebar.button("ingest"):
         from scraper_utils.job_scraper_linkedin_guest import scrape_ai_jobs_for_rag
         
         with st.sidebar:
             with st.spinner("Scraping jobs..."):
                 jobs = scrape_ai_jobs_for_rag()
             
             st.info(f"Scraped {len(jobs)} jobs, checking for duplicates...")
             
             # Use batch ingestion endpoint
             vector_ingest_url = os.environ.get("VECTOR_DB_URL", "http://localhost:8002/ingest/batch")
             
             payload = []
             for job in jobs:
                 payload.append({
                     "id": job["id"],
                     "text_preview": job["text"],
                     "metadata": job["metadata"]
                 })
             
             with st.spinner("Ingesting new jobs..."):
                 response = requests.post(vector_ingest_url, json=payload)
             
             if response.status_code == 200:
                 result = response.json()
                 st.success(f"✅ Ingestion Complete!")
                 st.info(f"📊 **Results:**")
                 st.info(f"• **New jobs added:** {result['new_jobs']}")
                 st.info(f"• **Duplicates skipped:** {result['skipped_jobs']}")
                 st.info(f"• **Failed:** {result['failed_jobs']}")
                 st.info(f"• **Total processed:** {result['total_jobs']}")
                 
                 if result['new_jobs'] > 0:
                     st.balloons()
             else:
                 st.error(f"❌ Ingestion failed: {response.status_code}")
                 st.error(response.text)
         
         # Show sample of vector-ready job from scraped data
         if jobs:
             st.sidebar.subheader("Sample Vector-Ready Job:")
             sample_job = jobs[0]
             st.sidebar.json({
                 "id": sample_job["id"],
                 "text_preview": sample_job["text"][:200] + "...",
                 "metadata_keys": list(sample_job["metadata"].keys())
             })
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
        if "VECTOR SEARCH RESULTS" in response:
            service_used = "Vector Retrieval Service"
            logger.info("Response identified as coming from Vector Retrieval Service")
        else:
            logger.info("Response identified as coming from GPT-3.5")
        
        # Display the response with service indicator if applicable
        if service_used:
            st.markdown(f"<div style='background-color: #e6f3ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;'><strong>🔧 Using {service_used}</strong></div>", unsafe_allow_html=True)
        
        st.success(response)
        logger.info("Response displayed to user")
        
        if service_used == "Vector Retrieval Service":
            import re
            num_match = re.search(r'(\d+)\s+jobs?', current_input.lower())
            n_results = int(num_match.group(1)) if num_match else 5
            
            try:
                retriever_url = st.session_state.agent.retriever_url
                retrieval_response = requests.get(
                    f"{retriever_url}/retrieve",
                    params={"query": current_input, "n_results": n_results}
                )
                
                if retrieval_response.status_code == 200:
                    retrieval_data = retrieval_response.json()
                    results = retrieval_data.get("results", [])
                    
                    if results:
                        st.subheader("Retrieved Job Listings")
                        
                        # Summary table
                        summary_data = []
                        for i, result in enumerate(results):
                            metadata = result.get("metadata", {})
                            summary_data.append({
                                "Rank": i + 1,
                                "Title": metadata.get("title", "N/A"),
                                "Company": metadata.get("company", "N/A"),
                                "Location": metadata.get("location", "N/A"),
                                "Posted": metadata.get("posted_date", "N/A"),
                                "Similarity": f"{result.get('similarity_score', 0):.3f}"
                            })
                        
                        st.table(summary_data)
                        # Graph context display
                        if retrieval_data.get("graph_context"):
                            st.subheader("🕸️ Related Opportunities")
                            graph_ctx = retrieval_data["graph_context"]
                            
                            if graph_ctx.get("total_related", 0) > 0:
                                st.info(f"Found {graph_ctx['total_related']} related jobs through company connections and shared skills")
                                
                                with st.expander("View Related Jobs"):
                                    st.write("**Related opportunities found through graph connections:**")
                                    
                                    # Display the actual related jobs
                                    related_jobs = graph_ctx.get("related_jobs", [])
                                    if related_jobs:
                                        for i, job in enumerate(related_jobs, 1):
                                            job_title = job.get("title", "Unknown Title")
                                            company = job.get("company", "Unknown Company")
                                            job_id = job.get("job_id", "")
                                            st.write(f"**{i}.** {job_title} at {company}")
                                            if job_id:
                                                st.write(f"   *Job ID: {job_id}*")
                                    else:
                                        st.write("No related job details available")
                                    
                                    # Show expansion reasons
                                    st.write("\n**Connection types:**")
                                    for reason in set(graph_ctx.get("expansion_reasons", [])):
                                        if reason == "same_company":
                                            st.write("• Jobs at the same companies")
                                        elif reason == "shared_skills":
                                            st.write("• Jobs requiring similar skills")
                            else:
                                st.info("No related jobs found in company/skill network")
                        
                        # Detailed results
                        st.subheader("Detailed Results")
                        for i, result in enumerate(results):
                            metadata = result.get("metadata", {})
                            with st.expander(f"Job {i+1}: {metadata.get('title', 'Unknown')} at {metadata.get('company', 'Unknown')}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.write("**Job Details:**")
                                    st.write(f"**Title:** {metadata.get('title', 'N/A')}")
                                    st.write(f"**Company:** {metadata.get('company', 'N/A')}")
                                    st.write(f"**Location:** {metadata.get('location', 'N/A')}")
                                    st.write(f"**Posted Date:** {metadata.get('posted_date', 'N/A')}")
                                    st.write(f"**Experience Level:** {metadata.get('experience_level', 'N/A')}")
                                    st.write(f"**Employment Type:** {metadata.get('employment_type', 'N/A')}")
                                
                                with col2:
                                    st.write("**Additional Info:**")
                                    st.write(f"**Remote Friendly:** {metadata.get('remote_friendly', 'N/A')}")
                                    st.write(f"**Salary Range:** {metadata.get('salary_range', 'N/A')}")
                                    st.write(f"**Tech Stack:** {metadata.get('tech_stack', 'N/A')}")
                                    st.write(f"**Similarity Score:** {result.get('similarity_score', 0):.3f}")
                                
                                if metadata.get('apply_link'):
                                    st.write(f"**Apply Link:** {metadata.get('apply_link')}")
                                
                                # Show document preview
                                document = result.get("document", "")
                                if document:
                                    st.write("**Job Description Preview:**")
                                    st.text_area("", document[:500] + "..." if len(document) > 500 else document, height=100, key=f"doc_{i}")
                    else:
                        st.info("No job listings found for your query.")
                else:
                    st.error(f"Failed to retrieve job listings: {retrieval_response.status_code}")
            except Exception as e:
                st.error(f"Failed to fetch job listings: {e}")
        
        # Clear the last submitted value to prevent re-processing
        st.session_state.last_submitted = ""

if __name__ == '__main__':
    main()
