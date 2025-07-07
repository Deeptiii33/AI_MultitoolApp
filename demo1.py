# Basic chatbot using Gemini API and streamlit

import streamlit as st
import google.generativeai as ai
from googleapiclient.discovery import build
from datetime import datetime
import base64
import os

# Configure the Generative AI
GOOGLE_API_KEY = "enter your api key"  
api_key = os.getenv("GOOGLE_API_KEY", GOOGLE_API_KEY) # Use environment variable

ai.configure(api_key=api_key)
model = ai.GenerativeModel('gemini-pro')

# Google Custom Search API configuration
SEARCH_API_KEY = "enter your api key" # Your Custom Search API key
SEARCH_ENGINE_ID = "enter your ID" # Your Search Engine ID

# Initialize chatbot and session state variables
if "chatbot" not in st.session_state:
    st.session_state.chatbot = model.start_chat(history=[])

if "history" not in st.session_state:
    st.session_state.history = []

# Streamlit App Title
st.title("🤖 Welcome to Chatbot")

# Sidebar for user settings and options:
with st.sidebar:
    st.header("Settings")
    
    if st.button("Clear Chat History"):
        st.session_state.history = []
        st.success("Chat history cleared!")

    if st.button("Download Chat History"):
        chat_text = "\n".join([f"[{role}] {content}" for role, content in st.session_state.history])
        b64 = base64.b64encode(chat_text.encode()).decode()
        href = f'<a href="data:text/plain;base64,{b64}" download="chat_history.txt">Download Chat History</a>'
        st.markdown(href, unsafe_allow_html=True)
    #st.markdown("This AI chatbot is created by **RAM**")   
    #st.markdown("You can interact with the chatbot, give feedback, and even download the conversation!")

# Helper function to display message
def display_message(role, content):
    if role == "human":
        st.chat_message("human").write(content)
    else:
        st.chat_message("ai").write(content)

# Helper function to perform image search
def image_search(query):
    resource = build("customsearch", "v1", developerKey=SEARCH_API_KEY).cse()
    result = resource.list(q=query, cx=SEARCH_ENGINE_ID, searchType="image", num=1).execute()
    return result

# Display conversation history
for role, content in st.session_state.history:
    display_message(role, content)

# Input for user prompt
user_prompt = st.chat_input("Type your message here...")

# Handle user input and AI response
if user_prompt:
    # Display user's message
    display_message("human", user_prompt)
    st.session_state.history.append(("human", user_prompt))

    # Generate AI response with a loading indicator
    with st.spinner("Generating Response..."):
        try:
            response = st.session_state.chatbot.send_message(user_prompt)
            ai_response = response.text if response.text else "I'm not sure how to respond to that."

            # Perform image search
            if 'image search' in user_prompt.lower():
                query = user_prompt.lower().replace('image search', '').strip()
                search_result = image_search(query)
                if "items" in search_result:
                    image_url = search_result["items"][0]["link"]
                    st.image(image_url, width=400)
                    ai_response = f"Here is an image result for your search: {query}"
                else:
                    ai_response = "I couldn't find any images for your search."
                    
        except Exception as e:
            ai_response = f"An error occurred: {str(e)}"

    # Display AI's message
    display_message("ai", ai_response)
    st.session_state.history.append(("ai", ai_response))
    
    # Provide feedback option
    feedback = st.text_input("Give feedback on this response (optional):")
    if feedback:
        st.success("Thank you for your feedback!")
