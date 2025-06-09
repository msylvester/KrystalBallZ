from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import chromadb
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Embedding Ingestion Service", version="1.0")

class JobListing(BaseModel):
    id: str
    text_preview: str
    metadata: dict

# Initialize OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None

# Initialize ChromaDB client with persistent storage
# Use the same data directory as the retriever service
chroma_data_path = os.environ.get("CHROMA_DATA_PATH", "./chroma_data")
chroma_client = chromadb.PersistentClient(path=chroma_data_path)

try:
    job_collection = chroma_client.get_collection("job_listings")
    logger.info("Connected to existing 'job_listings' collection")
except Exception:
    job_collection = chroma_client.create_collection("job_listings")
    logger.info("Created new 'job_listings' collection")

@app.post("/ingest")
async def ingest_job_listing(job: JobListing):
    """
    Ingests a vector-ready job listing, embeds the text_preview field using OpenAI embeddings,
    and stores the vector along with its metadata in a ChromaDB collection.
    """
    try:
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        logger.info(f"Processing job listing with ID: {job.id}")
        
        # Generate embedding for text_preview using the new OpenAI API
        response = openai_client.embeddings.create(
            input=job.text_preview,
            model="text-embedding-ada-002"
        )
        embedding = response.data[0].embedding

        # Add the job listing to the ChromaDB collection
        job_collection.add(
            ids=[job.id],
            embeddings=[embedding],
            documents=[job.text_preview],
            metadatas=[job.metadata]
        )
        
        logger.info(f"Successfully ingested job listing: {job.id}")
        return {"status": "success", "message": "Job listing ingested successfully"}
    except Exception as e:
        logger.error(f"Error ingesting job listing {job.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        count = job_collection.count()
        return {
            "status": "healthy",
            "service": "Job Embedding Ingestion Service",
            "openai_configured": openai_client is not None,
            "chromadb_connected": True,
            "total_documents": count
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "openai_configured": openai_client is not None,
            "chromadb_connected": False
        }
