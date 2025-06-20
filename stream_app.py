import streamlit as st
from openai import OpenAI
import os
import requests
import json
import logging
import re
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
        return self.retrieve_jobs_with_temporal(query, n_results, False, [])

    def retrieve_jobs_with_temporal(self, query, n_results=5, temporal_intent=False, temporal_keywords=None):
        """Retrieve jobs with temporal awareness"""
        try:
            params = {
                "query": query, 
                "n_results": n_results,
                "temporal_intent": temporal_intent
            }
            if temporal_keywords:
                params["temporal_keywords"] = ",".join(temporal_keywords)
                
            self.logger.info(f"Calling retriever service with query='{query}', n_results={n_results}, temporal_intent={temporal_intent}")
            response = requests.get(f"{self.retriever_url}/retrieve", params=params)
            
            if response.status_code == 200:
                data = response.json()
                total_results = data.get("total_results", 0)
                self.logger.info(f"Retrieved {total_results} jobs from vector service")
                
                if temporal_intent:
                    return f"🔍 RECENT JOBS SEARCH: Found {total_results} recent AI engineering jobs"
                else:
                    return f"🔍 VECTOR SEARCH RESULTS: Found {total_results} relevant jobs for '{query}'"
            elif response.status_code == 404:
                self.logger.warning("No job data found in collection")
                return "📭 **No Job Data Available**\n\nThe job database is currently empty. Please use the 'ingest' button in the sidebar to scrape and load fresh job data before searching."
            elif response.status_code == 500:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get("detail", "")
                except:
                    error_detail = response.text
                
                if "No job data found in collection" in error_detail:
                    self.logger.warning("Collection exists but is empty")
                    return "📭 **Job Database Empty**\n\nThe job collection exists but contains no data. Please use the 'ingest' button in the sidebar to scrape and load job listings."
                elif "Job collection not available" in error_detail:
                    self.logger.error("Job collection not available")
                    return "🚫 **Database Connection Issue**\n\nThe job collection is not available. Please check that the vector database service is running and try again."
                else:
                    self.logger.error(f"Retriever service error: {response.status_code} - {error_detail}")
                    return f"❌ **Service Error**\n\nError retrieving jobs: {error_detail}\n\nPlease try again or contact support if the issue persists."
            else:
                self.logger.error(f"Retriever service error: {response.status_code}")
                return f"❌ **Service Error**\n\nError retrieving jobs: {response.status_code} - {response.text}"
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to retriever service")
            return "🔌 **Connection Error**\n\nCannot connect to the job retrieval service. Please ensure the service is running on the expected port."
        except Exception as e:
            self.logger.error(f"Error calling retriever service: {str(e)}")
            return f"❌ **Unexpected Error**\n\nError retrieving jobs: {str(e)}"

    def _classify_query_with_confidence(self, query):
        """Classify intent with confidence scoring"""
        if not self.api_key:
            return self._fallback_intent_with_confidence(query)
        
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """
                    Classify the user's intent and provide a confidence score.
                    
                    Categories:
                    - "job_listing_request": User wants specific job listings
                    - "analytical_question": User wants job market analysis  
                    - "general_question": Other questions
                    
                    Also assess temporal intent and specificity for RAG retrieval.
                    
                    Respond in JSON format:
                    {
                        "intent": "category_name",
                        "confidence": 0.85,
                        "rag_suitable": true,
                        "temporal_intent": true,
                        "temporal_keywords": ["recent", "latest"],
                        "reasoning": "explanation"
                    }
                    
                    Temporal intent: true if query asks for recent/latest/new jobs
                    Temporal keywords: list of time-related words found
                    """},
                    {"role": "user", "content": query}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            self.logger.info(f"Intent classification: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in LLM intent classification: {e}")
            return self._fallback_intent_with_confidence(query)
    
    def _fallback_intent_with_confidence(self, query):
        """Fallback classification with confidence scoring"""
        query_lower = query.lower()
        
        # Detect temporal keywords
        temporal_keywords = ["recent", "latest", "new", "newest", "fresh", "today", "yesterday", "this week", "last week"]
        found_temporal = [kw for kw in temporal_keywords if kw in query_lower]
        has_temporal_intent = len(found_temporal) > 0
        
        # High confidence patterns
        if any(pattern in query_lower for pattern in ["find jobs", "show me jobs", "i want a job"]):
            return {
                "intent": "job_listing_request",
                "confidence": 0.9,
                "rag_suitable": True,
                "temporal_intent": has_temporal_intent,
                "temporal_keywords": found_temporal,
                "reasoning": "Clear job search request"
            }
        
        # Medium confidence patterns
        if any(word in query_lower for word in ["jobs", "positions", "openings"]):
            return {
                "intent": "job_listing_request", 
                "confidence": 0.6,
                "rag_suitable": len(query.split()) >= 3,  # Need some specificity
                "temporal_intent": has_temporal_intent,
                "temporal_keywords": found_temporal,
                "reasoning": "Contains job-related terms but may lack specificity"
            }
        
        # Low confidence - too vague
        return {
            "intent": "general_question",
            "confidence": 0.3,
            "rag_suitable": False,
            "temporal_intent": has_temporal_intent,
            "temporal_keywords": found_temporal,
            "reasoning": "Query too vague for specific retrieval"
        }
    
    def _handle_analytical_query(self, query):
        """Handle analytical questions about job market data"""
        try:
            # Try to get analytical data from retriever service
            response = requests.get(
                f"{self.retriever_url}/analyze",
                params={"query": query, "analysis_type": "location_distribution"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return self._format_analytical_response(query, data)
            else:
                # Fallback to GPT with job context
                return self._gpt_with_job_context(query)
                
        except Exception as e:
            self.logger.error(f"Error in analytical processing: {str(e)}")
            return self._gpt_with_job_context(query)
    
    def _format_analytical_response(self, query, data):
        """Format analytical response data"""
        if data.get("analysis_type") == "location_distribution":
            top_locations = data.get("top_locations", [])
            total_jobs = data.get("total_jobs", 0)
            
            if top_locations:
                response = f"📊 **Job Market Analysis:**\n\n"
                response += f"Based on {total_jobs} AI engineering jobs in our database:\n\n"
                response += f"**Top locations:**\n"
                for i, (location, count) in enumerate(top_locations[:5], 1):
                    percentage = (count / total_jobs * 100) if total_jobs > 0 else 0
                    response += f"{i}. **{location}**: {count} jobs ({percentage:.1f}%)\n"
                
                return response
            else:
                return "No location data available for analysis."
        
        return str(data)
    
    def _assess_query_quality(self, query, intent_result):
        """Assess if query is suitable for RAG retrieval"""
        
        quality_checks = {
            "length": len(query.split()) >= 2,  # At least 2 words
            "specificity": self._has_specific_terms(query),
            "clarity": intent_result["confidence"] >= 0.7,
            "rag_suitable": intent_result.get("rag_suitable", False)
        }
        
        quality_score = sum(quality_checks.values()) / len(quality_checks)
        
        return {
            "quality_score": quality_score,
            "checks": quality_checks,
            "should_use_rag": quality_score >= 0.6,
            "issues": [k for k, v in quality_checks.items() if not v]
        }

    def _has_specific_terms(self, query):
        """Check if query has specific, searchable terms"""
        specific_terms = [
            # Job types
            "engineer", "developer", "scientist", "analyst", "manager",
            # Technologies  
            "python", "javascript", "machine learning", "ai", "data",
            # Industries
            "biotech", "finance", "healthcare", "startup",
            # Locations
            "san francisco", "new york", "remote", "seattle"
        ]
        
        query_lower = query.lower()
        return any(term in query_lower for term in specific_terms)

    def _should_use_rag(self, query, intent_result):
        """Central decision point for RAG usage"""
        
        # Get quality assessment
        quality_result = self._assess_query_quality(query, intent_result)
        
        # Decision logic
        decision_factors = {
            "intent_suitable": intent_result["intent"] in ["job_listing_request", "analytical_question"],
            "confidence_high": intent_result["confidence"] >= 0.7,
            "quality_sufficient": quality_result["should_use_rag"],
            "not_too_broad": not self._is_too_broad(query),
            "has_context": self._has_searchable_context(query)
        }
        
        # Require majority of factors to be true
        use_rag = sum(decision_factors.values()) >= 3
        
        self.logger.info(f"RAG decision factors: {decision_factors}")
        self.logger.info(f"Use RAG: {use_rag}")
        
        return {
            "use_rag": use_rag,
            "factors": decision_factors,
            "quality": quality_result,
            "recommendation": self._get_recommendation(decision_factors, quality_result)
        }

    def _is_too_broad(self, query):
        """Check if query is too broad for effective RAG retrieval"""
        broad_patterns = [
            r"^(what|how|why|when|where)$",  # Single question words
            r"^(jobs|work|career)$",         # Single broad terms
            r"tell me about",                # Very open-ended
            r"everything about"
        ]
        
        query_lower = query.lower().strip()
        return any(re.match(pattern, query_lower) for pattern in broad_patterns)

    def _has_searchable_context(self, query):
        """Check if query has enough context for meaningful search"""
        context_indicators = [
            len(query.split()) >= 3,  # At least 3 words
            any(char.isupper() for char in query),  # Proper nouns/companies
            bool(re.search(r'\b(in|at|for|with|using)\b', query.lower())),  # Contextual prepositions
        ]
        
        return sum(context_indicators) >= 2

    def _get_recommendation(self, factors, quality):
        """Provide recommendation for improving query"""
        if not factors["quality_sufficient"]:
            return "Query needs more specific terms (job titles, technologies, companies, locations)"
        elif not factors["confidence_high"]:
            return "Query intent unclear - try rephrasing more directly"
        elif not factors["not_too_broad"]:
            return "Query too broad - add specific requirements"
        else:
            return "Query suitable for search"

    def _gpt_with_job_context(self, query):
        """Use GPT with job market context for analytical questions"""
        if not self.api_key:
            return "Error: OpenAI API key not set for analytical queries"
        
        try:
            # Get some job data for context
            job_response = requests.get(
                f"{self.retriever_url}/retrieve",
                params={"query": "ai engineering jobs", "n_results": 20}
            )
            
            context = ""
            if job_response.status_code == 200:
                job_data = job_response.json()
                locations = {}
                companies = {}
                
                for result in job_data.get("results", []):
                    metadata = result.get("metadata", {})
                    location = metadata.get("location", "Unknown")
                    company = metadata.get("company", "Unknown")
                    
                    locations[location] = locations.get(location, 0) + 1
                    companies[company] = companies.get(company, 0) + 1
                
                top_locations = dict(sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5])
                top_companies = dict(sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5])
                
                context = f"Current job market data - Top locations: {top_locations}, Top companies: {top_companies}"
            
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are an AI job market analyst. Answer questions about job market trends and data. Use this context: {context}"},
                    {"role": "user", "content": query}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error analyzing job market data: {str(e)}"

    def process_event(self, event):
        """Process event with uncertainty handling"""
        self.event_history.append(event)
        self.logger.info(f"Processing event: '{event}'")
        
        # Get intent with confidence
        intent_result = self._classify_query_with_confidence(event)
        
        # Decide whether to use RAG
        rag_decision = self._should_use_rag(event, intent_result)
        
        if rag_decision["use_rag"]:
            self.logger.info("✅ Using RAG retrieval")
            return self._handle_with_rag(event, intent_result)
        else:
            self.logger.info("❌ Skipping RAG - using alternative handling")
            return self._handle_without_rag(event, intent_result, rag_decision)

    def _handle_without_rag(self, query, intent_result, rag_decision):
        """Handle queries that shouldn't use RAG"""
        
        # Provide helpful guidance
        guidance = f"""
🤔 **Query Analysis:**
- Intent: {intent_result['intent']} (confidence: {intent_result['confidence']:.2f})
- Recommendation: {rag_decision['recommendation']}

**To get better job search results, try:**
- Adding specific job titles (e.g., "machine learning engineer")
- Including technologies (e.g., "Python", "AI")
- Specifying companies or industries (e.g., "at biotech companies")
- Adding location preferences (e.g., "in San Francisco")

**Example:** "Find AI engineering jobs at biology companies in San Francisco"
        """
        
        # For very general questions, still try GPT
        if intent_result["intent"] == "general_question":
            return self._fallback_to_gpt(query)
        
        return guidance

    def _handle_with_rag(self, query, intent_result):
        """Handle queries suitable for RAG"""
        if intent_result["intent"] == "job_listing_request":
            return self._process_job_search(query, intent_result)
        elif intent_result["intent"] == "analytical_question":
            return self._handle_analytical_query(query)
        else:
            return self._fallback_to_gpt(query)

    def _process_job_search(self, query, intent_result=None):
        """Process job search with RAG"""
        # Extract number of results
        num_match = re.search(r'(\d+)\s+jobs?', query.lower())
        n_results = int(num_match.group(1)) if num_match else 5
        
        # Check for temporal intent
        temporal_intent = intent_result.get("temporal_intent", False) if intent_result else False
        temporal_keywords = intent_result.get("temporal_keywords", []) if intent_result else []
        
        self.logger.info(f"Calling retriever with query='{query}', n_results={n_results}, temporal_intent={temporal_intent}")
        
        # Call retriever with temporal information
        return self.retrieve_jobs_with_temporal(query=query, n_results=n_results, temporal_intent=temporal_intent, temporal_keywords=temporal_keywords)

    def _fallback_to_gpt(self, query):
        """Fallback to GPT for general questions"""
        if not self.api_key:
            self.logger.error("OpenAI API key not set")
            return "Error: OpenAI API key not set"
        
        try:
            self.logger.info("Routing to GPT-3.5 for general question")
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": query}
                ],
                max_tokens=150,
                temperature=0.7
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
        
        # Check if this is an error response and display appropriately
        if any(error_indicator in response for error_indicator in ["📭", "🚫", "❌", "🔌"]):
            st.error(response)
        else:
            st.success(response)
        logger.info("Response displayed to user")
        
        if service_used == "Vector Retrieval Service" and not any(error_indicator in response for error_indicator in ["📭", "🚫", "❌", "🔌"]):
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
                elif retrieval_response.status_code == 404:
                    st.info("💡 **Tip:** Use the 'ingest' button in the sidebar to load job data first.")
                elif retrieval_response.status_code == 500:
                    try:
                        error_data = retrieval_response.json()
                        error_detail = error_data.get("detail", "")
                        if "No job data found" in error_detail:
                            st.info("💡 **Tip:** Use the 'ingest' button in the sidebar to scrape and load fresh job data.")
                        else:
                            st.error(f"Service error: {error_detail}")
                    except:
                        st.error(f"Failed to retrieve job listings: {retrieval_response.status_code}")
                else:
                    st.error(f"Failed to retrieve job listings: {retrieval_response.status_code}")
            except requests.exceptions.ConnectionError:
                st.error("🔌 Cannot connect to retrieval service. Please ensure it's running.")
            except Exception as e:
                st.error(f"Failed to fetch job listings: {e}")
        
        # Clear the last submitted value to prevent re-processing
        st.session_state.last_submitted = ""

if __name__ == '__main__':
    main()
