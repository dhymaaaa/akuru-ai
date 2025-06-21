import json
import os
import re
import google.generativeai as genai
from dotenv import load_dotenv
from flask import Response, current_app

# Load environment variables
load_dotenv()

# Get the Gemini API key from the environment variables
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

# Configure the Gemini API 
genai.configure(api_key=api_key)

# Initialize model globally for reuse
model = genai.GenerativeModel('gemini-2.0-flash')

# System instruction for the Gemini model
SYSTEM_INSTRUCTION = """
You are Akuru, a friendly and patient Dhivehi language learning assistant. Your name is Akuru and you are specifically designed to help users learn Dhivehi in a supportive, encouraging way.

Key guidelines:
- Your name is Akuru - introduce yourself when appropriate and respond when users ask your name
- Always be enthusiastic and supportive about language learning
- Never reference previous conversations or mention if a question was asked before
- Treat each question as fresh and new, even if it's repetitive
- Vary your responses naturally - don't always start with the same phrases
- Be patient with learners who ask the same things multiple times
- Focus on being helpful rather than efficient but still focus on efficiency

CRITICAL FORMATTING RULE: 
2. Do NOT use "بالکل" or any Arabic/Urdu words in the Dhivehi section
3. Do NOT use "ච්", "ච", "තේරුම්" or any Sinhala words in the Dhivehi section
4. Do NOT use "മനസ്സിലാ" or any Malayalam words in the Dhivehi section

IMPORTANT: Format your responses with English first, followed by a newline, then PURE Dhivehi (no Arabic or urdu words mixed in):

[English response here]

[Dhivehi response here]

Example interaction:
User: "What is your name?"
Assistant: "Hi there! My name is Akuru, and I'm here to help you learn Dhivehi! It's wonderful to meet you.

އަހަރެންގެ ނަމަކީ އަކުރެވެ، އަދި އަހަރެން ހުރީ ތިބާއަށް ދިވެހިބަސް ދަސްކުރުވަން ތައްޔާރަށެވެ."

User: "What is the Dhivehi word for unique?"
Assistant: "The word for 'unique' is 'ލާސާނީ' (lāsānī) in Dhivehi. It's a beautiful word!

'ޔުނީކް' އަށް ދިވެހިބަހުން ކިޔަނީ 'ލާސާނީ' އެވެ."

WRONG example (do NOT do this):
"ތިޔަބުނަނީ بالکل ރަނގަޅު ވާހަކައެކެވެ! ޝުކުރިއްޔާ!" 

CORRECT example:
"ތިޔަ ބުނަނީ ވަރަށް ރަނގަޅު ވާހަކައެކެވެ! ޝުކުރިއްޔާ!" 
"""

def initialize_chat_session():
    """Initialize and return a new chat session with the model."""
    return model.start_chat(history=[
        {"role": "user", "parts": ["Please act as a friendly Dhivehi language learning assistant with the following instructions:"]},
        {"role": "model", "parts": ["I'm excited to help you learn Dhivehi! I'll be your friendly and patient language learning companion."]},
        {"role": "user", "parts": [SYSTEM_INSTRUCTION]},
        {"role": "model", "parts": ["Perfect! I understand. I'll be a friendly, enthusiastic Dhivehi language learning assistant. I'll treat every question as new and exciting, encourage repetition as part of learning, and always respond with both English and Dhivehi. I'm here to make your language learning journey enjoyable! What would you like to learn today?"]}
    ])

def clean_dhivehi_text(text):
    """
    Clean the Dhivehi text by removing non-Dhivehi characters and common foreign words.
    
    Args:
        text: The text to clean
        
    Returns:
        Cleaned text with only Dhivehi characters, English letters, numbers, and basic punctuation
    """
    # Define allowed character ranges
    dhivehi_range = r'\u0780-\u07BF'  # Dhivehi/Thaana script
    english_range = r'a-zA-Z'  # English letters
    numbers = r'0-9'  # Numbers
    basic_punctuation = r'.,!?؛،\s()\[\]"\'`'  # Basic punctuation including Arabic punctuation
    
    # Combine all allowed characters
    allowed_pattern = f'[{dhivehi_range}{english_range}{numbers}{basic_punctuation}]'
    
    # Remove characters that are NOT in the allowed ranges
    cleaned_text = re.sub(f'[^{dhivehi_range}{english_range}{numbers}{basic_punctuation}]', '', text)
    
    # Define common foreign words to replace with Dhivehi equivalents
    replacements = {
        'بالکل': 'ހަމަ',  # Arabic "bilkul" -> Dhivehi "hama" (exactly/completely)
        'ޝުކުރިއްޔާ': 'ޝުކުރު',  # Arabic "shukuriyyaa" -> simpler Dhivehi "shukuru" 
        'ތަންކިޔޫ': 'ޝުކުރިއްޔާ',  # English "thank you" -> Dhivehi "shukuru"
        'ސޮރީ': 'މާފުކުރައްވާ',  # English "sorry" -> Dhivehi "maafukuravvaa"
    }
    
    # Apply replacements
    for foreign_word, dhivehi_word in replacements.items():
        cleaned_text = cleaned_text.replace(foreign_word, dhivehi_word)
    
    return cleaned_text

