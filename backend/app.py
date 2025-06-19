from flask import Flask, request, jsonify, session, Response
from flask_cors import CORS
from flask_session import Session
import bcrypt
import jwt
import uuid
import datetime
import os
from dotenv import load_dotenv
import json
import db 
import gemini_integration  
from dialect_middleware import DialectMiddleware
from dict_middleware import DictionaryMiddleware

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Enable CORS 
CORS(app, resources={r"/api/*": {
    "origins": ["http://localhost:5173"],  # Vite's default port
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True
}})

# Secret key for JWT
SECRET_KEY = os.getenv('SECRET_KEY')

# ADD THE SESSION CONFIGURATION HERE:
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_FILE_DIR'] = './flask_session'

# Initialize session
Session(app)

# Initialize database
db.setup_database()

# Initialize dialect middleware
dialect_middleware = DialectMiddleware()
dict_middleware = DictionaryMiddleware()

def generate_conversation_title(content):
    """Generate a conversation title from the first message"""
    # Remove extra whitespace and limit length
    content = content.strip()
    
    # If message is short enough, use it as title
    if len(content) <= 50:
        return content
    
    # For longer messages, take first 47 characters and add ellipsis
    return content[:47] + "..."

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401

# Middleware to protect routes
def token_required(f):
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            # You can attach user to request here if needed
            # request.user = data
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(*args, **kwargs)
    
    # Preserve the original function name to prevent endpoint conflicts
    decorated.__name__ = f.__name__
    return decorated

# AUTHENTICATED USER STREAMING ENDPOINT (unchanged)
@app.route('/api/chat/stream', methods=['POST'])
@token_required
def chat_stream():
    """
    Streaming chat endpoint that returns response chunks as they're generated.
    """
    try:
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            return jsonify({'error': 'conversation_id is required'}), 400
        
        # Verify conversation exists and user has access
        token = request.headers.get('Authorization')
        token = token[7:] if token.startswith('Bearer ') else token
        
        try:
            jwt_data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user_id = jwt_data['user_id']
            
            # Verify user owns this conversation
            conversations = db.get_conversations(user_id)
            conversation_exists = any(conv['id'] == conversation_id for conv in conversations)
            
            if not conversation_exists:
                return jsonify({'error': 'Conversation not found or access denied'}), 404
                
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get conversation messages
        messages = gemini_integration.process_conversation_messages(conversation_id, db)
        
        if not messages:
            return jsonify({'error': 'No messages found'}), 400
        
        # Return streaming response
        return gemini_integration.get_gemini_response_stream_flask(messages)
        
    except Exception as e:
        app.logger.error(f"Error in chat_stream: {str(e)}")
        return jsonify({'error': str(e)}), 500

# NEW: GUEST USER STREAMING ENDPOINT
@app.route('/api/guest/stream', methods=['POST'])
def guest_stream():
    """
    Streaming chat endpoint for guest users
    """
    try:
        # Check if guest session exists
        if 'guest_session_id' not in session or 'guest_messages' not in session:
            return jsonify({'error': 'No guest session found'}), 400
        
        guest_messages = session.get('guest_messages', [])
        
        if not guest_messages:
            return jsonify({'error': 'No messages found in guest session'}), 400
        
        # Get the last user message to respond to
        user_messages = [msg for msg in guest_messages if msg['role'] == 'user']
        if not user_messages:
            return jsonify({'error': 'No user message to respond to'}), 400
        
        last_user_message = user_messages[-1]
        
        # Check if this is a dialect request (guests should be prompted to login)
        try:
            dialect_response = dialect_middleware.process_dialect_request(last_user_message['content'], is_authenticated=False)
            if dialect_response:
                # Return non-streaming response for dialect requests from guests
                def generate_login_prompt():
                    login_message = "Dialect translation feature is only available for logged in users. Please create an account or log in to access this feature.\n\nދިވެހި ބަހުރުވަ ތަކަށް ތަރުޖަމާ ކުރުމަށް އެކައުންޓެއް ހައްދަވާ، ނުވަތަ ލޮގިންވެ ލައްވާ. މި ފީޗަރަކީ ލޮގިންވާ ފަރާތްތަކަށް އިންނަ ފީޗަރެއް."
                    yield f"data: {json.dumps({'chunk': login_message})}\n\n"
                    yield f"data: {json.dumps({'done': True})}\n\n"
                
                return Response(
                    generate_login_prompt(),
                    mimetype='text/plain',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'X-Accel-Buffering': 'no'
                    }
                )
        except Exception as e:
            app.logger.error(f"Error in dialect processing for guest: {str(e)}")
        
        # Convert guest messages to format expected by Gemini
        messages_for_ai = [
            {'role': msg['role'], 'content': msg['content']} 
            for msg in guest_messages
        ]
        
        # Return streaming response from Gemini
        return gemini_integration.get_gemini_response_stream_flask(messages_for_ai)
        
    except Exception as e:
        app.logger.error(f"Error in guest_stream: {str(e)}")
        return jsonify({'error': str(e)}), 500

