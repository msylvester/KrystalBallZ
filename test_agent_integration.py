
# test_agent_integration.py
import pytest
import os
from unittest.mock import patch, MagicMock
from stream_app import Agent

class TestAgentIntegration:

    def setup_method(self):
        """Setup for each test method"""
        self.agent = Agent()

    def test_agent_initialization(self):
        """Test that Agent initializes correctly with all components"""
        assert self.agent.event_history == []
        assert self.agent.country_service is not None
        assert self.agent.job_service is not None
        assert "country_report" in self.agent.tools
        assert "ai_jobs" in self.agent.tools
        assert self.agent.logger is not None

    def test_agent_country_query_integration(self):
        """Test complete flow for country-related queries"""
        # Test basic country query
        response = self.agent.process_event("Tell me about countries")

        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        assert self.agent.get_event_history()[0] == "Tell me about countries"
        # Should contain country data or error message
        assert isinstance(response, str)

    def test_agent_country_with_region_integration(self):
        """Test country query with specific region"""
        response = self.agent.process_event("Show me countries in Europe")

        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # The agent should extract "europe" as the region
        assert isinstance(response, str)

    def test_agent_job_search_integration(self):
        """Test complete flow for AI job search queries"""
        response = self.agent.process_event("Find AI jobs")

        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        assert self.agent.get_event_history()[0] == "Find AI jobs"
        assert isinstance(response, str)

    def test_agent_job_search_with_location_integration(self):
        """Test job search with specific location"""
        response = self.agent.process_event("Show me AI jobs in New York")

        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # Should extract location and process job search
        assert isinstance(response, str)

    def test_agent_san_francisco_jobs_integration(self):
        """Test special handling for San Francisco jobs"""
        response = self.agent.process_event("Find AI jobs in San Francisco")

        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # Should use special San Francisco handling
        assert isinstance(response, str)

    def test_agent_job_search_with_limit_integration(self):
        """Test job search with custom limit"""
        response = self.agent.process_event("Show 10 jobs in Seattle")

        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # Should extract limit of 10
        assert isinstance(response, str)

    # @patch('openai.OpenAI')
    # def test_agent_gpt_fallback_integration(self, mock_openai):
    #     """Test that non-tool queries fall back to GPT-3.5"""
    #     # Mock OpenAI response
    #     mock_client = MagicMock()
    #     mock_response = MagicMock()
    #     mock_response.choices[0].message.content = "This is a GPT response"
    #     mock_client.chat.completions.create.return_value = mock_response
    #     mock_openai.return_value = mock_client

    #     # Set API key for this test
    #     self.agent.api_key = "test-key"

    #     response = self.agent.process_event("What is the weather like?")

    #     assert response == "This is a GPT response"
    #     assert len(self.agent.get_event_history()) == 1
    #     mock_openai.assert_called_once_with(api_key="test-key")
    #     mock_client.chat.completions.create.assert_called_once()

    def test_agent_no_api_key_error(self):
        """Test behavior when OpenAI API key is not set"""
        # Ensure no API key is set
        self.agent.api_key = ""

        response = self.agent.process_event("What is machine learning?")

        assert "Error: OpenAI API key not set" in response
        assert len(self.agent.get_event_history()) == 1

    # @patch('openai.OpenAI')
    # def test_agent_openai_error_handling(self, mock_openai):
    #     """Test error handling when OpenAI API fails"""
    #     # Mock OpenAI to raise an exception
    #     mock_openai.side_effect = Exception("API Error")

    #     self.agent.api_key = "test-key"
    #     response = self.agent.process_event("Tell me a joke")

    #     assert "Error processing with GPT-3.5" in response
    #     assert "API Error" in response
    #     assert len(self.agent.get_event_history()) == 1

    def test_agent_multiple_events_history(self):
        """Test that event history accumulates correctly"""
        events = [
            "Tell me about countries",
            "Find AI jobs",
            "What is Python?"
        ]

        for event in events:
            self.agent.process_event(event)

        history = self.agent.get_event_history()
        assert len(history) == 3
        assert history == events

    def test_agent_case_insensitive_routing(self):
        """Test that routing works with different cases"""
        test_cases = [
            "TELL ME ABOUT COUNTRIES",
            "find ai JOBS",
            "Show me NATIONS in asia"
        ]

        for event in test_cases:
            response = self.agent.process_event(event)
            assert response is not None
            assert isinstance(response, str)

    def test_agent_tools_accessibility(self):
        """Test that tools are properly accessible through the agent"""
        # Test country tool directly
        country_response = self.agent.tools["country_report"]()
        assert country_response is not None

        # Test job tool directly
        job_response = self.agent.tools["ai_jobs"]()
        assert job_response is not None

    def test_agent_logging_integration(self):
        """Test that logging works correctly during event processing"""
        with patch('logging.getLogger') as mock_logger:
            mock_log_instance = MagicMock()
            mock_logger.return_value = mock_log_instance

            agent = Agent()
            agent.process_event("Test event")

            # Verify logger was called
            mock_logger.assert_called()

    @pytest.mark.parametrize("event,expected_service", [
        ("Tell me about countries", "country"),
        ("Show me nations in Europe", "country"),
        ("Find AI jobs", "job"),
        ("AI job search in NYC", "job"),
        ("What is the capital of France?", "gpt")  # Should fall back to GPT
    ])
    def test_agent_routing_logic(self, event, expected_service):
        """Test that events are routed to the correct service"""
        with patch.object(self.agent, 'tools') as mock_tools:
            mock_tools.__getitem__.return_value = MagicMock(return_value="mocked response")

            if expected_service == "gpt":
                with patch('openai.OpenAI') as mock_openai:
                    mock_client = MagicMock()
                    mock_response = MagicMock()
                    mock_response.choices[0].message.content = "GPT response"
                    mock_client.chat.completions.create.return_value = mock_response
                    mock_openai.return_value = mock_client
                    self.agent.api_key = "test-key"

                    response = self.agent.process_event(event)
                    assert response == "GPT response"
            else:
                response = self.agent.process_event(event)
                assert response == "mocked response"
