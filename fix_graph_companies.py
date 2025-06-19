import os
import requests
from neo4j import GraphDatabase
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_graph_company_relationships():
    """
    Fix Neo4j graph database by creating Company nodes and relationships
    using company information from the vector database.
    """
    
    # Configuration
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "jobsearch")
    retriever_url = os.environ.get("RETRIEVER_SERVICE_URL", "http://localhost:8001")
    
    # Connect to Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            # Step 1: Get all job IDs from Neo4j that have null or missing company info
            logger.info("Getting jobs with missing company information from Neo4j...")
            jobs_needing_fix = session.run("""
                MATCH (j:Job)
                WHERE j.company IS NULL OR j.company = '' OR NOT EXISTS(j.company)
                RETURN j.id as job_id
            """).data()
            
            logger.info(f"Found {len(jobs_needing_fix)} jobs needing company information")
            
            if not jobs_needing_fix:
                logger.info("No jobs need fixing!")
                return
            
            # Step 2: For each job, query vector DB to get company information
            fixed_count = 0
            for job_record in jobs_needing_fix:
                job_id = job_record['job_id']
                logger.info(f"Processing job ID: {job_id}")
                
                try:
                    # Query vector database to find this job and get its company info
                    response = requests.get(
                        f"{retriever_url}/retrieve",
                        params={"query": f"job id {job_id}", "n_results": 50}
                    )
                    
                    if response.status_code == 200:
                        vector_data = response.json()
                        results = vector_data.get("results", [])
                        
                        # Find the exact job by ID
                        company_name = None
                        for result in results:
                            if result.get("id") == job_id:
                                metadata = result.get("metadata", {})
                                company_name = metadata.get("company")
                                break
                        
                        if company_name and company_name.strip():
                            logger.info(f"Found company '{company_name}' for job {job_id}")
                            
                            # Step 3: Update Neo4j with company information
                            session.run("""
                                // Create or get Company node
                                MERGE (c:Company {name: $company_name})
                                
                                // Update Job node with company info
                                WITH c
                                MATCH (j:Job {id: $job_id})
                                SET j.company = $company_name
                                
                                // Create relationship
                                MERGE (c)-[:HAS_JOB]->(j)
                                
                                RETURN j.id as updated_job_id, c.name as company_name
                            """, job_id=job_id, company_name=company_name)
                            
                            fixed_count += 1
                            logger.info(f"✅ Fixed job {job_id} -> {company_name}")
                        else:
                            logger.warning(f"❌ No company found for job {job_id} in vector DB")
                    else:
                        logger.error(f"❌ Vector DB query failed for job {job_id}: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing job {job_id}: {str(e)}")
                    continue
            
            logger.info(f"🎉 Fixed {fixed_count} out of {len(jobs_needing_fix)} jobs")
            
            # Step 4: Verify the fix
            logger.info("Verifying the fix...")
            verification = session.run("""
                MATCH (c:Company)-[:HAS_JOB]->(j:Job)
                RETURN c.name as company, count(j) as job_count
                ORDER BY job_count DESC
            """).data()
            
            logger.info("Company relationships after fix:")
            for record in verification:
                logger.info(f"  {record['company']}: {record['job_count']} jobs")
                
    except Exception as e:
        logger.error(f"Error during fix process: {str(e)}")
    finally:
        driver.close()

def verify_fix():
    """
    Verify that the fix worked by checking for jobs without company relationships
    """
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
    neo4j_password = os.environ.get("NEO4J_PASSWORD", "jobsearch")
    
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    try:
        with driver.session() as session:
            # Check for jobs still missing company info
            orphaned_jobs = session.run("""
                MATCH (j:Job)
                WHERE NOT EXISTS((j)<-[:HAS_JOB]-(:Company))
                RETURN count(j) as orphaned_count
            """).single()
            
            total_jobs = session.run("""
                MATCH (j:Job)
                RETURN count(j) as total_count
            """).single()
            
            logger.info(f"Verification Results:")
            logger.info(f"  Total jobs: {total_jobs['total_count']}")
            logger.info(f"  Jobs without company relationships: {orphaned_jobs['orphaned_count']}")
            logger.info(f"  Jobs with company relationships: {total_jobs['total_count'] - orphaned_jobs['orphaned_count']}")
            
    finally:
        driver.close()

if __name__ == "__main__":
    logger.info("🔧 Starting graph database company relationship fix...")
    fix_graph_company_relationships()
    logger.info("🔍 Running verification...")
    verify_fix()
    logger.info("✅ Fix process completed!")
