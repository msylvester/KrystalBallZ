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

## 🚀 Usage

2. Run the application:
   ```bash
   streamlit run stream_app.py
   ```

## 🔑 Usage
- Enter your OpenAI API key in the sidebar
- Submit events to get AI-powered insights
- View your event history in the app

## 📊 Data Processing Pipeline for Vector Database Ingestion

### Overview
This document demonstrates the data transformation process from raw scraped job data to vector database-ready format.

### Pipeline Stages

#### Stage 1: Raw Scraped Data
- Direct output from web scraping
- Inconsistent formatting
- May contain duplicates
- Minimal validation

#### Stage 2: Standardized Data
- Cleaned and normalized text
- Extracted metadata (tech stack, experience level)
- Consistent field names and formats
- Quality validation applied

#### Stage 3: Vector-Ready Format
- Optimized text for embedding
- Structured metadata for filtering
- Unique IDs for deduplication
- Ready for vector database insertion


### File Outputs
- `raw_jobs_*.json` - Original scraped data
- `processed_jobs_*.json` - Cleaned and standardized
- `vector_ready_jobs_*.json` - Optimized for embedding
- `jobs_with_embeddings.json` - Final format (when ready)

### Running the Data Pipeline Demo
```bash
python data_format_demo.py
```

This will show the complete data transformation pipeline with sample data.

## 🛠️ Technologies
- OpenAI GPT-3
- Streamlit
- Python

## 👥 Contributors 
- **ashruidan** - [https://github.com/ashruidan](https://github.com/ashruidan)
- **krystal_mess323** - [twitch.tv/krystal_mess323](https://www.twitch.tv/krystal_mess323)
