import os
import sys
import signal
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime

# Load environment variables
load_dotenv()

# Get the Gemini API key from the environment variables
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# Configure the Gemini API 
genai.configure(api_key=api_key)

# Comment out this line to disable file logging
ENABLE_FILE_LOGGING = False  # Set to False or comment out to disable file logging

# Setup signal handler for graceful exit with Ctrl+C
def signal_handler(sig, frame):
    print("\nExiting chat bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def get_log_file():
    """Returns the file handle for logging, or None if logging is disabled."""
    if not ENABLE_FILE_LOGGING:
        return None
    
    file_path = "response.txt"
    return open(file_path, "a", encoding="utf-8")

def write_to_log(file, role, text):
    """Write to log file if logging is enabled."""
    if file:
        file.write(f"{role}: {text}\n")
        if role == "Gemini":
            file.write("\n")
        file.flush()

def get_gemini_streaming_response(chat_session, prompt, log_file=None):
    """Gets a streaming response from the Gemini API using chat history."""
    try:
        # Write user query to file if logging is enabled
        write_to_log(log_file, "User", prompt)
        
        # Add user message to chat history and get response
        response = chat_session.send_message(prompt, stream=True)
        
        full_response = ""
        print("Gemini: ", end="", flush=True)
        
        # Start Gemini response in file if logging is enabled
        if log_file:
            log_file.write("Gemini: ")
            log_file.flush()
        
        for chunk in response:
            if chunk.text:
                # Print to console
                print(chunk.text, end="", flush=True)
                
                # Write to file if logging is enabled
                if log_file:
                    log_file.write(chunk.text)
                    log_file.flush()
                
                full_response += chunk.text
        
        # Add newline after complete response
        print()
        if log_file:
            log_file.write("\n\n")
            log_file.flush()
        
        return full_response
        
    except Exception as e:
        error_msg = f"Error communicating with Gemini API: {e}"
        print(error_msg)
        write_to_log(log_file, "System", f"Error: {e}")
        return None

def chat_bot():
    """Starts the chat bot interaction with memory."""
    print("Welcome to a conversation with Akuru AI\n\n")
    
    # Define the precontext/system message
    system_instruction = """
    You are a helpful assistant. You provide concise, accurate, and helpful responses.
    You maintain context throughout the conversation and refer back to previous messages when appropriate.
    If you don't know the answer to something, you acknowledge that instead of making things up.
    """
    
    # Initialize the chat session with the model and system instruction
    model = genai.GenerativeModel('gemini-2.0-flash')
    chat_session = model.start_chat(history=[
        {"role": "user", "parts": ["Please act as a helpful assistant with the following instructions:"]},
        {"role": "model", "parts": ["I'll act as a helpful assistant based on your instructions."]},
        {"role": "user", "parts": [system_instruction]},
        {"role": "model", "parts": ["I understand. I'll be a helpful assistant that provides concise,\
            accurate responses while maintaining context throughout our conversation. I'll refer back to \
            previous messages when appropriate, and I'll be honest when I don't know something instead \
            of making up information. How can I help you today?"]}
    ])
    
    # Get log file if logging is enabled
    log_file = get_log_file()
    
    try:
        while True:
            user_input = input("User: ")
            
            # Check for exit command
            if user_input.lower() in ["exit", "quit", "bye", "q"]:
                print("Goodbye!")
                write_to_log(log_file, "User", user_input)
                write_to_log(log_file, "Gemini", "Goodbye!")
                break
            
            get_gemini_streaming_response(chat_session, user_input, log_file)
    
    finally:
        # Close log file if it was opened
        if log_file:
            log_file.close()

if __name__ == "__main__":
    chat_bot()