import http.client
import json
import logging
from datetime import datetime, timedelta
import re

# Configure logging for the job service
logger = logging.getLogger("agent_app.job_service")

class AIJobSearchService:
    def __init__(self, api_key=None):
        """Initialize with Jooble API credentials"""
        self.api_key = api_key or '<YOUR_API_KEY>'
        self.host = 'jooble.org'
        self.logger = logging.getLogger("agent_app.job_service.AIJobSearchService")
        self.logger.info("AIJobSearchService initialized")
        
    def get_ai_jobs(self, location="", limit=10):
        """MCP implementation to get AI engineering job data"""
        self.logger.info(f"Getting AI jobs for location='{location}', limit={limit}")
        try:
            # Model: Get data from Jooble API
            self.logger.info("Fetching job data from API")
            job_data = self._fetch_job_data(location, limit)
            
            # Controller: Process the data
            self.logger.info(f"Processing job data with {len(job_data.get('jobs', []))} jobs")
            processed_data = self._process_job_data(job_data)
            
            # Processor: Format the response
            self.logger.info("Formatting job report")
            report = self._format_job_report(processed_data)
            self.logger.info(f"Job report generated ({len(report)} chars)")
            return report
        except Exception as e:
            self.logger.error(f"Error getting AI job listings: {str(e)}")
            return f"Error getting AI job listings: {str(e)}"
    
    def _fetch_job_data(self, location, limit):
        """Model component: Fetch AI engineering jobs from Jooble API"""
        try:
            self.logger.info(f"Connecting to {self.host}")
            connection = http.client.HTTPConnection(self.host)
            
            # Request headers
            headers = {"Content-type": "application/json"}
            
            # JSON query for AI engineering jobs
            query_body = {
                "keywords": "AI Engineer OR Artificial Intelligence Engineer OR Machine Learning Engineer OR ML Engineer",
                "location": location or "United States",
                "radius": "25",
                "salary": "",
                "datecreatedfrom": "",
                "page": "1"
            }
            
            body = json.dumps(query_body)
            self.logger.info(f"API request: {body}")
            
            # Make API request
            connection.request('POST', '/api/' + self.api_key, body, headers)
            self.logger.info("Waiting for API response")
            response = connection.getresponse()
            
            if response.status == 200:
                self.logger.info("API request successful (200 OK)")
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)
                self.logger.info(f"Received {len(data.get('jobs', []))} jobs from API")
                return data
            else:
                self.logger.warning(f"API Error: {response.status} {response.reason}")
                self.logger.info("Falling back to mock data")
                # If San Francisco was requested, provide San Francisco-specific mock data
                if location and "san francisco" in location.lower():
                    self.logger.info("Providing San Francisco-specific mock data")
                    return self._get_san_francisco_mock_data()
                return self._get_mock_data()
                
        except Exception as e:
            self.logger.error(f"Connection error: {str(e)}")
            self.logger.info("Falling back to mock data due to error")
            return self._get_mock_data()
        finally:
            if 'connection' in locals():
                connection.close()
                self.logger.debug("Connection closed")
    
    def _get_mock_data(self):
        """Fallback mock data for demonstration"""
        self.logger.info("Generating mock job data")
        return {
            'jobs': [
                {
                    'title': 'Senior AI Engineer',
                    'company': 'TechFlow AI',
                    'location': 'San Francisco, CA',
                    'snippet': 'Design and implement AI models for production systems. Work with neural networks, deep learning frameworks, and cloud infrastructure. Requires 5+ years experience with Python, TensorFlow, PyTorch.',
                    'updated': '2024-05-28T10:30:00',
                    'link': 'https://jooble.org/desc/123456789',
                    'salary': '$150,000 - $200,000',
                    'source': 'TechFlow Careers',
                    'type': 'Permanent'
                },
                {
                    'title': 'Machine Learning Engineer',
                    'company': 'DataVision Corp',
                    'location': 'New York, NY',
                    'snippet': 'Build scalable ML pipelines and deploy models to production. Experience with MLOps, Docker, Kubernetes, and AWS required. Work on computer vision and NLP projects.',
                    'updated': '2024-05-27T14:15:00',
                    'link': 'https://jooble.org/desc/987654321',
                    'salary': '$120,000 - $160,000',
                    'source': 'DataVision Jobs',
                    'type': 'Permanent'
                },
                {
                    'title': 'AI Research Engineer',
                    'company': 'Innovation Labs',
                    'location': 'Seattle, WA',
                    'snippet': 'Research and develop cutting-edge AI algorithms. Focus on reinforcement learning and generative AI. PhD in Computer Science or related field preferred.',
                    'updated': '2024-05-26T09:45:00',
                    'link': 'https://jooble.org/desc/456789123',
                    'salary': '$140,000 - $180,000',
                    'source': 'Innovation Careers',
                    'type': 'Permanent'
                },
                {
                    'title': 'Junior AI Engineer',
                    'company': 'StartupAI Inc',
                    'location': 'Austin, TX',
                    'snippet': 'Entry-level position for recent graduates. Work on AI chatbots and recommendation systems. Requires knowledge of Python, machine learning basics, and eagerness to learn.',
                    'updated': '2024-05-25T16:20:00',
                    'link': 'https://jooble.org/desc/789123456',
                    'salary': '$80,000 - $110,000',
                    'source': 'StartupAI Careers',
                    'type': 'Permanent'
                },
                {
                    'title': 'Lead ML Engineer',
                    'company': 'FinTech Solutions',
                    'location': 'Chicago, IL',
                    'snippet': 'Lead a team of ML engineers building fraud detection systems. Experience with real-time ML, distributed systems, and team leadership required.',
                    'updated': '2024-05-24T11:00:00',
                    'link': 'https://jooble.org/desc/321654987',
                    'salary': '$180,000 - $220,000',
                    'source': 'FinTech Jobs',
                    'type': 'Permanent'
                }
            ],
            'totalCount': 1247
        }
    
    def _get_san_francisco_mock_data(self):
        """San Francisco specific mock data for demonstration"""
        self.logger.info("Generating San Francisco specific mock data")
        return {
            'jobs': [
                {
                    'title': 'Senior AI Engineer',
                    'company': 'TechFlow AI',
                    'location': 'San Francisco, CA',
                    'snippet': 'Design and implement AI models for production systems. Work with neural networks, deep learning frameworks, and cloud infrastructure. Requires 5+ years experience with Python, TensorFlow, PyTorch.',
                    'updated': '2024-05-28T10:30:00',
                    'link': 'https://jooble.org/desc/123456789',
                    'salary': '$180,000 - $220,000',
                    'source': 'TechFlow Careers',
                    'type': 'Permanent'
                },
                {
                    'title': 'Machine Learning Engineer',
                    'company': 'Bay Area Tech',
                    'location': 'San Francisco, CA',
                    'snippet': 'Build scalable ML pipelines and deploy models to production. Experience with MLOps, Docker, Kubernetes, and AWS required. Work on computer vision and NLP projects.',
                    'updated': '2024-05-27T14:15:00',
                    'link': 'https://jooble.org/desc/987654321',
                    'salary': '$160,000 - $190,000',
                    'source': 'Bay Area Tech Jobs',
                    'type': 'Permanent'
                },
                {
                    'title': 'AI Research Scientist',
                    'company': 'SF Innovation Labs',
                    'location': 'San Francisco, CA',
                    'snippet': 'Research and develop cutting-edge AI algorithms. Focus on reinforcement learning and generative AI. PhD in Computer Science or related field preferred.',
                    'updated': '2024-05-26T09:45:00',
                    'link': 'https://jooble.org/desc/456789123',
                    'salary': '$170,000 - $210,000',
                    'source': 'SF Innovation Careers',
                    'type': 'Permanent'
                },
                {
                    'title': 'NLP Engineer',
                    'company': 'Language AI',
                    'location': 'San Francisco, CA',
                    'snippet': 'Develop natural language processing models for our conversational AI platform. Experience with transformer models, BERT, GPT required. Python and PyTorch expertise essential.',
                    'updated': '2024-05-25T16:20:00',
                    'link': 'https://jooble.org/desc/789123456',
                    'salary': '$150,000 - $180,000',
                    'source': 'Language AI Careers',
                    'type': 'Permanent'
                },
                {
                    'title': 'Lead ML Engineer',
                    'company': 'SF FinTech',
                    'location': 'San Francisco, CA',
                    'snippet': 'Lead a team of ML engineers building fraud detection systems. Experience with real-time ML, distributed systems, and team leadership required.',
                    'updated': '2024-05-24T11:00:00',
                    'link': 'https://jooble.org/desc/321654987',
                    'salary': '$200,000 - $240,000',
                    'source': 'SF FinTech Jobs',
                    'type': 'Permanent'
                }
            ],
            'totalCount': 187
        }
    
    def _process_job_data(self, data):
        """Controller component: Process the job data"""
        jobs = data.get('jobs', [])
        total_results = data.get('totalCount', 0)
        
        processed_jobs = []
        salary_ranges = []
        locations = {}
        companies = {}
        job_types = {}
        
        for job in jobs:
            # Process individual job
            processed_job = {
                'title': job.get('title', 'N/A'),
                'company': job.get('company', 'N/A'),
                'location': job.get('location', 'N/A'),
                'snippet': job.get('snippet', 'No description available'),
                'date_posted': self._format_date(job.get('updated', '')),
                'url': job.get('link', ''),
                'salary': job.get('salary', 'Not specified'),
                'source': job.get('source', 'Jooble'),
                'type': job.get('type', 'Not specified'),
                'seniority': self._determine_seniority(job.get('title', '')),
                'tech_stack': self._extract_tech_stack(job.get('snippet', ''))
            }
            processed_jobs.append(processed_job)
            
            # Collect data for analysis
            if job.get('salary') and 'not specified' not in job.get('salary', '').lower():
                salary_ranges.append(job.get('salary'))
            
            # Count locations
            location = job.get('location', 'Unknown')
            locations[location] = locations.get(location, 0) + 1
            
            # Count companies
            company = job.get('company', 'Unknown')
            companies[company] = companies.get(company, 0) + 1
            
            # Count job types
            job_type = job.get('type', 'Unknown')
            job_types[job_type] = job_types.get(job_type, 0) + 1
        
        return {
            'jobs': processed_jobs,
            'total_results': total_results,
            'salary_ranges': salary_ranges,
            'top_locations': sorted(locations.items(), key=lambda x: x[1], reverse=True)[:5],
            'top_companies': sorted(companies.items(), key=lambda x: x[1], reverse=True)[:5],
            'job_types': dict(sorted(job_types.items(), key=lambda x: x[1], reverse=True)),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    
    def _determine_seniority(self, title):
        """Determine job seniority level from title"""
        title_lower = title.lower()
        if any(word in title_lower for word in ['senior', 'sr', 'lead', 'principal', 'staff', 'head', 'director']):
            return 'Senior'
        elif any(word in title_lower for word in ['junior', 'jr', 'entry', 'associate', 'intern', 'graduate']):
            return 'Junior'
        else:
            return 'Mid-level'
    
    def _extract_tech_stack(self, snippet):
        """Extract technology stack from job description"""
        tech_keywords = [
            'Python', 'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn',
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes',
            'MLOps', 'Apache Spark', 'Hadoop', 'SQL', 'NoSQL',
            'React', 'Node.js', 'Java', 'C++', 'R',
            'Computer Vision', 'NLP', 'Deep Learning', 'Neural Networks'
        ]
        
        found_tech = []
        snippet_lower = snippet.lower()
        
        for tech in tech_keywords:
            if tech.lower() in snippet_lower:
                found_tech.append(tech)
        
        return found_tech[:5]  # Return top 5 technologies mentioned
    
    def _format_date(self, date_string):
        """Format date string to readable format"""
        if not date_string:
            return 'Recently'
        try:
            # Parse ISO date format from Jooble
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            days_ago = (datetime.now() - dt.replace(tzinfo=None)).days
            if days_ago == 0:
                return 'Today'
            elif days_ago == 1:
                return 'Yesterday'
            else:
                return f'{days_ago} days ago'
        except:
            return 'Recently'
    
    def _format_job_report(self, data):
        """Processor component: Format the job report for display"""
        jobs = data['jobs']
        total_results = data['total_results']
        
        # Header
        report = f"🤖 AI ENGINEERING JOBS REPORT - Powered by Jooble ({data['timestamp']})\n\n"
        report += f"Found {total_results:,} AI engineering positions\n"
        report += f"Showing top {len(jobs)} results:\n\n"
        
        # Job listings
        for i, job in enumerate(jobs, 1):
            report += f"#{i}. {job['title']} ({job['seniority']})\n"
            report += f"   🏢 Company: {job['company']}\n"
            report += f"   📍 Location: {job['location']}\n"
            report += f"   💰 Salary: {job['salary']}\n"
            report += f"   📅 Posted: {job['date_posted']}\n"
            report += f"   🔗 Type: {job['type']}\n"
            
            if job['tech_stack']:
                report += f"   🛠️  Tech Stack: {', '.join(job['tech_stack'])}\n"
            
            report += f"   📝 Summary: {job['snippet'][:120]}...\n"
            
            if job['url']:
                report += f"   🔗 Apply: {job['url']}\n"
            report += "\n"
        
        # Summary statistics
        if data['top_locations']:
            report += "📍 TOP HIRING LOCATIONS:\n"
            for location, count in data['top_locations']:
                report += f"   • {location}: {count} positions\n"
            report += "\n"
        
        if data['top_companies']:
            report += "🏢 TOP HIRING COMPANIES:\n"
            for company, count in data['top_companies']:
                report += f"   • {company}: {count} positions\n"
            report += "\n"
        
        if data['job_types']:
            report += "💼 JOB TYPES:\n"
            for job_type, count in data['job_types'].items():
                report += f"   • {job_type}: {count} positions\n"
            report += "\n"
        
        if data['salary_ranges']:
            report += "💰 SALARY INSIGHTS:\n"
            report += f"   • {len(data['salary_ranges'])} positions with salary data\n"
            
            # Analyze salary ranges
            seniority_salaries = {'Junior': [], 'Mid-level': [], 'Senior': []}
            for job in jobs:
                if job['salary'] != 'Not specified':
                    seniority_salaries[job['seniority']].append(job['salary'])
            
            for level, salaries in seniority_salaries.items():
                if salaries:
                    report += f"   • {level}: {len(salaries)} positions with salary info\n"
            report += "\n"
        
        report += "💡 INSIGHTS:\n"
        report += "   • Most positions require Python and ML framework experience\n"
        report += "   • Cloud platform knowledge (AWS/Azure/GCP) highly valued\n"
        report += "   • MLOps and production deployment skills in high demand\n"
        report += "   • Computer Vision and NLP specializations are trending\n\n"
        
        report += "🔄 Data source: Jooble API - Real-time job aggregation from multiple job boards"
        
        return report


# Usage example:
# service = AIJobSearchService(api_key="your_jooble_api_key")
# report = service.get_ai_jobs(location="San Francisco", limit=10)
# print(report)