# NEW: SAVE GUEST STREAMING RESPONSE
@app.route('/api/guest/save-response', methods=['POST'])
def save_guest_response():
    """Save streamed AI response to guest session"""
    try:
        if 'guest_session_id' not in session:
            return jsonify({'error': 'No guest session found'}), 400
        
        data = request.get_json()
        role = data.get('role', 'akuru')
        content = data.get('content', '')
        
        if not content.strip():
            return jsonify({'error': 'Content is required'}), 400
        
        # Initialize guest_messages if it doesn't exist
        if 'guest_messages' not in session:
            session['guest_messages'] = []
        
        # Create AI message
        ai_message = {
            'id': len(session['guest_messages']) + 1,
            'role': role,
            'content': content,
            'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        # Add to session
        session['guest_messages'].append(ai_message)
        
        return jsonify({
            'id': ai_message['id'],
            'success': True,
            'message': 'Response saved successfully'
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error saving guest response: {str(e)}")
        return jsonify({'error': str(e)}), 500

# @app.route('/api/signup', methods=['POST'])
# def signup():
#     data = request.get_json()
#     name = data.get('name')
#     email = data.get('email')
#     password = data.get('password')
    
#     if not name or not email or not password:
#         return jsonify({'error': 'Name, email and password are required'}), 400
    
#     # Hash the password
#     hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
#     success, message = db.create_user(name, email, hashed_password.decode('utf-8'))
    
#     if success:
#         return jsonify({'message': message}), 201
#     else:
#         if message == "User already exists":
#             return jsonify({'error': message}), 409
#         return jsonify({'error': message}), 500

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not name or not email or not password:
        return jsonify({'error': 'Name, email and password are required'}), 400
    
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    success, message = db.create_user(name, email, hashed_password.decode('utf-8'))
    
    if success:
        # Get the newly created user to generate JWT token
        user = db.get_user_by_email(email)
        
        if user:
            # Generate JWT token
            token = jwt.encode({
                'user_id': user['id'],
                'email': user['email'],
                'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
            }, SECRET_KEY, algorithm='HS256')
            
            return jsonify({
                'message': 'Account created successfully',
                'token': token,
                'user': {
                    'id': user['id'],
                    'name': user['name'],
                    'email': user['email']
                }
            }), 201
        else:
            # Fallback if user retrieval fails
            return jsonify({'message': message}), 201
    else:
        if message == "User already exists":
            return jsonify({'error': message}), 409
        return jsonify({'error': message}), 500


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = db.get_user_by_email(email)
    
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Check password
    if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email']
            }
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401


# @app.route('/api/signup', methods=['POST'])
# def signup():
#     data = request.get_json()
#     name = data.get('name')
#     email = data.get('email')
#     password = data.get('password')
    
#     if not name or not email or not password:
#         return jsonify({'error': 'Name, email and password are required'}), 400
    
#     # Hash the password
#     hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
#     success, message = db.create_user(name, email, hashed_password.decode('utf-8'))
    
#     if success:
#         # Get the newly created user to generate JWT token
#         user = db.get_user_by_email(email)
        
#         if user:
#             # Generate JWT token (same as login)
#             token = jwt.encode({
#                 'user_id': user['id'],
#                 'email': user['email'],
#                 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
#             }, SECRET_KEY, algorithm='HS256')
            
#             return jsonify({
#                 'message': message,
#                 'token': token,
#                 'refreshToken': 'refresh_token_str',  # You may want to implement proper refresh tokens
#                 'user': {
#                     'id': user['id'],
#                     'name': user['name'],
#                     'email': user['email']
#                 }
#             }), 201
#         else:
#             # Fallback if user retrieval fails
#             return jsonify({'message': message}), 201
#     else:
#         if message == "User already exists":
#             return jsonify({'error': message}), 409
#         return jsonify({'error': message}), 500

# @app.route('/api/login', methods=['POST'])
# def login():
#     data = request.get_json()
#     email = data.get('email')
#     password = data.get('password')
    
#     if not email or not password:
#         return jsonify({'error': 'Email and password are required'}), 400
    
#     user = db.get_user_by_email(email)
    
#     if not user:
#         return jsonify({'error': 'Invalid credentials'}), 401
    
#     # Check password
#     if bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
#         # Generate JWT token
#         token = jwt.encode({
#             'user_id': user['id'],
#             'email': user['email'],
#             'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
#         }, SECRET_KEY, algorithm='HS256')
        
#         return jsonify({
#             'message': 'Login successful',
#             'token': token,
#             'refreshToken': 'refresh_token_str'
#         }), 200
#     else:
#         return jsonify({'error': 'Invalid credentials'}), 401

# @app.route('/api/refresh', methods=['POST'])
# def refresh_token():
#     data = request.get_json()
#     refresh_token = data.get('refreshToken')
    
#     if not refresh_token:
#         return jsonify({'error': 'Refresh token required'}), 401
    
#     try:
#         decoded = jwt.decode(refresh_token, SECRET_KEY, algorithms=['HS256'])
        
#         # Validate it's actually a refresh token
#         if decoded.get('type') != 'refresh':
#             return jsonify({'error': 'Invalid token type'}), 401
            
#         # Generate new access token
#         new_token = jwt.encode({
#             'user_id': decoded['user_id'],
#             'email': decoded['email'],
#             'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
#         }, SECRET_KEY, algorithm='HS256')
        
#         return jsonify({'token': new_token}), 200
#     except:
#         return jsonify({'error': 'Invalid refresh token'}), 401

@app.route('/api/user', methods=['GET'])
@token_required
def get_profile():
    token = request.headers.get('Authorization')
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = data['user_id']
        
        user = db.get_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user), 200
    
    except Exception as e:
        print(f"Token decode error: {str(e)}")
        return jsonify({'error': 'Token validation failed'}), 401

# Conversations endpoints
@app.route('/api/conversations', methods=['GET'])
@token_required
def get_user_conversations():
    token = request.headers.get('Authorization')
    token = token[7:] if token.startswith('Bearer ') else token
    
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = data['user_id']
        
        conversations = db.get_conversations(user_id)
        return jsonify(conversations), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['POST'])
