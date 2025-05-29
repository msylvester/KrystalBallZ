import streamlit as st
from openai import OpenAI
import os

class Agent:
    def __init__(self):
        self.event_history = []
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
    
    def process_event(self, event):
        """Process an incoming event using GPT-3.5 and return a response"""
        self.event_history.append(event)
        
        if not self.api_key:
            return "Error: OpenAI API key not set"
        
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": event}
                ],
                max_tokens=150,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            ai_response = response.choices[0].message.content.strip()
            return ai_response
        except Exception as e:
            return f"Error processing with GPT-3.5: {str(e)}"
    
    def get_event_history(self):
        return self.event_history

def main():
    st.title("GPT-3.5 Powered Agent App")

    if 'agent' not in st.session_state:
        st.session_state.agent = Agent()
    
    api_key = st.sidebar.text_input(
        "OpenAI API Key", 
        value=st.session_state.agent.api_key, 
        type="password"
    )
    if api_key:
        st.session_state.agent.api_key = api_key

    if st.session_state.agent.get_event_history():
        st.subheader("Event History")
        for i, event in enumerate(st.session_state.agent.get_event_history()):
            st.text(f"{i + 1}. {event}")

    user_input = st.text_input("Enter event data", "")
    if st.button("Submit Event"):
        if user_input:
            response = st.session_state.agent.process_event(user_input)
            st.success(response)
        else:
            st.warning("Please enter event data")

if __name__ == '__main__':
    main()
