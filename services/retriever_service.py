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
    graph_context: Optional[Dict[str, Any]] = None

class JobRetrieverService:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OpenAI API key not found in environment variables")
        
        self.aclient = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        
        # Initialize ChromaDB client with persistent storage
        # Use the same data directory as the vector_db_service
        chroma_data_path = os.environ.get("CHROMA_DATA_PATH", "./chroma_data")
        logger.info(f"Retriever Service - ChromaDB path: {os.path.abspath(chroma_data_path)}")
        self.chroma_client = chromadb.PersistentClient(path=chroma_data_path)
        
        # Get or create the job_listings collection
        try:
            self.job_collection = self.chroma_client.get_collection("job_listings")
            logger.info("Connected to existing 'job_listings' collection")
        except Exception as e:
            logger.warning(f"Collection 'job_listings' not found: {e}")
            try:
                # Try to create the collection if it doesn't exist
                self.job_collection = self.chroma_client.create_collection("job_listings")
                logger.info("Created new 'job_listings' collection")
            except Exception as create_error:
                logger.error(f"Failed to create collection: {create_error}")
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
    @app.get("/debug/chroma")
    def debug_chroma_connection():
        """Debug ChromaDB connection details"""
        try:
            # Check the actual path being used
            chroma_data_path = os.environ.get("CHROMA_DATA_PATH", "./chroma_data")

            # List all collections
            collections = retriever_service.chroma_client.list_collections()
            collection_names = [col.name for col in collections]

            # Try to get collection info
            collection_info = None
            if retriever_service.job_collection:
                collection_info = {
                    "name": retriever_service.job_collection.name,
                    "count": retriever_service.job_collection.count()
                }

            return {
                "chroma_data_path": chroma_data_path,
                "collections_found": collection_names,
                "job_collection_status": collection_info,
                "client_type": str(type(retriever_service.chroma_client))
            }
        except Exception as e:
            return {"error": str(e)}
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
            raise HTTPException(status_code=500, detail="Job collection not available. Please ingest some job data first.")
        
        try:
            # Check if collection has any data
            count = self.job_collection.count()
            if count == 0:
                raise HTTPException(status_code=404, detail="No job data found in collection. Please ingest some job data first.")
            
            results = self.job_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            return results
        except HTTPException:
            raise
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
        """Bare minimum graph expansion - find related jobs by company"""
        logger.info(f"🕸️ GRAPH EXPANSION: Starting graph expansion for {len(vector_results)} vector results")
        
        if not self.neo4j_driver:
            logger.warning("🕸️ GRAPH EXPANSION: Neo4j driver not available - skipping graph expansion")
            return {"related_jobs": [], "total_related": 0, "expansion_reasons": []}
        
        related_jobs = []
        expansion_reasons = []
        
        try:
            with self.neo4j_driver.session() as session:
                logger.info("🕸️ GRAPH EXPANSION: Connected to Neo4j session")
                
                for i, result in enumerate(vector_results):
                    job_id = result.get('id')
                    if not job_id:
                        logger.warning(f"🕸️ GRAPH EXPANSION: Result {i} has no job_id, skipping")
                        continue
                    
                    logger.info(f"🕸️ GRAPH EXPANSION: Processing job_id: {job_id}")
                    logger.info(f"🕸️ GRAPH EXPANSION: Attempting query with job_id: '{job_id}'")
                    
                    # Find other jobs at the same company
                    same_company_jobs = session.run("""
                        MATCH (c:Company)-[:HAS_JOB]->(j1:Job {id: $job_id})
                        MATCH (c)-[:HAS_JOB]->(j2:Job)
                        WHERE j1 <> j2
                        RETURN j2.id as job_id, j2.title as title, c.name as company
                        LIMIT 2
                    """, job_id=job_id).data()
                    
                    if same_company_jobs:
                        logger.info(f"🕸️ GRAPH EXPANSION: Found {len(same_company_jobs)} related jobs for {job_id}")
                        related_jobs.extend(same_company_jobs)
                        expansion_reasons.append("same_company")
                        for job in same_company_jobs:
                            logger.info(f"🕸️ GRAPH EXPANSION: Related job - {job['title']} at {job['company']}")
                    else:
                        logger.info(f"🕸️ GRAPH EXPANSION: No related jobs found for {job_id}")
        
        except Exception as e:
            logger.error(f"🕸️ GRAPH EXPANSION: Error expanding results with graph: {e}")
            return {"related_jobs": [], "total_related": 0, "expansion_reasons": [], "error": str(e)}
        
        logger.info(f"🕸️ GRAPH EXPANSION: Completed - found {len(related_jobs)} total related jobs")
        return {
            "related_jobs": related_jobs,
            "total_related": len(related_jobs),
            "expansion_reasons": expansion_reasons
        }

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
        
        # Add graph context for enhanced results
        logger.info(f"🕸️ GRAPH CONTEXT: Checking if graph expansion should be performed")
        logger.info(f"🕸️ GRAPH CONTEXT: formatted_response.results count: {len(formatted_response.results)}")
        logger.info(f"🕸️ GRAPH CONTEXT: neo4j_driver available: {self.neo4j_driver is not None}")
        
        if formatted_response.results and self.neo4j_driver:
            logger.info("🕸️ GRAPH CONTEXT: Conditions met - performing graph expansion")
            # Get basic graph expansion (related jobs by company)
            graph_expansions = self.expand_results_with_graph(formatted_response.results)
            
            # Add graph context to response
            formatted_response.graph_context = {
                "related_jobs": graph_expansions.get("related_jobs", []),
                "related_jobs_found": graph_expansions.get("total_related", 0),  # UI expects this key
                "total_related": graph_expansions.get("total_related", 0),
                "expansion_reasons": graph_expansions.get("expansion_reasons", []),
                "graph_available": True
            }
            logger.info(f"🕸️ GRAPH CONTEXT: Added graph context with {graph_expansions.get('total_related', 0)} related jobs")
        else:
            logger.info("🕸️ GRAPH CONTEXT: Conditions not met - skipping graph expansion")
            if not formatted_response.results:
                logger.info("🕸️ GRAPH CONTEXT: No vector results to expand")
            if not self.neo4j_driver:
                logger.info("🕸️ GRAPH CONTEXT: Neo4j driver not available")
            
            formatted_response.graph_context = {
                "related_jobs": [],
                "related_jobs_found": 0,  # UI expects this key
                "total_related": 0,
                "expansion_reasons": [],
                "graph_available": False
            }
        
        logger.info(f"Retrieved {formatted_response.total_results} results for query")
        return formatted_response
    
    async def analyze_location_distribution(self):
        """Analyze job distribution by location"""
        if not self.job_collection:
            raise HTTPException(status_code=500, detail="No job data available")
        
        try:
            # Get all job metadata
            all_results = self.job_collection.get(include=["metadatas"])
            locations = {}
            
            for metadata in all_results.get("metadatas", []):
                location = metadata.get("location", "Unknown")
                # Clean up location names
                if "San Francisco" in location or "SF" in location:
                    location = "San Francisco, CA"
                elif "New York" in location or "NYC" in location:
                    location = "New York, NY"
                elif "Seattle" in location:
                    location = "Seattle, WA"
                elif "Boston" in location:
                    location = "Boston, MA"
                elif "Austin" in location:
                    location = "Austin, TX"
                
                locations[location] = locations.get(location, 0) + 1
            
            # Sort by count
            sorted_locations = sorted(locations.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "analysis_type": "location_distribution",
                "total_jobs": len(all_results.get("metadatas", [])),
                "top_locations": sorted_locations[:10],
                "summary": f"Most AI engineering jobs are in {sorted_locations[0][0]} with {sorted_locations[0][1]} positions" if sorted_locations else "No location data available"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing location distribution: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def analyze_company_distribution(self):
        """Analyze job distribution by company"""
        if not self.job_collection:
            raise HTTPException(status_code=500, detail="No job data available")
        
        try:
            # Get all job metadata
            all_results = self.job_collection.get(include=["metadatas"])
            companies = {}
            
            for metadata in all_results.get("metadatas", []):
                company = metadata.get("company", "Unknown")
                companies[company] = companies.get(company, 0) + 1
            
            # Sort by count
            sorted_companies = sorted(companies.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "analysis_type": "company_distribution", 
                "total_jobs": len(all_results.get("metadatas", [])),
                "top_companies": sorted_companies[:10],
                "summary": f"Most AI engineering jobs are at {sorted_companies[0][0]} with {sorted_companies[0][1]} positions" if sorted_companies else "No company data available"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing company distribution: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/analyze")
async def analyze_job_market(
    query: str = Query(..., description="Analytical query"),
    analysis_type: str = Query("location_distribution", description="Type of analysis")
):
    """Analyze job market data for insights"""
    try:
        if analysis_type == "location_distribution":
            return await retriever_service.analyze_location_distribution()
        elif analysis_type == "company_distribution":
            return await retriever_service.analyze_company_distribution()
        else:
            return {"error": "Analysis type not supported"}
    except Exception as e:
        logger.error(f"Error in job market analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