@token_required
def create_new_conversation():
    token = request.headers.get('Authorization')
    token = token[7:] if token.startswith('Bearer ') else token
    
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = data['user_id']
        
        title = request.json.get('title', 'New Conversation')
        conversation_id = db.create_conversation(user_id, title)
        
        return jsonify({
            'id': conversation_id,
            'title': title
        }), 201
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Messages endpoints
@app.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
@token_required
def get_conversation_messages(conversation_id):
    messages = db.get_messages(conversation_id)
    return jsonify(messages), 200

# UPDATED MESSAGE ENDPOINT WITH STREAMING SUPPORT
# @app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
# @token_required
# def add_conversation_message(conversation_id):
#     content = request.json.get('content')
#     role = request.json.get('role', 'user')
#     use_streaming = request.json.get('use_streaming', True)  # Default to streaming
    
#     if not content:
#         return jsonify({'error': 'Message content is required'}), 400
    
#     # Add the user message to the database
#     try:
#         message_id = db.add_message(conversation_id, role, content)
#     except Exception as e:
#         print(f"ERROR adding user message: {str(e)}")
#         return jsonify({'error': 'Failed to save message'}), 500
    
#     # Check if this is the first user message and update title if needed
#     if role == 'user':
#         try:
#             # Get all messages to count user messages
#             messages = db.get_messages(conversation_id)
#             user_messages = [msg for msg in messages if msg['role'] == 'user']
            
