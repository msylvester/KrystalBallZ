import json
from datetime import datetime
from data_processor import standardize_job_data, prepare_for_vector_db

def create_sample_raw_job():
    """Create a sample raw job posting as it comes from scraping"""
    return {
        "job_title": "Senior AI Engineer",
        "company": "TechCorp Inc.",
        "location": "San Francisco, CA",
        "description": "We are looking for a Senior AI Engineer with 5+ years experience in Python, TensorFlow, and machine learning. Must have Bachelor's degree in Computer Science.",
        "employment_type": "Full-time",
        "salary_range": "$150k-200k",
        "tech_stack": ["Python", "TensorFlow", "AWS"],
        "apply_link": "https://example.com/apply",
        "source": "LinkedIn",
        "search_term": "ai engineering",
        "posted_date": "2024-12-06"
    }

def demonstrate_data_pipeline():
    """Demonstrate the complete data processing pipeline"""
    
    print("=== DATA PROCESSING PIPELINE DEMONSTRATION ===\n")
    
    # Step 1: Raw scraped data
    raw_job = create_sample_raw_job()
    print("1. RAW SCRAPED DATA:")
    print(json.dumps(raw_job, indent=2))
    print("\n" + "="*50 + "\n")
    
    # Step 2: Standardized/cleaned data
    standardized_job = standardize_job_data(raw_job)
    print("2. STANDARDIZED DATA:")
    print(json.dumps(standardized_job, indent=2))
    print("\n" + "="*50 + "\n")
    
    # Step 3: Vector-ready format
    vector_ready = prepare_for_vector_db(standardized_job)
    print("3. VECTOR-READY FORMAT:")
    print(json.dumps({
        "id": vector_ready["id"],
        "text_preview": vector_ready["text"][:200] + "...",
        "metadata": vector_ready["metadata"]
    }, indent=2))
    print("\n" + "="*50 + "\n")
    
    # Step 4: Show what the final embedded format would look like
    print("4. FINAL FORMAT (with placeholder embedding):")
    final_format = vector_ready.copy()
    final_format["embedding"] = "[384-dimensional vector would go here]"
    final_format["text"] = final_format["text"][:100] + "..."  # Truncate for display
    
    print(json.dumps(final_format, indent=2))
    
    return {
        "raw": raw_job,
        "standardized": standardized_job,
        "vector_ready": vector_ready
    }

if __name__ == "__main__":
    demonstrate_data_pipeline()
