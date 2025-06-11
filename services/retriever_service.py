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
    
    def get_enhanced_graph_context(self, vector_results: List[Dict], query: str) -> Dict:
        """Get comprehensive graph context for RAG"""
        if not self.neo4j_driver:
            logger.warning("Neo4j driver not available for graph context")
            return {}
        
        context = {
            "company_insights": [],
            "skill_analysis": [],
            "market_trends": [],
            "career_paths": [],
            "location_insights": [],
            "query_analysis": {
                "has_location_intent": False,
                "has_career_intent": False,
                "has_skill_intent": False,
                "detected_keywords": []
            }
        }
        
        # Analyze query intent
        query_lower = query.lower()
        location_keywords = ["location", "remote", "san francisco", "new york", "seattle", "boston", "austin", "where"]
        career_keywords = ["senior", "junior", "career", "progression", "advancement", "level", "experience"]
        skill_keywords = ["python", "javascript", "machine learning", "ai", "skills", "technology", "programming"]
        
        context["query_analysis"]["has_location_intent"] = any(keyword in query_lower for keyword in location_keywords)
        context["query_analysis"]["has_career_intent"] = any(keyword in query_lower for keyword in career_keywords)
        context["query_analysis"]["has_skill_intent"] = any(keyword in query_lower for keyword in skill_keywords)
        context["query_analysis"]["detected_keywords"] = [kw for kw in location_keywords + career_keywords + skill_keywords if kw in query_lower]
        
        # Extract entities from vector results
        companies = list(set([r.get('metadata', {}).get('company') for r in vector_results if r.get('metadata', {}).get('company')]))
        job_ids = [r.get('id') for r in vector_results if r.get('id')]
        
        try:
            with self.neo4j_driver.session() as session:
                # 1. Company hiring patterns
                if companies:
                    logger.info(f"Analyzing {len(companies)} companies for hiring patterns")
                    company_data = session.run("""
                        MATCH (c:Company)-[:HAS_JOB]->(j:Job)
                        WHERE c.name IN $companies
                        WITH c, count(j) as job_count, collect(j.location) as locations
                        RETURN c.name as company, 
                               job_count,
                               [loc IN locations WHERE loc IS NOT NULL AND loc <> ''] as unique_locations,
                               size([loc IN locations WHERE loc CONTAINS 'Remote' OR loc CONTAINS 'remote']) as remote_count
                        ORDER BY job_count DESC
                    """, companies=companies).data()
                    context["company_insights"] = company_data
                    logger.info(f"Found insights for {len(company_data)} companies")
                
                # 2. Skill demand analysis
                skill_trends = session.run("""
                    MATCH (s:Skill)<-[:REQUIRES]-(j:Job)
                    WITH s, count(j) as demand
                    WHERE demand > 0
                    RETURN s.name as skill, demand
                    ORDER BY demand DESC LIMIT 10
                """).data()
                context["skill_analysis"] = skill_trends
                logger.info(f"Analyzed {len(skill_trends)} skills for demand trends")
                
                # 3. Location-based insights (if location intent detected)
                if context["query_analysis"]["has_location_intent"]:
                    logger.info("Location intent detected, gathering location insights")
                    location_data = session.run("""
                        MATCH (j:Job)
                        WHERE j.location IS NOT NULL AND j.location <> ''
                        WITH j.location as location, count(j) as job_count
                        WHERE job_count > 0
                        RETURN location, job_count
                        ORDER BY job_count DESC LIMIT 10
                    """).data()
                    context["location_insights"] = location_data
                    logger.info(f"Found insights for {len(location_data)} locations")
                
                # 4. Career progression paths (if career intent detected)
                if context["query_analysis"]["has_career_intent"]:
                    logger.info("Career intent detected, analyzing progression paths")
                    career_data = session.run("""
                        MATCH (j1:Job)-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
                        WHERE (j1.title CONTAINS 'Junior' OR j1.title CONTAINS 'Entry') 
                          AND (j2.title CONTAINS 'Senior' OR j2.title CONTAINS 'Lead')
                        WITH s, count(*) as connection_strength
                        WHERE connection_strength > 0
                        RETURN s.name as skill, connection_strength
                        ORDER BY connection_strength DESC LIMIT 5
                    """).data()
                    context["career_paths"] = career_data
                    logger.info(f"Found {len(career_data)} career progression skills")
                
                # 5. Market trends - overall job distribution
                market_data = session.run("""
                    MATCH (c:Company)-[:HAS_JOB]->(j:Job)
                    WITH c, count(j) as job_count
                    WHERE job_count >= 2
                    RETURN count(c) as active_companies, 
                           avg(job_count) as avg_jobs_per_company,
                           max(job_count) as max_jobs_single_company
                """).single()
                
                if market_data:
                    context["market_trends"] = {
                        "active_companies": market_data["active_companies"],
                        "avg_jobs_per_company": round(market_data["avg_jobs_per_company"], 1),
                        "max_jobs_single_company": market_data["max_jobs_single_company"]
                    }
                    logger.info("Gathered market trend data")
        
        except Exception as e:
            logger.error(f"Error gathering graph context: {e}")
            context["error"] = str(e)
        
        return context

    def expand_results_with_graph(self, vector_results: List[Dict]) -> Dict:
        """Enhanced graph expansion with detailed context"""
        if not self.neo4j_driver:
            return {"insights": [], "related_jobs": []}
        
        expanded_context = {
            "related_jobs": [],
            "company_connections": [],
            "skill_connections": [],
            "expansion_summary": {
                "total_related": 0,
                "same_company": 0,
                "shared_skills": 0
            }
        }
        
        try:
            with self.neo4j_driver.session() as session:
                for result in vector_results:
                    job_id = result.get('id')
                    if not job_id:
                        continue
                    
                    # Find related jobs through company and skills
                    related_jobs = session.run("""
                        // Same company jobs
                        MATCH (c:Company)-[:HAS_JOB]->(j1:Job {id: $job_id})
                        MATCH (c)-[:HAS_JOB]->(j2:Job)
                        WHERE j1 <> j2
                        RETURN j2.id as related_job_id, j2.title as job_title, 
                               c.name as company, 'same_company' as reason
                        LIMIT 3
                        
                        UNION
                        
                        // Shared skills jobs
                        MATCH (j1:Job {id: $job_id})-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
                        WHERE j1 <> j2
                        RETURN j2.id as related_job_id, j2.title as job_title,
                               s.name as shared_skill, 'shared_skills' as reason
                        LIMIT 3
                    """, job_id=job_id).data()
                    
                    for related in related_jobs:
                        expanded_context["related_jobs"].append(related)
                        if related["reason"] == "same_company":
                            expanded_context["expansion_summary"]["same_company"] += 1
                        elif related["reason"] == "shared_skills":
                            expanded_context["expansion_summary"]["shared_skills"] += 1
                    
                    expanded_context["expansion_summary"]["total_related"] = len(expanded_context["related_jobs"])
        
        except Exception as e:
            logger.error(f"Error expanding results with graph: {e}")
            expanded_context["error"] = str(e)
        
        return expanded_context

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
        
        # Enhanced graph expansion
        if formatted_response.results:
            # Get enhanced graph context
            enhanced_context = self.get_enhanced_graph_context(formatted_response.results, query)
            
            # Get expanded related jobs
            graph_expansions = self.expand_results_with_graph(formatted_response.results)
            
            # Add comprehensive graph context to response
            if hasattr(formatted_response, '__dict__'):
                formatted_response.__dict__['enhanced_graph_context'] = enhanced_context
                formatted_response.__dict__['graph_expansions'] = graph_expansions
                
                # Legacy compatibility
                formatted_response.__dict__['graph_context'] = {
                    "related_jobs_found": graph_expansions.get("expansion_summary", {}).get("total_related", 0),
                    "expansion_reasons": [exp.get('reason', '') for exp in graph_expansions.get("related_jobs", [])]
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
