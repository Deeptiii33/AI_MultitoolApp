# Generates results from the wikipedia

from dotenv import load_dotenv
import streamlit as st
import os
import wikipedia

# Load environment variables
load_dotenv()

# Function to get response from Wikipedia
def get_wikipedia_response(question):
    try:
        summary = wikipedia.summary(question, sentences=3)
        return summary
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Disambiguation error: {e.options}"
    except wikipedia.exceptions.PageError:
        return "Page not found"
    except Exception as e:
        return f"An error occurred: {e}"

# Streamlit app setup
st.set_page_config(page_title="Chatbot")
st.header("Welcome to my chatbot")

# User input and response display
if "input_text" not in st.session_state:
    st.session_state.input_text = ""

input_text = st.text_input("Input:", st.session_state.input_text)

if st.button("Get Response") and input_text:
    response = get_wikipedia_response(input_text)
    st.subheader("The Response is")
    st.write(response)