#             # Check if this is the first user message and update title
#             updated_title = None
#             if len(user_messages) == 1:
#                 new_title = generate_conversation_title(content)
#                 success = db.update_conversation_title(conversation_id, new_title)
#                 if success:
#                     updated_title = new_title
            
#             # Check for dialect request
#             try:
#                 dialect_response = dialect_middleware.process_dialect_request(content, is_authenticated=True)
#             except Exception as e:
#                 print(f"ERROR in dialect processing: {str(e)}")
#                 dialect_response = None
            
#             response_data = {
#                 'id': message_id,
#                 'use_streaming': use_streaming
#             }
            
#             # Include updated title if it was changed
#             if updated_title:
#                 response_data['updated_title'] = updated_title
#                 response_data['conversation_id'] = conversation_id
            
#             if dialect_response:
#                 # Save the dialect response as AI message
#                 try:
#                     ai_message_id = db.add_message(conversation_id, 'akuru', dialect_response)
#                     response_data['ai_response'] = {
#                         'id': ai_message_id,
#                         'content': dialect_response
#                     }
#                     response_data['source'] = 'dialect_database'
#                     response_data['use_streaming'] = False  # Dialect responses don't stream
#                 except Exception as e:
#                     print(f"ERROR saving dialect response: {str(e)}")
#                     raise e
                    
#             elif not use_streaming:
#                 # Use Gemini for non-streaming response
#                 try:
#                     # Get all messages in this conversation for context
#                     messages = gemini_integration.process_conversation_messages(conversation_id, db)
                    
#                     # Get response from Gemini
#                     ai_response = gemini_integration.get_gemini_response(messages)
                    
#                     if not ai_response:
#                         raise Exception("Gemini returned empty response")
                    
#                     # Save the AI response to the database
#                     ai_message_id = db.add_message(conversation_id, 'akuru', ai_response)
                    
#                     response_data['ai_response'] = {
#                         'id': ai_message_id,
#                         'content': ai_response
#                     }
#                     response_data['source'] = 'gemini_ai'
#                 except Exception as e:
#                     print(f"ERROR in Gemini processing: {str(e)}")
#                     raise e
#             else:
#                 # For streaming, we just return success and let the client call /api/chat/stream
#                 response_data['source'] = 'gemini_ai_streaming'
#                 response_data['message'] = 'User message saved, use /api/chat/stream for AI response'
            
#             return jsonify(response_data), 201
            
#         except Exception as e:
#             print(f"Error generating response: {str(e)}")
#             import traceback
#             print(f"Full traceback: {traceback.format_exc()}")
            
#             # Still return success for the user message, but with error info
#             return jsonify({
#                 'id': message_id,
#                 'error': f"Failed to generate response: {str(e)}"
#             }), 201

