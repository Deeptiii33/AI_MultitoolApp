# Voice Assistant powered by Google Speech Recognition and Gemini AI, PDF analysis, image analysis

import streamlit as st
import google.generativeai as ai
import fitz  # PyMuPDF
import requests
from googleapiclient.discovery import build
from datetime import datetime
from PIL import Image
from io import BytesIO
import base64
import os
import speech_recognition as sr
import tempfile
import numpy as np
import pyaudio
import wave
import threading
import time
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(page_title="AI Voice Assistant", layout="wide")

# Configure the Generative AI
GOOGLE_API_KEY = "Enter your gemini api key here"
api_key = os.getenv("GOOGLE_API_KEY", GOOGLE_API_KEY)
ai.configure(api_key=api_key)
model = ai.GenerativeModel('gemini-pro')
vision_model = ai.GenerativeModel('gemini-pro-vision')

# Initialize session state
if "chatbot" not in st.session_state:
    st.session_state.chatbot = model.start_chat(history=[])
if "history" not in st.session_state:
    st.session_state.history = []
if "recording" not in st.session_state:
    st.session_state.recording = False

# Main title
st.title("🎙️ AI Voice Assistant")
st.markdown("""
This AI assistant can:
- Listen to your voice commands
- Process PDFs and images
- Engage in voice conversations
- Provide real-time responses
""")

class VoiceRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.stream = None
        self.is_recording = False
        
    def start_recording(self):
        self.frames = []
        self.is_recording = True
        
        def record():
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=1024
            )
            
            while self.is_recording:
                data = self.stream.read(1024)
                self.frames.append(data)
        
        self.record_thread = threading.Thread(target=record)
        self.record_thread.start()
    
    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        # Wait for recording thread to finish
        if hasattr(self, 'record_thread'):
            self.record_thread.join()
        
        # Save recording to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            wf = wave.open(temp_audio.name, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            return temp_audio.name

def process_voice_command(audio_file_path):
    """Convert speech to text and process command"""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text
    except Exception as e:
        return f"Error processing voice: {str(e)}"

def process_pdf(pdf_file):
    """Process PDF and extract text/images"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf.write(pdf_file.read())
            temp_pdf_path = temp_pdf.name
        
        doc = fitz.open(temp_pdf_path)
        text = ""
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text()
            
            for img in enumerate(page.get_images()):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(BytesIO(image_bytes))
                images.append(image)
        
        doc.close()
        os.unlink(temp_pdf_path)
        
        return text, images
    except Exception as e:
        return f"Error processing PDF: {str(e)}", []

def analyze_image(image):
    """Analyze image using AI"""
    try:
        if isinstance(image, bytes):
            image = Image.open(BytesIO(image))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        response = vision_model.generate_content([
            "Analyze this image in detail",
            image
        ])
        return response.text if response.text else "Could not analyze image."
    except Exception as e:
        return f"Error analyzing image: {str(e)}"

# Sidebar for tool selection
with st.sidebar:
    st.header("Tools & Settings")
    tool_choice = st.radio(
        "Choose Tool:",
        ["Voice Assistant", "PDF Analysis", "Image Analysis"]
    )

# Main interface based on tool selection
if tool_choice == "Voice Assistant":
    st.header("Voice Interaction")
    
    # Initialize voice recorder
    if "voice_recorder" not in st.session_state:
        st.session_state.voice_recorder = VoiceRecorder()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Start/Stop recording button
        if not st.session_state.recording:
            if st.button("🎙️ Start Listening"):
                st.session_state.recording = True
                st.session_state.voice_recorder.start_recording()
                st.rerun()
        else:
            if st.button("⏹️ Stop Listening"):
                st.session_state.recording = False
                audio_file_path = st.session_state.voice_recorder.stop_recording()
                
                # Process voice command
                with st.spinner("Processing voice command..."):
                    command = process_voice_command(audio_file_path)
                    st.success(f"You said: {command}")
                    
                    # Get AI response
                    response = st.session_state.chatbot.send_message(command)
                    st.write("AI Response:", response.text if response.text else "Could not generate response.")
                    
                    # Add to history
                    st.session_state.history.append(("human", command))
                    st.session_state.history.append(("ai", response.text))
                
                st.rerun()
    
    with col2:
        # Recording status indicator
        if st.session_state.recording:
            st.markdown("🔴 Recording...")
        #else:
            #st.markdown("⚪ Not recording")
    
    # Display conversation history
    st.subheader("Conversation History")
    for role, content in st.session_state.history:
        with st.chat_message(role):
            st.write(content)

elif tool_choice == "PDF Analysis":
    st.header("PDF Analysis")
    uploaded_pdf = st.file_uploader("Upload PDF", type=['pdf'])
    
    if uploaded_pdf:
        with st.spinner("Analyzing PDF..."):
            text, images = process_pdf(uploaded_pdf)
            
            if isinstance(text, str) and not text.startswith("Error"):
                st.subheader("Text Content")
                with st.expander("Show extracted text"):
                    st.text(text)
                
                # Analyze text content
                analysis_prompt = f"Summarize this document: {text[:8000]}"
                analysis = st.session_state.chatbot.send_message(analysis_prompt)
                
                st.subheader("Summary")
                st.write(analysis.text if analysis.text else "Could not generate summary.")
                
                # Display and analyze images
                if images:
                    st.subheader(f"Found {len(images)} images")
                    for idx, img in enumerate(images):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.image(img, caption=f"Image {idx+1}")
                        with col2:
                            st.write(analyze_image(img))
            else:
                st.error(text)

else:  # Image Analysis
    st.header("Image Analysis")
    image_source = st.radio("Choose image source:", ["Upload Image", "Image URL"])
    
    if image_source == "Upload Image":
        uploaded_image = st.file_uploader("Upload image", type=['png', 'jpg', 'jpeg'])
        if uploaded_image:
            st.image(uploaded_image)
            with st.spinner("Analyzing image..."):
                analysis = analyze_image(uploaded_image.getvalue())
                st.write(analysis)
    else:
        image_url = st.text_input("Enter image URL:")
        if image_url:
            try:
                response = requests.get(image_url)
                image = Image.open(BytesIO(response.content))
                st.image(image_url)
                with st.spinner("Analyzing image..."):
                    analysis = analyze_image(image)
                    st.write(analysis)
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("Voice Assistant powered by Google Speech Recognition and Gemini AI")
