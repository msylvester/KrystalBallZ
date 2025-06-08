from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import chromadb
import os

app = FastAPI(title="Job Embedding Ingestion Service", version="1.0")

class JobListing(BaseModel):
    id: str
    text_preview: str
    metadata: dict

# Initialize OpenAI API key from environment
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Initialize ChromaDB client and collection
chroma_client = chromadb.Client()

try:
    job_collection = chroma_client.get_collection("job_listings")
except Exception:
    job_collection = chroma_client.create_collection("job_listings")

@app.post("/ingest")
async def ingest_job_listing(job: JobListing):
    """
    Ingests a vector-ready job listing, embeds the text_preview field using OpenAI embeddings,
    and stores the vector along with its metadata in a ChromaDB collection.
    """
    try:
        # Generate embedding for text_preview using the new OpenAI API
        from openai.embeddings_utils import get_embedding
        embedding = get_embedding(job.text_preview, engine="text-embedding-ada-002")

        # Add the job listing to the ChromaDB collection
        job_collection.add(
            ids=[job.id],
            embeddings=[embedding],
            documents=[job.text_preview],
            metadatas=[job.metadata]
        )
        return {"status": "success", "message": "Job listing ingested successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