#     # For non-user messages, just return the message ID
#     return jsonify({'id': message_id}), 201
@app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
@token_required
def add_conversation_message(conversation_id):
    content = request.json.get('content')
    role = request.json.get('role', 'user')
    use_streaming = request.json.get('use_streaming', True)  # Default to streaming
   
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
   
    # Add the user message to the database
    try:
        message_id = db.add_message(conversation_id, role, content)
    except Exception as e:
        print(f"ERROR adding user message: {str(e)}")
        return jsonify({'error': 'Failed to save message'}), 500
   
    # Check if this is the first user message and update title if needed
    if role == 'user':
        try:
            # Get all messages to count user messages
            messages = db.get_messages(conversation_id)
            user_messages = [msg for msg in messages if msg['role'] == 'user']
           
            # Check if this is the first user message and update title
            updated_title = None
            if len(user_messages) == 1:
                new_title = generate_conversation_title(content)
                success = db.update_conversation_title(conversation_id, new_title)
                if success:
                    updated_title = new_title
           
            # Check for dictionary request FIRST
            try:
                dictionary_response = dict_middleware.process_dictionary_request(content, is_authenticated=True)
            except Exception as e:
                print(f"ERROR in dictionary processing: {str(e)}")
                dictionary_response = None
           
            # Check for dialect request if no dictionary match
            dialect_response = None
            if not dictionary_response:
                try:
                    dialect_response = dialect_middleware.process_dialect_request(content, is_authenticated=True)
                except Exception as e:
                    print(f"ERROR in dialect processing: {str(e)}")
                    dialect_response = None
           
            response_data = {
                'id': message_id,
                'use_streaming': use_streaming
            }
           
            # Include updated title if it was changed
            if updated_title:
                response_data['updated_title'] = updated_title
                response_data['conversation_id'] = conversation_id
           
            # Handle dictionary response
            if dictionary_response:
                try:
                    ai_message_id = db.add_message(conversation_id, 'akuru', dictionary_response)
                    response_data['ai_response'] = {
                        'id': ai_message_id,
                        'content': dictionary_response
                    }
                    response_data['source'] = 'dictionary_database'
                    response_data['use_streaming'] = False  # Dictionary responses don't stream
                except Exception as e:
                    print(f"ERROR saving dictionary response: {str(e)}")
                    raise e
            
            # Handle dialect response
            elif dialect_response:
                try:
                    ai_message_id = db.add_message(conversation_id, 'akuru', dialect_response)
                    response_data['ai_response'] = {
                        'id': ai_message_id,
                        'content': dialect_response
                    }
                    response_data['source'] = 'dialect_database'
                    response_data['use_streaming'] = False  # Dialect responses don't stream
                except Exception as e:
                    print(f"ERROR saving dialect response: {str(e)}")
                    raise e
                   
            elif not use_streaming:
                # Use Gemini for non-streaming response
                try:
                    # Get all messages in this conversation for context
                    messages = gemini_integration.process_conversation_messages(conversation_id, db)
                   
                    # Get response from Gemini
                    ai_response = gemini_integration.get_gemini_response(messages)
                   
                    if not ai_response:
                        raise Exception("Gemini returned empty response")
                   
                    # Save the AI response to the database
                    ai_message_id = db.add_message(conversation_id, 'akuru', ai_response)
                   
                    response_data['ai_response'] = {
                        'id': ai_message_id,
                        'content': ai_response
                    }
                    response_data['source'] = 'gemini_ai'
                except Exception as e:
                    print(f"ERROR in Gemini processing: {str(e)}")
                    raise e
            else:
                # For streaming, we just return success and let the client call /api/chat/stream
                response_data['source'] = 'gemini_ai_streaming'
                response_data['message'] = 'User message saved, use /api/chat/stream for AI response'
           
            return jsonify(response_data), 201
           
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
           
            # Still return success for the user message, but with error info
            return jsonify({
                'id': message_id,
                'error': f"Failed to generate response: {str(e)}"
            }), 201
    
    # For non-user messages, just return the message ID
    return jsonify({'id': message_id}), 201

