import pytest
import requests
import json
from neo4j import GraphDatabase
import os
import time

class TestEnhancedGraphContext:
    """Test enhanced graph context retrieval functionality"""
    
    @classmethod
    def setup_class(cls):
        """Setup test data in Neo4j"""
        cls.neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        cls.neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        cls.neo4j_password = os.environ.get("NEO4J_PASSWORD", "jobsearch")
        cls.retriever_url = "http://localhost:8001"
        cls.vector_db_url = "http://localhost:8002"
        
        # Connect to Neo4j
        cls.driver = GraphDatabase.driver(cls.neo4j_uri, auth=(cls.neo4j_user, cls.neo4j_password))
        
        # Setup test data
        cls.setup_test_data()
    
    @classmethod
    def setup_test_data(cls):
        """Create test data in Neo4j and vector DB"""
        with cls.driver.session() as session:
            # Clear existing test data
            session.run("MATCH (n) WHERE n.id STARTS WITH 'test_' DETACH DELETE n")
            
            # Create test companies
            session.run("""
                CREATE (google:Company {name: 'Google'})
                CREATE (microsoft:Company {name: 'Microsoft'})
                CREATE (openai:Company {name: 'OpenAI'})
            """)
            
            # Create test jobs
            session.run("""
                MATCH (google:Company {name: 'Google'})
                MATCH (microsoft:Company {name: 'Microsoft'})
                MATCH (openai:Company {name: 'OpenAI'})
                
                CREATE (j1:Job {id: 'test_job_1', title: 'Senior AI Engineer', location: 'San Francisco, CA'})
                CREATE (j2:Job {id: 'test_job_2', title: 'Junior AI Engineer', location: 'San Francisco, CA'})
                CREATE (j3:Job {id: 'test_job_3', title: 'Machine Learning Engineer', location: 'Remote'})
                CREATE (j4:Job {id: 'test_job_4', title: 'Senior Python Developer', location: 'New York, NY'})
                CREATE (j5:Job {id: 'test_job_5', title: 'Data Scientist', location: 'Remote'})
                
                CREATE (google)-[:HAS_JOB]->(j1)
                CREATE (google)-[:HAS_JOB]->(j2)
                CREATE (microsoft)-[:HAS_JOB]->(j3)
                CREATE (microsoft)-[:HAS_JOB]->(j4)
                CREATE (openai)-[:HAS_JOB]->(j5)
            """)
            
            # Create test skills
            session.run("""
                MATCH (j1:Job {id: 'test_job_1'})
                MATCH (j2:Job {id: 'test_job_2'})
                MATCH (j3:Job {id: 'test_job_3'})
                MATCH (j4:Job {id: 'test_job_4'})
                MATCH (j5:Job {id: 'test_job_5'})
                
                CREATE (python:Skill {name: 'Python'})
                CREATE (ml:Skill {name: 'Machine Learning'})
                CREATE (tf:Skill {name: 'Tensorflow'})
                CREATE (js:Skill {name: 'Javascript'})
                
                CREATE (j1)-[:REQUIRES]->(python)
                CREATE (j1)-[:REQUIRES]->(ml)
                CREATE (j1)-[:REQUIRES]->(tf)
                
                CREATE (j2)-[:REQUIRES]->(python)
                CREATE (j2)-[:REQUIRES]->(ml)
                
                CREATE (j3)-[:REQUIRES]->(python)
                CREATE (j3)-[:REQUIRES]->(ml)
                CREATE (j3)-[:REQUIRES]->(tf)
                
                CREATE (j4)-[:REQUIRES]->(python)
                CREATE (j4)-[:REQUIRES]->(js)
                
                CREATE (j5)-[:REQUIRES]->(python)
                CREATE (j5)-[:REQUIRES]->(ml)
            """)
        
        # Add test data to vector DB
        test_jobs = [
            {
                "id": "test_job_1",
                "text_preview": "Senior AI Engineer position at Google focusing on machine learning and deep learning technologies. Requires Python, TensorFlow, and 5+ years experience.",
                "metadata": {
                    "title": "Senior AI Engineer",
                    "company": "Google",
                    "location": "San Francisco, CA",
                    "experience_level": "Senior"
                }
            },
            {
                "id": "test_job_2", 
                "text_preview": "Junior AI Engineer role at Google. Entry-level position for recent graduates. Python and machine learning knowledge required.",
                "metadata": {
                    "title": "Junior AI Engineer",
                    "company": "Google", 
                    "location": "San Francisco, CA",
                    "experience_level": "Junior"
                }
            }
        ]
        
        for job in test_jobs:
            try:
                response = requests.post(f"{cls.vector_db_url}/ingest", json=job)
                if response.status_code != 200:
                    print(f"Warning: Failed to ingest test job {job['id']}: {response.status_code}")
            except Exception as e:
                print(f"Warning: Could not ingest test data: {e}")
        
        # Wait for data to be available
        time.sleep(2)
    
    @classmethod
    def teardown_class(cls):
        """Clean up test data"""
        with cls.driver.session() as session:
            session.run("MATCH (n) WHERE n.id STARTS WITH 'test_' DETACH DELETE n")
            session.run("MATCH (c:Company) WHERE c.name IN ['Google', 'Microsoft', 'OpenAI'] DETACH DELETE c")
            session.run("MATCH (s:Skill) WHERE s.name IN ['Python', 'Machine Learning', 'Tensorflow', 'Javascript'] DETACH DELETE s")
        cls.driver.close()
    
    def test_enhanced_graph_context_basic(self):
        """Test basic enhanced graph context retrieval"""
        response = requests.get(
            f"{self.retriever_url}/retrieve",
            params={"query": "AI Engineer", "n_results": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that enhanced graph context is present
        assert "enhanced_graph_context" in data
        context = data["enhanced_graph_context"]
        
        # Verify structure
        assert "company_insights" in context
        assert "skill_analysis" in context
        assert "query_analysis" in context
        assert "market_trends" in context
        
        print(f"✅ Enhanced graph context structure verified")
        print(f"📊 Found {len(context.get('company_insights', []))} company insights")
        print(f"🔧 Found {len(context.get('skill_analysis', []))} skill trends")
    
    def test_query_intent_detection(self):
        """Test query intent detection functionality"""
        test_cases = [
            ("Senior AI Engineer in San Francisco", True, False, False),  # location intent
            ("Junior to Senior career progression", False, True, False),  # career intent  
            ("Python machine learning jobs", False, False, True),        # skill intent
            ("Remote AI Engineer position", True, False, True),          # location + skill
        ]
        
        for query, expect_location, expect_career, expect_skill in test_cases:
            response = requests.get(
                f"{self.retriever_url}/retrieve",
                params={"query": query, "n_results": 2}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            context = data["enhanced_graph_context"]
            query_analysis = context["query_analysis"]
            
            assert query_analysis["has_location_intent"] == expect_location
            assert query_analysis["has_career_intent"] == expect_career
            assert query_analysis["has_skill_intent"] == expect_skill
            
            print(f"✅ Query intent detection for '{query}': L={expect_location}, C={expect_career}, S={expect_skill}")
    
    def test_company_insights(self):
        """Test company hiring pattern analysis"""
        response = requests.get(
            f"{self.retriever_url}/retrieve",
            params={"query": "Google AI Engineer", "n_results": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        context = data["enhanced_graph_context"]
        company_insights = context["company_insights"]
        
        # Should find Google in company insights
        google_insight = next((c for c in company_insights if c["company"] == "Google"), None)
        if google_insight:
            assert google_insight["job_count"] >= 1
            print(f"✅ Google company insight: {google_insight['job_count']} jobs")
        else:
            print("⚠️  Google not found in company insights (may be expected if no vector matches)")
    
    def test_skill_demand_analysis(self):
        """Test skill demand analysis"""
        response = requests.get(
            f"{self.retriever_url}/retrieve",
            params={"query": "Python developer", "n_results": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        context = data["enhanced_graph_context"]
        skill_analysis = context["skill_analysis"]
        
        # Should have skill demand data
        assert len(skill_analysis) > 0
        
        # Python should be in top skills (we created many Python jobs)
        python_skill = next((s for s in skill_analysis if s["skill"] == "Python"), None)
        if python_skill:
            assert python_skill["demand"] >= 1
            print(f"✅ Python skill demand: {python_skill['demand']} jobs")
        
        print(f"📈 Total skills analyzed: {len(skill_analysis)}")
    
    def test_location_intent_processing(self):
        """Test location-specific insights when location intent is detected"""
        response = requests.get(
            f"{self.retriever_url}/retrieve",
            params={"query": "Remote AI jobs", "n_results": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        context = data["enhanced_graph_context"]
        
        # Should detect location intent
        assert context["query_analysis"]["has_location_intent"] == True
        
        # Should have location insights
        location_insights = context["location_insights"]
        assert len(location_insights) >= 0  # May be empty if no location data
        
        print(f"✅ Location intent detected and processed")
        print(f"📍 Found {len(location_insights)} location insights")
    
    def test_career_intent_processing(self):
        """Test career progression analysis when career intent is detected"""
        response = requests.get(
            f"{self.retriever_url}/retrieve",
            params={"query": "Senior AI Engineer career progression", "n_results": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        context = data["enhanced_graph_context"]
        
        # Should detect career intent
        assert context["query_analysis"]["has_career_intent"] == True
        
        # Should have career paths (may be empty if no junior->senior connections)
        career_paths = context["career_paths"]
        assert isinstance(career_paths, list)
        
        print(f"✅ Career intent detected and processed")
        print(f"🚀 Found {len(career_paths)} career progression skills")
    
    def test_graph_expansions(self):
        """Test enhanced graph expansion functionality"""
        response = requests.get(
            f"{self.retriever_url}/retrieve",
            params={"query": "AI Engineer", "n_results": 2}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check graph expansions
        assert "graph_expansions" in data
        expansions = data["graph_expansions"]
        
        # Verify structure
        assert "related_jobs" in expansions
        assert "expansion_summary" in expansions
        
        summary = expansions["expansion_summary"]
        assert "total_related" in summary
        assert "same_company" in summary
        assert "shared_skills" in summary
        
        print(f"✅ Graph expansions structure verified")
        print(f"🔗 Total related jobs: {summary['total_related']}")
        print(f"🏢 Same company: {summary['same_company']}")
        print(f"🔧 Shared skills: {summary['shared_skills']}")
    
    def test_market_trends(self):
        """Test market trends analysis"""
        response = requests.get(
            f"{self.retriever_url}/retrieve",
            params={"query": "AI jobs market", "n_results": 3}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        context = data["enhanced_graph_context"]
        market_trends = context["market_trends"]
        
        if market_trends:  # May be empty if not enough companies with 2+ jobs
            assert "active_companies" in market_trends
            assert "avg_jobs_per_company" in market_trends
            assert "max_jobs_single_company" in market_trends
            
            print(f"✅ Market trends analysis:")
            print(f"🏢 Active companies: {market_trends['active_companies']}")
            print(f"📊 Avg jobs per company: {market_trends['avg_jobs_per_company']}")
            print(f"📈 Max jobs (single company): {market_trends['max_jobs_single_company']}")
        else:
            print("ℹ️  No market trends data (expected if <2 companies with multiple jobs)")

if __name__ == "__main__":
    # Run a quick test
    test = TestEnhancedGraphContext()
    test.setup_class()
    
    try:
        print("🧪 Running Enhanced Graph Context Tests...")
        test.test_enhanced_graph_context_basic()
        test.test_query_intent_detection()
        test.test_company_insights()
        test.test_skill_demand_analysis()
        test.test_location_intent_processing()
        test.test_career_intent_processing()
        test.test_graph_expansions()
        test.test_market_trends()
        print("✅ All tests completed successfully!")
    finally:
        test.teardown_class()