import pytest
import os
from unittest.mock import patch, MagicMock
from stream_app import Agent

class TestAgentIntegration:
    
    def setup_method(self):
        """Setup for each test method"""
        self.agent = Agent()
    
    def test_agent_initialization(self):
        """Test that Agent initializes correctly with all components"""
        assert self.agent.event_history == []
        assert self.agent.country_service is not None
        assert self.agent.job_service is not None
        assert "country_report" in self.agent.tools
        assert "ai_jobs" in self.agent.tools
        assert self.agent.logger is not None
    
    def test_agent_country_query_integration(self):
        """Test complete flow for country-related queries"""
        # Test basic country query
        response = self.agent.process_event("Tell me about countries")
        
        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        assert self.agent.get_event_history()[0] == "Tell me about countries"
        # Should contain country data or error message
        assert isinstance(response, str)
    
    def test_agent_country_with_region_integration(self):
        """Test country query with specific region"""
        response = self.agent.process_event("Show me countries in Europe")
        
        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # The agent should extract "europe" as the region
        assert isinstance(response, str)
    
    def test_agent_job_search_integration(self):
        """Test complete flow for AI job search queries"""
        response = self.agent.process_event("Find AI jobs")
        
        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        assert self.agent.get_event_history()[0] == "Find AI jobs"
        assert isinstance(response, str)
    
    def test_agent_job_search_with_location_integration(self):
        """Test job search with specific location"""
        response = self.agent.process_event("Show me AI jobs in New York")
        
        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # Should extract location and process job search
        assert isinstance(response, str)
    
    def test_agent_san_francisco_jobs_integration(self):
        """Test special handling for San Francisco jobs"""
        response = self.agent.process_event("Find AI jobs in San Francisco")
        
        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # Should use special San Francisco handling
        assert isinstance(response, str)
    
    def test_agent_job_search_with_limit_integration(self):
        """Test job search with custom limit"""
        response = self.agent.process_event("Show 10 jobs in Seattle")
        
        assert response is not None
        assert len(self.agent.get_event_history()) == 1
        # Should extract limit of 10
        assert isinstance(response, str)
    
    # @patch('openai.OpenAI')
    # def test_agent_gpt_fallback_integration(self, mock_openai):
    #     """Test that non-tool queries fall back to GPT-3.5"""
    #     # Mock OpenAI response
    #     mock_client = MagicMock()
    #     mock_response = MagicMock()
    #     mock_response.choices[0].message.content = "This is a GPT response"
    #     mock_client.chat.completions.create.return_value = mock_response
    #     mock_openai.return_value = mock_client
        
    #     # Set API key for this test
    #     self.agent.api_key = "test-key"
        
    #     response = self.agent.process_event("What is the weather like?")
        
    #     assert response == "This is a GPT response"
    #     assert len(self.agent.get_event_history()) == 1
    #     mock_openai.assert_called_once_with(api_key="test-key")
    #     mock_client.chat.completions.create.assert_called_once()
    
    def test_agent_no_api_key_error(self):
        """Test behavior when OpenAI API key is not set"""
        # Ensure no API key is set
        self.agent.api_key = ""
        
        response = self.agent.process_event("What is machine learning?")
        
        assert "Error: OpenAI API key not set" in response
        assert len(self.agent.get_event_history()) == 1
    
    # @patch('openai.OpenAI')
    # def test_agent_openai_error_handling(self, mock_openai):
    #     """Test error handling when OpenAI API fails"""
    #     # Mock OpenAI to raise an exception
    #     mock_openai.side_effect = Exception("API Error")
        
    #     self.agent.api_key = "test-key"
    #     response = self.agent.process_event("Tell me a joke")
        
    #     assert "Error processing with GPT-3.5" in response
    #     assert "API Error" in response
    #     assert len(self.agent.get_event_history()) == 1
    
    def test_agent_multiple_events_history(self):
        """Test that event history accumulates correctly"""
        events = [
            "Tell me about countries",
            "Find AI jobs",
            "What is Python?"
        ]
        
        for event in events:
            self.agent.process_event(event)
        
        history = self.agent.get_event_history()
        assert len(history) == 3
        assert history == events
    
    def test_agent_case_insensitive_routing(self):
        """Test that routing works with different cases"""
        test_cases = [
            "TELL ME ABOUT COUNTRIES",
            "find ai JOBS",
            "Show me NATIONS in asia"
        ]
        
        for event in test_cases:
            response = self.agent.process_event(event)
            assert response is not None
            assert isinstance(response, str)
    
    def test_agent_tools_accessibility(self):
        """Test that tools are properly accessible through the agent"""
        # Test country tool directly
        country_response = self.agent.tools["country_report"]()
        assert country_response is not None
        
        # Test job tool directly
        job_response = self.agent.tools["ai_jobs"]()
        assert job_response is not None
    
    def test_agent_logging_integration(self):
        """Test that logging works correctly during event processing"""
        with patch('logging.getLogger') as mock_logger:
            mock_log_instance = MagicMock()
            mock_logger.return_value = mock_log_instance
            
            agent = Agent()
            agent.process_event("Test event")
            
            # Verify logger was called
            mock_logger.assert_called()
