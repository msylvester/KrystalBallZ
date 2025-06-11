from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import asyncio
import chromadb
from openai import AsyncOpenAI
import logging
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Job Retrieval Service", version="1.0")

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5

class QueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    query: str
    total_results: int

class JobRetrieverService:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OpenAI API key not found in environment variables")
        
        self.aclient = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        
        # Initialize ChromaDB client with persistent storage
        # Use the same data directory as the vector_db_service
        chroma_data_path = os.environ.get("CHROMA_DATA_PATH", "./chroma_data")
        self.chroma_client = chromadb.PersistentClient(path=chroma_data_path)
        
        # Get or create the job_listings collection
        try:
            self.job_collection = self.chroma_client.get_collection("job_listings")
            logger.info("Connected to existing 'job_listings' collection")
        except Exception as e:
            logger.warning(f"Collection 'job_listings' not found: {e}")
            self.job_collection = None
        
        # Initialize Neo4j client
        neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "jobsearch")
        
        try:
            self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            logger.info("Connected to Neo4j for retrieval service")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")
            self.neo4j_driver = None
    
    async def create_query_embedding(self, query_text: str) -> List[float]:
        """Create embedding for the user query using OpenAI API"""
        if not self.aclient:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        
        try:
            response = await self.aclient.embeddings.create(
                input=[query_text],
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error creating query embedding: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating query embedding: {str(e)}")
    
    def query_vector_database(self, embedding: List[float], n_results: int = 5) -> Dict[str, Any]:
        """Query the ChromaDB vector database with the embedding"""
        if not self.job_collection:
            raise HTTPException(status_code=500, detail="Job collection not available")
        
        try:
            results = self.job_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            return results
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error querying vector database: {str(e)}")
    
    def expand_results_with_graph(self, vector_results: List[Dict]) -> List[Dict]:
        """Expand vector results using graph relationships"""
        if not self.neo4j_driver:
            return []
        
        expanded_jobs = []
        
        try:
            with self.neo4j_driver.session() as session:
                for result in vector_results:
                    job_id = result.get('id')
                    if not job_id:
                        continue
                    
                    # Find similar jobs through company and skills
                    similar_jobs = session.run("""
                        MATCH (c:Company)-[:HAS_JOB]->(j1:Job {id: $job_id})
                        MATCH (c)-[:HAS_JOB]->(j2:Job)
                        WHERE j1 <> j2
                        RETURN j2.id as similar_job_id, 'same_company' as reason
                        LIMIT 3
                        
                        UNION
                        
                        MATCH (j1:Job {id: $job_id})-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
                        WHERE j1 <> j2
                        RETURN j2.id as similar_job_id, 'shared_skills' as reason
                        LIMIT 3
                    """, job_id=job_id).data()
                    
                    expanded_jobs.extend(similar_jobs)
        except Exception as e:
            logger.error(f"Error expanding results with graph: {e}")
        
        return expanded_jobs

    def format_results(self, raw_results: Dict[str, Any], query: str) -> QueryResponse:
        """Format the raw ChromaDB results into a structured response"""
        formatted_results = []
        
        if raw_results.get("documents") and raw_results["documents"][0]:
            documents = raw_results["documents"][0]
            metadatas = raw_results.get("metadatas", [[]])[0]
            distances = raw_results.get("distances", [[]])[0]
            ids = raw_results.get("ids", [[]])[0]
            
            for i, doc in enumerate(documents):
                result = {
                    "id": ids[i] if i < len(ids) else f"result_{i}",
                    "document": doc,
                    "similarity_score": 1 - distances[i] if i < len(distances) else 0,  # Convert distance to similarity
                    "metadata": metadatas[i] if i < len(metadatas) else {}
                }
                formatted_results.append(result)
        
        return QueryResponse(
            results=formatted_results,
            query=query,
            total_results=len(formatted_results)
        )
    
    async def retrieve_jobs(self, query: str, n_results: int = 5) -> QueryResponse:
        """Main retrieval method that handles the full pipeline"""
        logger.info(f"Processing query: '{query}' with n_results={n_results}")
        
        # Create embedding for the query
        query_embedding = await self.create_query_embedding(query)
        
        # Query the vector database
        raw_results = self.query_vector_database(query_embedding, n_results)
        
        # Format results
        formatted_response = self.format_results(raw_results, query)
        
        # Expand with graph relationships
        if formatted_response.results:
            graph_expansions = self.expand_results_with_graph(formatted_response.results)
            
            # Add graph context to response
            if hasattr(formatted_response, '__dict__'):
                formatted_response.__dict__['graph_context'] = {
                    "related_jobs_found": len(graph_expansions),
                    "expansion_reasons": [exp.get('reason', '') for exp in graph_expansions]
                }
        
        logger.info(f"Retrieved {formatted_response.total_results} results for query")
        return formatted_response

# Initialize the service
retriever_service = JobRetrieverService()

@app.post("/retrieve", response_model=QueryResponse)
async def retrieve_jobs(request: QueryRequest):
    """
    Retrieve relevant job listings based on a user query.
    
    Takes a user query, creates an embedding, and searches the vector database
    for the most relevant job listings.
    """
    try:
        return await retriever_service.retrieve_jobs(request.query, request.n_results)
    except Exception as e:
        logger.error(f"Error in retrieve endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/retrieve", response_model=QueryResponse)
async def retrieve_jobs_get(
    query: str = Query(..., description="Search query for job listings"),
    n_results: int = Query(5, description="Number of results to return", ge=1, le=50)
):
    """
    Retrieve relevant job listings based on a user query (GET endpoint).
    
    Alternative GET endpoint for easier testing and integration.
    """
    try:
        return await retriever_service.retrieve_jobs(query, n_results)
    except Exception as e:
        logger.error(f"Error in retrieve GET endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Job Retriever Service",
        "openai_configured": retriever_service.openai_api_key is not None,
        "chromadb_connected": retriever_service.job_collection is not None
    }

@app.get("/collection/info")
def collection_info():
    """Get information about the job collection"""
    if not retriever_service.job_collection:
        raise HTTPException(status_code=500, detail="Job collection not available")
    
    try:
        count = retriever_service.job_collection.count()
        return {
            "collection_name": "job_listings",
            "total_documents": count,
            "status": "available"
        }
    except Exception as e:
        logger.error(f"Error getting collection info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting collection info: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
