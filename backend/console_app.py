import os
from dotenv import load_dotenv
from datetime import datetime
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import signal
import sys

# Load environment variables
load_dotenv()

# Get HF token from environment variables
hf_token = os.getenv("HF_TOKEN")

if not hf_token:
    raise ValueError("HF_TOKEN environment variable not set.")

# Comment out this line to disable file logging
ENABLE_FILE_LOGGING = False  # Set to False or comment out to disable file logging

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
        if role == "Model":
            file.write("\n")
        file.flush()

# Setup signal handler for graceful exit with Ctrl+C
def signal_handler(sig, frame):
    print("\nExiting chat bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

class CustomModelChat:
    """Class to handle interactions with your custom Gemma 3 model."""
    
    def __init__(self, system_instruction=None, model_path="backend/models/gemma3/dhivehi-gemma-3-1b"):
        """Initialize your model here."""
        print(f"Loading model from {model_path}")
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            token=hf_token
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"
        
        # Load the fine-tuned model with optimizations
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            token=hf_token,
            device_map="auto",
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True  # Optimize memory usage
        )
        
        # Put model in evaluation mode
        self.model.eval()
        
        # Cache for storing generated responses
        self.response_cache = {}
        
        # Initialize chat history
        self.history = []
        
        # Define generation config once
        self.generation_config = {
            "max_new_tokens": 256,  # Reduced for faster response
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 50,
            "do_sample": True,
            "pad_token_id": self.tokenizer.eos_token_id,
        }
        
        # Add system instruction if provided
        if system_instruction:
            self.history.append({"role": "user", "parts": ["Please act as a helpful assistant with the following instructions:"]})
            self.history.append({"role": "model", "parts": ["I'll act as a helpful assistant based on your instructions."]})
            self.history.append({"role": "user", "parts": [system_instruction]})
            self.history.append({"role": "model", "parts": ["I understand. I'll be a helpful assistant that provides concise, accurate responses while maintaining context throughout our conversation."]})
    
    def send_message(self, prompt, stream=False):
        """Process user input and generate a response using your custom model."""
        # Add user message to history
        self.history.append({"role": "user", "parts": [prompt]})
        
        # Prepare input for your model based on history
        input_text = self._prepare_model_input()
        
        # Check if we have this exact prompt in cache
        cache_key = input_text[-200:]  # Use the last 200 chars as cache key (most relevant part)
        if cache_key in self.response_cache:
            response = self.response_cache[cache_key]
            # If we want streaming, convert cached response to streaming format
            if stream:
                streaming_response = StreamingResponse(response)
                self.history.append({"role": "model", "parts": [response]})
                return streaming_response
            else:
                self.history.append({"role": "model", "parts": [response]})
                return response
        
        # Generate response from your model
        response = self._generate_response(input_text, stream)
        
        # Add model response to history
        if not stream:
            self.response_cache[cache_key] = response
            self.history.append({"role": "model", "parts": [response]})
        else:
            self.response_cache[cache_key] = response.full_text
            self.history.append({"role": "model", "parts": [response.full_text]})
        
        return response
    
    def _prepare_model_input(self):
        """Convert conversation history to ChatML format for Gemma 3."""
        # Format following the ChatML format used in training
        formatted_text = "<start>\n"
        
        for i, message in enumerate(self.history):
            role = message["role"]
            content = message["parts"][0]
            
            if role == "user":
                # For Dhivehi response, add instruction to first user message
                if i == 0:
                    content = "ޖަވާބު ދިވެހިބަހުން ދޭށެވެ (Please respond in Dhivehi)\n" + content
                formatted_text += f"user: {content}\n"
            elif role == "model":
                formatted_text += f"assistant: {content}\n"
        
        # Limit context length to avoid exceeding model's capabilities
        # Keeping the last 1500 characters which should be most relevant
        if len(formatted_text) > 1500:
            formatted_text = formatted_text[-1500:]
            # Make sure we have a complete message by finding the first "user:" or "assistant:"
            first_role = formatted_text.find("user:")
            if first_role == -1:
                first_role = formatted_text.find("assistant:")
            if first_role > 0:
                formatted_text = formatted_text[first_role:]
        
        return formatted_text
    
    def _generate_response(self, input_text, stream=False):
        """Generate a response from your Gemma 3 model."""
        try:
            # Tokenize the input
            inputs = self.tokenizer(input_text, return_tensors="pt").to(self.model.device)
            
            # Generate response
            if not stream:
                # For non-streaming response
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        **self.generation_config
                    )
                
                # Decode the response
                generated_text = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
                
                # Extract assistant's response
                if "assistant:" in generated_text:
                    response = generated_text.split("assistant:")[1].split("<")[0]
                else:
                    response = generated_text.split("<")[0]
                
                return response.strip()
            else:
                # For streaming, we'll simulate streaming with batch generation then chunking
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        **self.generation_config
                    )
                
                # Decode the response
                generated_text = self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
                
                # Extract assistant's response
                if "assistant:" in generated_text:
                    response = generated_text.split("assistant:")[1].split("<")[0]
                else:
                    response = generated_text.split("<")[0]
                
                response = response.strip()
                
                # Return streaming response object
                return StreamingResponse(response)
        except Exception as e:
            print(f"Error generating response: {e}")
            return "Sorry, I encountered an error while generating a response." if not stream else StreamingResponse("Sorry, I encountered an error while generating a response.")

