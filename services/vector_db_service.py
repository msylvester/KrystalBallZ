from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import chromadb
import os
import logging
from typing import List
from neo4j import GraphDatabase
from models.graph_schema import JOB_GRAPH_SCHEMA
from scraper_utils.data_processor import extract_basic_skills

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Embedding Ingestion Service", version="1.0")

class JobListing(BaseModel):
    id: str
    text_preview: str
    metadata: dict

class JobIdCheck(BaseModel):
    job_ids: List[str]

# Initialize OpenAI client
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=openai_api_key) if openai_api_key else None

# Initialize ChromaDB client with persistent storage
# Use the same data directory as the retriever service
chroma_data_path = os.environ.get("CHROMA_DATA_PATH", "./chroma_data")
logger.info(f"Vector DB Service - ChromaDB path: {os.path.abspath(chroma_data_path)}")
chroma_client = chromadb.PersistentClient(path=chroma_data_path)

try:
    job_collection = chroma_client.get_collection("job_listings")
    logger.info("Connected to existing 'job_listings' collection")
except Exception:
    job_collection = chroma_client.create_collection("job_listings")
    logger.info("Created new 'job_listings' collection")

# Initialize Neo4j client
neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
neo4j_password = os.environ.get("NEO4J_PASSWORD", "jobsearch")

try:
    neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    logger.info("Connected to Neo4j database")
    
    # Initialize graph schema
    with neo4j_driver.session() as session:
        # First, try to drop existing indexes that might conflict with constraints
        try:
            session.run("DROP INDEX ON :Job(id) IF EXISTS")
            session.run("DROP INDEX ON :Company(name) IF EXISTS") 
            session.run("DROP INDEX ON :Skill(name) IF EXISTS")
            logger.info("Dropped existing indexes to avoid constraint conflicts")
        except Exception as e:
            logger.warning(f"Could not drop existing indexes: {e}")
        
        # Now create constraints and indexes
        for query in JOB_GRAPH_SCHEMA.constraints + JOB_GRAPH_SCHEMA.indexes:
            try:
                session.run(query)
                logger.info(f"Successfully executed schema query: {query[:50]}...")
            except Exception as e:
                logger.warning(f"Schema query failed (may already exist): {e}")
    logger.info("Graph schema initialized")
    
except Exception as e:
    logger.warning(f"Neo4j connection failed: {e}")
    neo4j_driver = None

def create_job_graph_node(job_data: dict):
    """Create graph nodes for job, company, and skills"""
    if not neo4j_driver:
        logger.warning("Neo4j not available, skipping graph creation")
        return
    
    try:
        with neo4j_driver.session() as session:
            # Extract skills from job text
            skills = extract_basic_skills(job_data.get('text_preview', ''))
            
            session.run("""
                MERGE (j:Job {id: $id})
                SET j.title = $title, j.location = $location
            
                MERGE (c:Company {name: $company})
                MERGE (c)-[:HAS_JOB]->(j)
            
                WITH j
                UNWIND $skills as skill_name
                MERGE (s:Skill {name: skill_name})
                MERGE (j)-[:REQUIRES]->(s)
            """, 
            id=job_data['id'],
            title=job_data.get('title', ''),
            company=job_data.get('company', ''),
            location=job_data.get('location', ''),
            skills=skills
            )
            logger.info(f"Created graph nodes for job {job_data['id']}")
    except Exception as e:
        logger.error(f"Error creating graph nodes: {e}")

@app.post("/ingest")
async def ingest_job_listing(job: JobListing):
    """
    Ingests a vector-ready job listing, embeds the text_preview field using OpenAI embeddings,
    and stores the vector along with its metadata in a ChromaDB collection.
    Also creates corresponding graph nodes in Neo4j.
    """
    try:
        # Check if job already exists
        try:
            existing_results = job_collection.get(ids=[job.id])
            if existing_results['ids']:
                logger.info(f"Job {job.id} already exists in database, skipping")
                return {
                    "status": "skipped", 
                    "message": f"Job {job.id} already exists",
                    "job_id": job.id
                }
        except Exception as e:
            logger.warning(f"Error checking for existing job {job.id}: {e}")
        
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
        
        # Create graph nodes in Neo4j
        graph_data = {
            'id': job.id,
            'title': job.metadata.get('title', ''),
            'company': job.metadata.get('company', ''),
            'location': job.metadata.get('location', ''),
            'text_preview': job.text_preview
        }
        create_job_graph_node(graph_data)
        
        logger.info(f"Successfully ingested job listing: {job.id}")
        return {"status": "success", "message": "Job listing ingested to vector + graph", "job_id": job.id}
    except Exception as e:
        logger.error(f"Error ingesting job listing {job.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/batch")
async def ingest_job_batch(jobs: List[JobListing]):
    """Batch ingest multiple jobs with duplicate checking"""
    results = {
        "total_jobs": len(jobs),
        "new_jobs": 0,
        "skipped_jobs": 0,
        "failed_jobs": 0,
        "details": []
    }
    
    for job in jobs:
        try:
            result = await ingest_job_listing(job)
            if result["status"] == "success":
                results["new_jobs"] += 1
            elif result["status"] == "skipped":
                results["skipped_jobs"] += 1
            results["details"].append(result)
        except Exception as e:
            results["failed_jobs"] += 1
            results["details"].append({
                "status": "failed",
                "job_id": job.id,
                "error": str(e)
            })
    
    logger.info(f"Batch ingestion complete: {results['new_jobs']} new, {results['skipped_jobs']} skipped, {results['failed_jobs']} failed")
    return results

@app.post("/check_existing")
def check_existing_jobs(request: JobIdCheck):
    """Check which job IDs already exist in the database"""
    try:
        existing_results = job_collection.get(ids=request.job_ids)
        existing_ids = existing_results['ids']
        return {
            "total_checked": len(request.job_ids),
            "existing_count": len(existing_ids),
            "existing_ids": existing_ids
        }
    except Exception as e:
        logger.error(f"Error checking existing jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/count")
def get_collection_count():
    """Get the total number of documents in the job_listings collection"""
    try:
        count = job_collection.count()
        return {"total_documents": count}
    except Exception as e:
        logger.error(f"Error getting collection count: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting collection count: {str(e)}")

@app.delete("/clear")
def clear_collection():
    """Clear all documents from the job_listings collection"""
    try:
        global job_collection
        # Delete the existing collection
        chroma_client.delete_collection("job_listings")
        # Recreate it
        job_collection = chroma_client.create_collection("job_listings")
        logger.info("Successfully cleared job_listings collection")
        return {"status": "success", "message": "Collection cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing collection: {str(e)}")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
