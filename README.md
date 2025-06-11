# 🔮 KrystalBallZ

Krystal Ball Z is an evolving application designed to deliver a multi-agent, real-time overview of the most relevant news and developments in the field of software engineering.
Emphasis will be on MCP, RAG, and, generally, multi-agent software & development.

## 🤖 Features
- GPT-3 powered responses
- Vector-based job search with semantic similarity
- 📊 Event history tracking
- 🌐 Streamlit web interface
- Real-time job scraping and ingestion

## 🚀 Local Setup

### Prerequisites
- Python 3.8+
- OpenAI API key

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file or set the following environment variables:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export RETRIEVER_SERVICE_URL="http://localhost:8001"
export VECTOR_DB_URL="http://localhost:8002/ingest"
export CHROMA_DATA_PATH="./chroma_data"
```

### 3. Start the Services

The application requires three services to run simultaneously:

#### Terminal 1: Vector Database Service (Port 8002)
```bash
python services/vector_db_service.py
```
This service handles job data ingestion and vector storage using ChromaDB.

#### Terminal 2: Retriever Service (Port 8001)
```bash
python services/retriever_service.py
```
This service handles semantic search queries and retrieves relevant jobs from the vector database.

#### Terminal 3: Main Streamlit Application (Port 8501)
```bash
streamlit run stream_app.py
```
This is the main user interface for the application.

### 4. Verify Services
Check that all services are running:
- Vector DB Service: http://localhost:8002/health
- Retriever Service: http://localhost:8001/health
- Streamlit App: http://localhost:8501

## 🔑 Usage
1. Open the Streamlit app at http://localhost:8501
2. Enter your OpenAI API key in the sidebar
3. Use the "ingest" button to scrape and load job data into the vector database
4. Submit job search queries to get AI-powered semantic search results
5. View detailed job listings with similarity scores and metadata

## 🔄 Syncing ChromaDB Between Services

If the retriever and ingestor services show different document counts, follow these steps to synchronize them:

### Check Current Status
```bash
# Check Vector DB Service (Ingestor) count
curl http://localhost:8002/count

# Check Retriever Service count  
curl http://localhost:8001/collection/info
```

### Sync Services
1. **Stop both services** (Ctrl+C in their terminals)
2. **Delete ChromaDB data**: `rm -rf ./chroma_data`
3. **Start Vector DB Service first**: `python services/vector_db_service.py`
4. **Start Retriever Service second**: `python services/retriever_service.py`
5. **Verify sync** using the curl commands above - both should show `"total_documents": 0`

Both services should now use the same ChromaDB collection and show identical document counts.