# Optional: Add endpoint to manually update conversation titles
@app.route('/api/conversations/<int:conversation_id>/title', methods=['PUT'])
@token_required
def update_conversation_title_endpoint(conversation_id):
    data = request.get_json()
    new_title = data.get('title')
    
    if not new_title:
        return jsonify({'error': 'Title is required'}), 400
    
    # Limit title length
    if len(new_title) > 100:
        new_title = new_title[:97] + "..."
    
    success = db.update_conversation_title(conversation_id, new_title)
    
    if success:
        return jsonify({'message': 'Title updated successfully', 'title': new_title}), 200
    else:
        return jsonify({'error': 'Failed to update title'}), 500

@app.route('/api/guest/new-session', methods=['POST'])
def create_guest_session():
    """Create a new guest session"""
    session_id = str(uuid.uuid4())
    session['guest_session_id'] = session_id
    session['guest_messages'] = []
    return jsonify({'session_id': session_id}), 201

@app.route('/api/guest/messages', methods=['GET'])
def get_guest_messages():
    """Get messages for current guest session"""
    messages = session.get('guest_messages', [])
    return jsonify(messages), 200

# UPDATED: Guest messages endpoint with streaming support
# @app.route('/api/guest/messages', methods=['POST'])
# def add_guest_message():
#     """Add message to guest session with streaming support"""
#     content = request.json.get('content')
#     role = request.json.get('role', 'user')
#     use_streaming = request.json.get('use_streaming', True)  # Default to streaming
   
#     if not content:
#         return jsonify({'error': 'Message content is required'}), 400
   
#     # Initialize session if it doesn't exist
#     if 'guest_messages' not in session:
#         session['guest_messages'] = []
   
#     # Add user message
#     user_message = {
#         'id': len(session['guest_messages']) + 1,
#         'role': role,
#         'content': content,
#         'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
#     }
#     session['guest_messages'].append(user_message)
   
#     # Generate AI response for user messages
#     if role == 'user':
#         try:
#             # Check if this is a dialect-related query
#             dialect_response = dialect_middleware.process_dialect_request(content, is_authenticated=False)
           
#             response_data = {
#                 'user_message': user_message,
#                 'use_streaming': use_streaming
#             }
           
#             if dialect_response:
#                 # For guest users, return login requirement message instead of dialect response
#                 ai_response = "Dialect translation feature is only available for logged in users. Please create an account or log in to access this feature.\n\nދިވެހި ބަހުރުވަ ތަކަށް ތަރުޖަމާ ކުރުމަށް އެކައުންޓެއް ހައްދަވާ، ނުވަތަ ލޮގިންވެ ލައްވާ. މި ފީޗަރަކީ ލޮގިންވާ ފަރާތްތަކަށް އިންނަ ފީޗަރެއް."
                
#                 ai_message = {
#                     'id': len(session['guest_messages']) + 1,
#                     'role': 'akuru',
#                     'content': ai_response,
#                     'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
#                 }
#                 session['guest_messages'].append(ai_message)
                
#                 response_data['ai_response'] = ai_message
#                 response_data['source'] = 'login_required'
#                 response_data['use_streaming'] = False  # Login prompts don't stream
                
#             elif not use_streaming:
#                 # Non-streaming response
#                 # Convert session messages to format expected by Gemini
#                 messages_for_ai = [{'role': msg['role'], 'content': msg['content']}
#                                  for msg in session['guest_messages']]
               
#                 ai_response = gemini_integration.get_gemini_response(messages_for_ai)
                
#                 ai_message = {
#                     'id': len(session['guest_messages']) + 1,
#                     'role': 'akuru',
#                     'content': ai_response,
#                     'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
#                 }
#                 session['guest_messages'].append(ai_message)
                
#                 response_data['ai_response'] = ai_message
#                 response_data['source'] = 'gemini_ai'
#             else:
#                 # For streaming, return success and let client call /api/guest/stream
#                 response_data['source'] = 'gemini_ai_streaming'
#                 response_data['message'] = 'User message saved, use /api/guest/stream for AI response'
           
#             return jsonify(response_data), 201
           
#         except Exception as e:
#             return jsonify({
#                 'user_message': user_message,
#                 'error': f"Failed to generate AI response: {str(e)}"
#             }), 201
   
