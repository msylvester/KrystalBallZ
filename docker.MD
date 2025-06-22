# Docker Setup Guide

This guide explains how to build and run the AI Jobs Agent (AIJA) project using Docker Compose.

## Prerequisites

- Docker Desktop installed and running
- OpenAI API key
- Git (to clone the repository)

## Project Architecture

The application consists of 4 containerized services:

1. **Neo4j Database** (`neo4j_jobs`) - Graph database for job relationships
2. **Vector DB Service** (`vector_db_service`) - Handles job data ingestion and embeddings
3. **Retriever Service** (`retriever_service`) - Provides job search and retrieval APIs
4. **Streamlit App** (`streamlit_app`) - Web interface for the AI agent

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd KrystalBallZ
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

Replace `your_openai_api_key_here` with your actual OpenAI API key.

### 3. Build and Start Services

```bash
docker-compose up --build
```

This command will:
- Build all Docker images
- Start all services
- Create necessary volumes for data persistence

### 4. Access the Application

Once all services are running, open your browser and navigate to:

```
http://localhost:8501
```

You should see the "AI Jobs Agent (AIJA)" interface.

## Service Endpoints

- **Streamlit App**: http://localhost:8501
- **Retriever Service**: http://localhost:8001
- **Vector DB Service**: http://localhost:8002
- **Neo4j Browser**: http://localhost:7474 (username: `neo4j`, password: `jobsearch`)

## First Time Usage

### 1. Ingest Job Data

Before searching for jobs, you need to populate the database:

1. In the Streamlit app, look for the **"ingest"** button in the sidebar
2. Click it to scrape and load fresh job data
3. Wait for the ingestion process to complete

### 2. Start Searching

Once data is loaded, you can interact with the agent:

- "Find AI engineering jobs in San Francisco"
- "Show me recent machine learning positions"
- "What companies are hiring Python developers?"

## Troubleshooting

### Services Not Starting

Check service status:
```bash
docker-compose ps
```

View logs for a specific service:
```bash
docker logs <service_name>
# Examples:
docker logs streamlit_app
docker logs retriever_service
docker logs vector_db_service
```

### Port Conflicts

If you get port binding errors, check what's using the ports:
```bash
# Check port usage
lsof -i :8501  # Streamlit
lsof -i :8001  # Retriever
lsof -i :8002  # Vector DB
lsof -i :7474  # Neo4j Browser
lsof -i :7687  # Neo4j Bolt
```

### Data Persistence

Data is stored in Docker volumes:
- `neo4j_data` - Graph database data
- `neo4j_logs` - Neo4j logs
- `chroma_data` - Vector embeddings

To reset all data:
```bash
docker-compose down -v
docker-compose up --build
```

### API Key Issues

If you see OpenAI API errors:
1. Verify your API key in the `.env` file
2. Check the key is valid at https://platform.openai.com/api-keys
3. Restart the services: `docker-compose restart`

## Development

### Rebuilding After Code Changes

```bash
# Rebuild all services
docker-compose up --build

# Rebuild specific service
docker-compose build streamlit_app
docker-compose up streamlit_app
```

### Viewing Service Health

Check if services are healthy:
```bash
curl http://localhost:8001/health  # Retriever service
curl http://localhost:8002/health  # Vector DB service
```

### Database Access

Access Neo4j browser at http://localhost:7474:
- Username: `neo4j`
- Password: `jobsearch`

## Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes all data)
docker-compose down -v
```

## Common Issues

### "No job data found"
- Use the "ingest" button to load job data first
- Check that the ingestion completed successfully

### "Connection Error"
- Ensure all services are running: `docker-compose ps`
- Check service logs for errors
- Verify no port conflicts exist

### Streamlit App Not Loading
- Check if container is running: `docker ps | grep streamlit`
- View logs: `docker logs streamlit_app`
- Try accessing http://127.0.0.1:8501 instead

## Architecture Notes

- **Data Flow**: Jobs are scraped → embedded → stored in ChromaDB + Neo4j → retrieved via vector search + graph context
- **Persistence**: All data persists in Docker volumes between restarts
- **Networking**: Services communicate via Docker's internal network (`job_network`)
- **Dependencies**: Services start in correct order based on `depends_on` configuration

For more detailed information about the individual services, see the main README.md file.
