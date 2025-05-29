import streamlit as st
import openai
import os

class Agent:
    def __init__(self):
        self.event_history = []
        # Get API key from environment variable or let user input it
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
    
    def process_event(self, event):
        """Process an incoming event using GPT-3 and return a response"""
        self.event_history.append(event)
        
        if not self.api_key:
            return "Error: OpenAI API key not set"
        
        try:
            openai.api_key = self.api_key
            response = openai.Completion.create(
                engine="text-davinci-003",  # GPT-3 model
                prompt=f"User input: {event}\nResponse:",
                max_tokens=150,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            ai_response = response.choices[0].text.strip()
            return ai_response
        except Exception as e:
            return f"Error processing with GPT-3: {str(e)}"
    
    def get_event_history(self):
        """Return the history of processed events"""
        return self.event_history

def main():
    st.title("GPT-3 Powered Agent App")
    
    # Initialize the agent in session state if it doesn't exist
    if 'agent' not in st.session_state:
        st.session_state.agent = Agent()
    
    # API Key input
    api_key = st.sidebar.text_input("OpenAI API Key", st.session_state.agent.api_key, type="password")
    if api_key:
        st.session_state.agent.api_key = api_key
    
    # Display event history
    if st.session_state.agent.get_event_history():
        st.subheader("Event History")
        for i, event in enumerate(st.session_state.agent.get_event_history()):
            st.text(f"{i+1}. {event}")
    
    # Input form
    user_input = st.text_input("Enter event data", "")
    if st.button("Submit Event"):
        if user_input:
            response = st.session_state.agent.process_event(user_input)
            st.success(response)
        else:
            st.warning("Please enter event data")

if __name__ == '__main__':
    main()
