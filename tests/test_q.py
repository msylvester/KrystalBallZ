#!/usr/bin/env python3
import sys
import os
import time
import requests
from openai import AsyncOpenAI

# Add parent directory to path so we can import from scraper_utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

aclient = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
import chromadb
from scraper_utils.job_scraper_linkedin_guest import scrape_ai_jobs_for_rag

# Ensure the OpenAI API key is set
if not aclient.api_key:
    print("Please set the OPENAI_API_KEY environment variable.")
    sys.exit(1)

# URL for the vector ingestion endpoint
VECTOR_INGEST_URL = os.environ.get("VECTOR_DB_URL", "http://localhost:8000/ingest")

def ingest_jobs():
    print("Scraping job listings...")
    jobs = scrape_ai_jobs_for_rag()
    if not jobs:
        print("No jobs were scraped. Exiting.")
        sys.exit(1)

    success_count = 0
    total_jobs = len(jobs)
    print(f"Found {total_jobs} jobs. Ingesting into the vector DB service...")
    for job in jobs:
        payload = {
            "id": job["id"],
            "text_preview": job["text"],
            "metadata": job["metadata"]
        }
        try:
            response = requests.post(VECTOR_INGEST_URL, json=payload)
            if response.status_code == 200:
                success_count += 1
            else:
                print(f"Failed to ingest job {job['id']} - Status Code: {response.status_code}")
        except Exception as e:
            print(f"Error ingesting job {job['id']}: {str(e)}")
    print(f"Ingestion complete: {success_count} of {total_jobs} jobs ingested.")

def embed_query(query_text):
    import asyncio
    try:
        async def get_emb():
            response = await aclient.embeddings.create(input=[query_text],
            model="text-embedding-ada-002")
            return response.data[0].embedding
        embedding = asyncio.run(get_emb())
        return embedding
    except Exception as e:
        print(f"Error creating query embedding: {str(e)}")
        sys.exit(1)

def query_vector_db(embedding, n_results=5):
    # Initialize ChromaDB client and get the job_listings collection.
    print("Querying the vector database...")
    chroma_client = chromadb.Client()
    try:
        collection = chroma_client.get_collection("job_listings")
    except Exception:
        print("Collection 'job_listings' not found in ChromaDB.")
        sys.exit(1)

    try:
        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        return results
    except Exception as e:
        print(f"Error querying ChromaDB: {str(e)}")
        sys.exit(1)

def cosine_similarity(vec1, vec2):
    import math
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    return dot / (norm1 * norm2) if norm1 and norm2 else 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_query.py [<jobs_file>] '<query_text>'")
        sys.exit(1)
    
    if len(sys.argv) == 2:
        jobs_file = None
        query_text = sys.argv[1]
    else:
        jobs_file = sys.argv[1]
        query_text = sys.argv[2]

    # Load vector-ready jobs from file if provided; otherwise, scrape job listings
    import json
    if jobs_file:
        try:
            with open(jobs_file, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
        except Exception as e:
            print(f"Error loading jobs file: {str(e)}")
            sys.exit(1)
    else:
        print("No jobs file provided. Scraping job listings instead...")
        jobs = scrape_ai_jobs_for_rag()

    if not jobs:
        print("No jobs found in file. Exiting.")
        sys.exit(1)

    # Create embedding for the supplied query
    query_embedding = embed_query(query_text)

    # Compute similarity between query embedding and each job embedding
    scored_jobs = []
    for job in jobs:
        embedding = job.get("embedding")
        if not embedding:
            embedding = embed_query(job["text"])
        score = cosine_similarity(query_embedding, embedding)
        scored_jobs.append((score, job))

    # Sort jobs by similarity, descending
    scored_jobs.sort(key=lambda x: x[0], reverse=True)

    # Print top 5 results
    print("\nTop 5 Query Results:")
    for score, job in scored_jobs[:5]:
        print(f"Score: {score:.4f} | Job ID: {job.get('id', 'N/A')} | Title: {job.get('title', 'N/A')}")
    print("\nEnd of Query Results\n")

if __name__ == "__main__":
    main()