def initialize_chat_session():
    """Initialize and return a new chat session with the model."""
    return model.start_chat(history=[
        {"role": "user", "parts": ["Please act as a friendly Dhivehi language learning assistant with the following instructions:"]},
        {"role": "model", "parts": ["I'm excited to help you learn Dhivehi! I'll be your friendly and patient language learning companion."]},
        {"role": "user", "parts": [SYSTEM_INSTRUCTION]},
        {"role": "model", "parts": ["Perfect! I understand. I'll be a friendly, enthusiastic Dhivehi language learning assistant. I'll treat every question as new and exciting, encourage repetition as part of learning, and always respond with both English and Dhivehi. I'm here to make your language learning journey enjoyable! What would you like to learn today?"]}
    ])

def get_gemini_response_stream(messages):
    """
    Get a streaming response from Gemini with improved error handling.
    This follows the same pattern as your console chatbot.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
    
    Yields:
        Dictionary with 'chunk' key containing the text chunk
    """
    try:
        # Create a new chat session
        chat = initialize_chat_session()
        
        # Add all previous messages to build context
        for message in messages[:-1]:  # All except the last message
            if message['role'] == 'user':
                try:
                    chat.send_message(message['content'])
                except Exception as e:
                    current_app.logger.error(f"Error adding message to context: {e}")
                    # Continue anyway, might still work
        
        # Stream the response for the last message (following your console pattern)
        if messages and messages[-1]['role'] == 'user':
            try:
                # Use stream=True for streaming response - same as your console version
                response_stream = chat.send_message(messages[-1]['content'], stream=True)
                
                dhivehi_section_started = False
                
                # Iterate through chunks - same pattern as your console version
                for chunk in response_stream:
                    if chunk.text:
                        # Check if we've hit the transition to Dhivehi
                        dhivehi_pattern = re.compile(r'[\u0780-\u07BF]')
                        dhivehi_match = dhivehi_pattern.search(chunk.text)
                        
                        if dhivehi_match and not dhivehi_section_started:
                            # We've hit the Dhivehi section
                            dhivehi_section_started = True
                            
                            # Send a marker to indicate section change
                            yield {
                                'chunk': '',
                                'section_change': True,
                                'section': 'dhivehi'
                            }
                        
                        # Process the chunk based on current section
                        if dhivehi_section_started:
                            # Clean the chunk for Dhivehi section
                            cleaned_chunk = clean_dhivehi_text(chunk.text)
                            if cleaned_chunk.strip():  # Only yield non-empty chunks
                                yield {
                                    'chunk': cleaned_chunk,
                                    'section': 'dhivehi'
                                }
                        else:
                            # English section - send as is
                            if chunk.text.strip():  # Only yield non-empty chunks
                                yield {
                                    'chunk': chunk.text,
                                    'section': 'english'
                                }
                
            except Exception as e:
                current_app.logger.error(f"Error in streaming response: {e}")
                yield {
                    'chunk': f"I apologize, but I encountered an error while generating the response: {str(e)}",
                    'section': 'error',
                    'error': True
                }
        else:
            yield {
                'chunk': "I'm sorry, I couldn't process that request correctly.",
                'section': 'error',
                'error': True
            }
            
    except Exception as e:
        current_app.logger.error(f"Error communicating with Gemini API: {e}")
        yield {
            'chunk': f"I apologize, but I encountered an error: {str(e)}",
            'section': 'error',
            'error': True
        }

def get_gemini_response_stream_flask(messages):
    """
    Flask-compatible streaming response generator with better error handling.
    
    Args:
        messages: List of message dictionaries
    
    Returns:
        Flask Response object for streaming
    """
    def generate():
        try:
            for chunk_data in get_gemini_response_stream(messages):
                # Send as Server-Sent Events (SSE) format
                yield f"data: {json.dumps(chunk_data)}\n\n"
        except Exception as e:
            # Send error as final message
            error_data = {
                'chunk': f"Sorry, I encountered an error: {str(e)}",
                'section': 'error',
                'error': True
            }
            yield f"data: {json.dumps(error_data)}\n\n"
        finally:
            # Send end-of-stream marker
            end_data = {'end_of_stream': True}
            yield f"data: {json.dumps(end_data)}\n\n"
    
    return Response(
        generate(),
        mimetype='text/plain',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
            'Access-Control-Allow-Origin': 'http://localhost:5173',  # CORS for streaming
            'Access-Control-Allow-Credentials': 'true'
        }
    )

def process_conversation_messages(conversation_id, db_module):
    """
    Process all messages for a conversation and return Gemini-compatible format.
    
    Args:
        conversation_id: ID of the conversation
        db_module: Database module for fetching messages
        
    Returns:
        List of message dictionaries with 'role' and 'content' keys
    """
    db_messages = db_module.get_messages(conversation_id)
    
    # Convert DB messages to Gemini format
    gemini_messages = []
    for msg in db_messages:
        # Map 'akuru' role to 'assistant' for compatibility with standard conventions
        role = 'assistant' if msg['role'] == 'akuru' else msg['role']
        gemini_messages.append({
            'role': role,
            'content': msg['content']
        })
    
    return gemini_messages