#     return jsonify({'message': user_message}), 201

@app.route('/api/guest/messages', methods=['POST'])
def add_guest_message():
    """Add message to guest session with streaming support"""
    content = request.json.get('content')
    role = request.json.get('role', 'user')
    use_streaming = request.json.get('use_streaming', True)  # Default to streaming
   
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
   
    # Initialize session if it doesn't exist
    if 'guest_messages' not in session:
        session['guest_messages'] = []
   
    # Add user message
    user_message = {
        'id': len(session['guest_messages']) + 1,
        'role': role,
        'content': content,
        'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    session['guest_messages'].append(user_message)
   
    # Generate AI response for user messages
    if role == 'user':
        try:
            # Check if this is a dictionary-related query FIRST (available to guests)
            dictionary_response = dict_middleware.process_dictionary_request(content, is_authenticated=True)  # Changed to True
            
            # Check if this is a dialect-related query if no dictionary match (login required)
            dialect_response = None
            if not dictionary_response:
                dialect_response = dialect_middleware.process_dialect_request(content, is_authenticated=False)
           
            response_data = {
                'user_message': user_message,
                'use_streaming': use_streaming
            }
           
            # Handle dictionary response for guests (now available!)
            if dictionary_response:
                ai_message = {
                    'id': len(session['guest_messages']) + 1,
                    'role': 'akuru',
                    'content': dictionary_response,
                    'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                session['guest_messages'].append(ai_message)
               
                response_data['ai_response'] = ai_message
                response_data['source'] = 'dictionary_database'
                response_data['use_streaming'] = False  # Dictionary responses don't stream
            
            # Handle dialect response for guests (still requires login)
            elif dialect_response:
                # For guest users, return login requirement message for dialect requests
                ai_response = "Dialect translation feature is only available for logged in users. Please create an account or log in to access this feature.\n\nދިވެހި ބަހުރުވަ ތަކަށް ތަރުޖަމާ ކުރުމަށް އެކައުންޓެއް ހައްދަވާ، ނުވަތަ ލޮގިންވެ ލައްވާ. މި ފީޗަރަކީ ލޮގިންވާ ފަރާތްތަކަށް އިންނަ ފީޗަރެއް."
               
                ai_message = {
                    'id': len(session['guest_messages']) + 1,
                    'role': 'akuru',
                    'content': ai_response,
                    'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                session['guest_messages'].append(ai_message)
               
                response_data['ai_response'] = ai_message
                response_data['source'] = 'dialect_login_required'
                response_data['use_streaming'] = False  # Login prompts don't stream
               
            elif not use_streaming:
                # Non-streaming response
                # Convert session messages to format expected by Gemini
                messages_for_ai = [{'role': msg['role'], 'content': msg['content']}
                                 for msg in session['guest_messages']]
               
                ai_response = gemini_integration.get_gemini_response(messages_for_ai)
               
                ai_message = {
                    'id': len(session['guest_messages']) + 1,
                    'role': 'akuru',
                    'content': ai_response,
                    'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
                session['guest_messages'].append(ai_message)
               
                response_data['ai_response'] = ai_message
                response_data['source'] = 'gemini_ai'
            else:
                # For streaming, return success and let client call /api/guest/stream
                response_data['source'] = 'gemini_ai_streaming'
                response_data['message'] = 'User message saved, use /api/guest/stream for AI response'
           
            return jsonify(response_data), 201
           
        except Exception as e:
            return jsonify({
                'user_message': user_message,
                'error': f"Failed to generate AI response: {str(e)}"
            }), 201
   
    return jsonify({'message': user_message}), 201

@app.route('/api/guest/new-chat', methods=['POST'])
def clear_guest_session():
    """Clear guest session messages (new chat)"""
    session['guest_messages'] = []
    return jsonify({'message': 'Session cleared'}), 200

# Test endpoint to verify CORS is working
@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({'message': 'CORS is working correctly!'}), 200

if __name__ == '__main__':
    app.run(debug=True)