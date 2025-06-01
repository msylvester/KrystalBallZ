# 🔮 KrystalBallZ

Krystal Ball Z is an evolving application designed to deliver a multi-agent, real-time overview of the most relevant news and developments in the field of software engineering.
Emphasis will be on MCP, RAG, and, generally, multi-agent software & development. 

## 🤖 Features
- GPT-3 powered responses
- 📊 Event history tracking
- 🌐 Streamlit web interface

## 🚀 Getting Started
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## 🧪 Running Tests

There are unit tests 🥳 to verify that the integration of API calls and the chatbot works seamlessly.

### 🔹 Agent Integration Tests

Run with:

```bash
pytest test_agent_integration.py -v
```

Tests included:

- `test_agent_initialization`
- `test_agent_country_query_integration`
- `test_agent_country_with_region_integration`
- `test_agent_job_search_integration`
- `test_agent_job_search_with_location_integration`
- `test_agent_san_francisco_jobs_integration`
- `test_agent_job_search_with_limit_integration`
- `test_agent_no_api_key_error`
- `test_agent_multiple_events_history`
- `test_agent_case_insensitive_routing`
- `test_agent_tools_accessibility`
- `test_agent_logging_integration`
- `test_agent_routing_logic`

### 🔹 Country Report Tests

Run with:

```bash
pytest test_country_report.py -v
```

Tests included:

- `test_api_authorization`
- `test_api_get_data_real_request`
- `test_api_get_data_with_region`
- `test_api_with_invalid_region`
- `test_process_country_data`
- `test_format_country_report`
```


3. Run the application:
   ```
   streamlit run stream_app.py
   ```

## 🔑 Usage
- Enter your OpenAI API key in the sidebar
- Submit events to get AI-powered insights
- View your event history in the app

## 🛠️ Technologies
- OpenAI GPT-3
- Streamlit
- Python

## Contributors 
- **ashruidan** [https://github.com/ashruidan]
- **krystal_mess323**: [twitch.tv/krystal_mess323](https://www.twitch.tv/krystal_mess323)
