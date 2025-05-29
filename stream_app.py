import streamlit as st

def main():
    st.title("Streamlit App")
    user_input = st.text_input("Enter input data", "")
    if st.button("Submit"):
         st.write("Button clicked!")
         st.write("User input:", user_input)

if __name__ == '__main__':
    main()