class StreamingResponse:
    """Class to simulate streaming responses from your custom model."""
    
    def __init__(self, text):
        self.text = text
        self.chunks = [text[i:i+5] for i in range(0, len(text), 5)]  # Split into chunks of 5 chars
        self.full_text = text
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if not self.chunks:
            raise StopIteration
        chunk = self.chunks.pop(0)
        return StreamingChunk(chunk)

class StreamingChunk:
    """Class to represent a chunk of streaming response."""
    
    def __init__(self, text):
        self.text = text

def get_custom_model_streaming_response(chat_session, prompt, log_file=None):
    """Gets a streaming response from your custom model using chat history."""
    try:
        # Write user query to file if logging is enabled
        write_to_log(log_file, "User", prompt)
        
        # Add user message to chat history and get response
        response = chat_session.send_message(prompt, stream=True)
        
        full_response = ""
        print("Model: ", end="", flush=True)
        
        # Start model response in file if logging is enabled
        if log_file:
            log_file.write("Model: ")
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
        error_msg = f"Error communicating with custom model: {e}"
        print(error_msg)
        write_to_log(log_file, "System", f"Error: {e}")
        return None

def chat_bot():
    """Starts the chat bot interaction with memory."""
    print("Welcome to a conversation with Dhivehi Gemma 3 AI\n\n")
    print("Loading model... Please wait, this may take a minute...")
    
    # Define the precontext/system message
    system_instruction = """
    You are a helpful assistant that responds in Dhivehi. You provide concise, accurate, and helpful responses.
    You maintain context throughout the conversation and refer back to previous messages when appropriate.
    If you don't know the answer to something, you acknowledge that instead of making things up.
    """
    
    try:
        # Initialize the chat session with your custom model and system instruction
        chat_session = CustomModelChat(system_instruction=system_instruction)
        print("Model loaded successfully!")
    except Exception as e:
        print(f"Error loading model: {e}")
        print("Make sure the model path is correct and HF_TOKEN is set properly.")
        return
    
    # Get log file if logging is enabled
    log_file = get_log_file()
    
    try:
        while True:
            user_input = input("User: ")
            
            # Check for exit command - strip any leading characters like ':'
            if user_input.lstrip(':').lower() in ["exit", "quit", "bye", "q"]:
                print("Goodbye!")
                write_to_log(log_file, "User", user_input)
                write_to_log(log_file, "Model", "Goodbye!")
                break
            
            get_custom_model_streaming_response(chat_session, user_input, log_file)
    
    except KeyboardInterrupt:
        print("\nExiting chat bot...")
    finally:
        # Close log file if it was opened
        if log_file:
            log_file.close()

if __name__ == "__main__":
    chat_bot()