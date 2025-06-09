import re
import hashlib
from typing import List, Dict, Any
from datetime import datetime

def clean_text(text: str) -> str:
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace, newlines, special characters
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'[^\w\s\-\.,;:()\[\]{}]', '', text)
    return text

def extract_requirements(description: str) -> List[str]:
    """Extract key requirements from job description"""
    requirements = []
    
    # Common requirement patterns
    patterns = [
        r'(?:require[sd]?|must have|need|essential)[\s\w]*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        r'(\d+\+?\s*years?\s*(?:of\s*)?experience)',
        r'(Bachelor\'?s?|Master\'?s?|PhD|degree)',
        r'(Python|JavaScript|Java|C\+\+|SQL|AWS|Docker|Kubernetes|TensorFlow|PyTorch)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, description, re.IGNORECASE)
        requirements.extend(matches)
    
    return list(set(requirements))  # Remove duplicates

def normalize_tech_stack(tech_list: List[str]) -> List[str]:
    """Normalize technology stack"""
    tech_mapping = {
        'js': 'JavaScript',
        'py': 'Python',
        'tf': 'TensorFlow',
        'k8s': 'Kubernetes',
        'react': 'React',
        'node': 'Node.js',
        'ml': 'Machine Learning',
        'ai': 'Artificial Intelligence'
    }
    
    normalized = []
    for tech in tech_list:
        tech_clean = tech.lower().strip()
        normalized.append(tech_mapping.get(tech_clean, tech))
    
    return normalized

def normalize_location(location: str) -> str:
    """Normalize location string"""
    if not location:
        return "Remote"
    
    location = clean_text(location)
    
    # Common location normalizations
    location_mapping = {
        'sf': 'San Francisco, CA',
        'nyc': 'New York, NY',
        'la': 'Los Angeles, CA',
        'remote': 'Remote',
        'n/a': 'Remote'
    }
    
    location_lower = location.lower()
    return location_mapping.get(location_lower, location)

def normalize_salary(salary: str) -> str:
    """Normalize salary range"""
    if not salary or salary.lower() in ['n/a', 'not specified']:
        return "Not specified"
    
    # Extract numbers and currency
    salary_clean = re.sub(r'[^\d\-k$,.]', ' ', salary.lower())
    return salary_clean.strip() if salary_clean.strip() else "Not specified"

def normalize_employment_type(emp_type: str) -> str:
    """Normalize employment type"""
    if not emp_type or emp_type.lower() in ['n/a', 'not specified']:
        return "Full-time"
    
    emp_type_lower = emp_type.lower()
    
    if any(term in emp_type_lower for term in ['full', 'permanent']):
        return "Full-time"
    elif any(term in emp_type_lower for term in ['part', 'contract']):
        return "Part-time/Contract"
    elif 'intern' in emp_type_lower:
        return "Internship"
    else:
        return emp_type

def determine_remote_status(job: Dict) -> bool:
    """Determine if job is remote-friendly"""
    location = job.get('location', '').lower()
    description = job.get('description', '').lower()
    
    remote_indicators = ['remote', 'work from home', 'wfh', 'distributed', 'anywhere']
    
    return any(indicator in location or indicator in description for indicator in remote_indicators)

def extract_experience_level(description: str) -> str:
    """Extract experience level from description"""
    if not description:
        return "Not specified"
    
    description_lower = description.lower()
    
    if any(term in description_lower for term in ['senior', 'sr.', 'lead', 'principal', 'staff']):
        return 'Senior'
    elif any(term in description_lower for term in ['junior', 'jr.', 'entry', 'graduate', 'new grad']):
        return 'Junior'
    elif any(term in description_lower for term in ['mid', 'intermediate']):
        return 'Mid-level'
    else:
        return 'Not specified'

def standardize_date(date_str: Any) -> str:
    """Standardize date format"""
    if isinstance(date_str, str):
        return date_str
    elif isinstance(date_str, datetime):
        return date_str.strftime("%Y-%m-%d")
    else:
        return datetime.now().strftime("%Y-%m-%d")

def generate_unique_id(job: Dict) -> str:
    """Generate unique ID for job posting"""
    # Create hash from title + company + location
    unique_string = f"{job.get('job_title', '')}{job.get('company', '')}{job.get('location', '')}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12]

def standardize_job_data(job: Dict) -> Dict:
    """Standardize and clean job data for vector embedding"""
    return {
        "id": generate_unique_id(job),
        "title": clean_text(job.get("job_title", "")),
        "company": clean_text(job.get("company", "")),
        "location": normalize_location(job.get("location", "")),
        "description": clean_text(job.get("description", "")),
        "requirements": extract_requirements(job.get("description", "")),
        "tech_stack": normalize_tech_stack(job.get("tech_stack", [])),
        "salary_range": normalize_salary(job.get("salary_range", "")),
        "employment_type": normalize_employment_type(job.get("employment_type", "")),
        "remote_friendly": determine_remote_status(job),
        "experience_level": extract_experience_level(job.get("description", "")),
        "posted_date": standardize_date(job.get("posted_date")),
        "source": job.get("source", ""),
        "apply_link": job.get("apply_link", ""),
        "search_term": job.get("search_term", "")
    }

def clean_for_embedding(text: str) -> str:
    """Clean text specifically for embedding"""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove special characters but keep basic punctuation
    text = re.sub(r'[^\w\s\-\.,;:()]', '', text)
    return text

def create_embedding_text(job: Dict) -> Dict:
    """Create optimized text for vector embedding"""
    
    # Primary embedding text (most important for similarity)
    primary_text = f"""
    Job Title: {job['title']}
    Company: {job['company']}
    Location: {job['location']}
    Description: {job['description'][:500]}
    Requirements: {' '.join(job['requirements'])}
    Tech Stack: {' '.join(job['tech_stack'])}
    Experience Level: {job['experience_level']}
    Employment Type: {job['employment_type']}
    """
    
    # Secondary metadata text
    metadata_text = f"""
    Remote: {job['remote_friendly']}
    Salary: {job['salary_range']}
    Posted: {job['posted_date']}
    Source: {job['source']}
    """
    
    return {
        "primary_text": clean_for_embedding(primary_text),
        "metadata_text": clean_for_embedding(metadata_text),
        "combined_text": clean_for_embedding(primary_text + metadata_text)
    }

def clean_metadata_for_chromadb(metadata: Dict) -> Dict:
    """Clean metadata to ensure ChromaDB compatibility"""
    cleaned_metadata = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            cleaned_metadata[key] = value
        elif isinstance(value, list):
            # Convert lists to comma-separated strings
            cleaned_metadata[key] = ", ".join(str(item) for item in value)
        else:
            # Convert other types to strings
            cleaned_metadata[key] = str(value)
    return cleaned_metadata

def prepare_for_vector_db(job_data: Dict) -> Dict:
    """Prepare job data for vector database insertion"""
    
    embedding_texts = create_embedding_text(job_data)
    
    raw_metadata = {
        "title": job_data["title"],
        "company": job_data["company"],
        "location": job_data["location"],
        "tech_stack": job_data["tech_stack"],
        "experience_level": job_data["experience_level"],
        "employment_type": job_data["employment_type"],
        "remote_friendly": job_data["remote_friendly"],
        "salary_range": job_data["salary_range"],
        "posted_date": job_data["posted_date"],
        "source": job_data["source"],
        "apply_link": job_data["apply_link"],
        "search_term": job_data["search_term"]
    }
    
    return {
        "id": job_data["id"],
        "text": embedding_texts["combined_text"],  # Text to embed
        "metadata": clean_metadata_for_chromadb(raw_metadata)
    }

def validate_job_data(job: Dict) -> bool:
    """Validate job data quality"""
    required_fields = ['job_title', 'company', 'location']
    
    # Check required fields
    for field in required_fields:
        if not job.get(field) or job[field].strip() == "":
            return False
    
    return True

def create_embeddings_openai(texts: List[str], api_key: str) -> List[List[float]]:
    """Create embeddings using OpenAI API"""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [embedding.embedding for embedding in response.data]
    except ImportError:
        raise ImportError("OpenAI package not installed. Run: pip install openai")
    except Exception as e:
        raise Exception(f"Error creating OpenAI embeddings: {str(e)}")

def create_embeddings_local(texts: List[str]) -> List[List[float]]:
    """Create embeddings using local sentence-transformers"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model.encode(texts).tolist()
    except ImportError:
        raise ImportError("sentence-transformers package not installed. Run: pip install sentence-transformers")
    except Exception as e:
        raise Exception(f"Error creating local embeddings: {str(e)}")
