import streamlit as st

class Agent:
    def __init__(self):
        self.event_history = []
    
    def process_event(self, event):
        """Process an incoming event and return a response"""
        self.event_history.append(event)
        return f"Processed: {event}"
    
    def get_event_history(self):
        """Return the history of processed events"""
        return self.event_history

def main():
    st.title("Agent-Driven Streamlit App")
    
    # Initialize the agent in session state if it doesn't exist
    if 'agent' not in st.session_state:
        st.session_state.agent = Agent()
    
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
