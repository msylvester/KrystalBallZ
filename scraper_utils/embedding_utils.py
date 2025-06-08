import json
import os
from typing import List, Dict, Optional
from data_processor import create_embeddings_openai, create_embeddings_local

def load_vector_ready_jobs(filename: str) -> List[Dict]:
    """Load vector-ready job data from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file {filename}: {str(e)}")
        return []

def create_embeddings_for_jobs(jobs: List[Dict], method: str = "local", api_key: Optional[str] = None) -> List[Dict]:
    """Create embeddings for job data"""
    if not jobs:
        print("No jobs to process")
        return []
    
    # Extract texts for embedding
    texts = [job["text"] for job in jobs]
    
    print(f"Creating embeddings for {len(texts)} jobs using {method} method...")
    
    try:
        if method == "openai":
            if not api_key:
                raise ValueError("OpenAI API key required for OpenAI embeddings")
            embeddings = create_embeddings_openai(texts, api_key)
        elif method == "local":
            embeddings = create_embeddings_local(texts)
        else:
            raise ValueError(f"Unknown embedding method: {method}")
        
        # Add embeddings to job data
        jobs_with_embeddings = []
        for job, embedding in zip(jobs, embeddings):
            job_with_embedding = job.copy()
            job_with_embedding["embedding"] = embedding
            jobs_with_embeddings.append(job_with_embedding)
        
        print(f"Successfully created {len(embeddings)} embeddings")
        return jobs_with_embeddings
        
    except Exception as e:
        print(f"Error creating embeddings: {str(e)}")
        return []

def save_embeddings(jobs_with_embeddings: List[Dict], output_filename: str):
    """Save jobs with embeddings to file"""
    try:
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(jobs_with_embeddings, f, indent=2, ensure_ascii=False)
        print(f"Embeddings saved to: {output_filename}")
    except Exception as e:
        print(f"Error saving embeddings: {str(e)}")

def process_jobs_to_embeddings(input_filename: str, output_filename: str, method: str = "local", api_key: Optional[str] = None):
    """Complete pipeline: load jobs, create embeddings, save results"""
    print(f"Processing jobs from {input_filename}")
    
    # Load vector-ready jobs
    jobs = load_vector_ready_jobs(input_filename)
    if not jobs:
        print("No jobs loaded, exiting")
        return
    
    # Create embeddings
    jobs_with_embeddings = create_embeddings_for_jobs(jobs, method, api_key)
    if not jobs_with_embeddings:
        print("No embeddings created, exiting")
        return
    
    # Save results
    save_embeddings(jobs_with_embeddings, output_filename)
    print("Processing complete!")

if __name__ == "__main__":
    import sys
    
    # Example usage
    if len(sys.argv) < 3:
        print("Usage: python embedding_utils.py <input_file> <output_file> [method] [api_key]")
        print("Methods: 'local' (default) or 'openai'")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    method = sys.argv[3] if len(sys.argv) > 3 else "local"
    api_key = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("OPENAI_API_KEY")
    
    process_jobs_to_embeddings(input_file, output_file, method, api_key)
