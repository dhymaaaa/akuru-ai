from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
import bcrypt
import jwt
import uuid
import datetime
import os
from dotenv import load_dotenv
import db  # Import our database module
import gemini_integration  # Import our Gemini integration
from dialect_middleware import DialectMiddleware

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
            'refreshToken': 'refresh_token_str'
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

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

@app.route('/api/refresh', methods=['POST'])
def refresh_token():
    data = request.get_json()
    refresh_token = data.get('refreshToken')
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 401
    
    try:
        decoded = jwt.decode(refresh_token, SECRET_KEY, algorithms=['HS256'])
        
        # Validate it's actually a refresh token
        if decoded.get('type') != 'refresh':
            return jsonify({'error': 'Invalid token type'}), 401
            
        # Generate new access token
        new_token = jwt.encode({
            'user_id': decoded['user_id'],
            'email': decoded['email'],
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        }, SECRET_KEY, algorithm='HS256')
        
        return jsonify({'token': new_token}), 200
    except:
        return jsonify({'error': 'Invalid refresh token'}), 401

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

# @app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
# @token_required
# def add_conversation_message(conversation_id):
#     content = request.json.get('content')
#     role = request.json.get('role', 'user')
    
#     if not content:
#         return jsonify({'error': 'Message content is required'}), 400
    
#     # Add the user message to the database
#     message_id = db.add_message(conversation_id, role, content)
    
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
#                     print(f"Updated conversation {conversation_id} title to: {new_title}")
            
#             # Get all messages in this conversation for context
#             messages = gemini_integration.process_conversation_messages(conversation_id, db)
            
#             # Get response from Gemini
#             ai_response = gemini_integration.get_gemini_response(messages)
            
#             # Save the AI response to the database
#             ai_message_id = db.add_message(conversation_id, 'akuru', ai_response)
            
#             response_data = {
#                 'id': message_id,
#                 'ai_response': {
#                     'id': ai_message_id,
#                     'content': ai_response
#                 }
#             }
            
#             # Include updated title if it was changed
#             if updated_title:
#                 response_data['updated_title'] = updated_title
#                 response_data['conversation_id'] = conversation_id
            
#             return jsonify(response_data), 201
            
#         except Exception as e:
#             app.logger.error(f"Error generating AI response: {str(e)}")
#             # Still return success for the user message, but with error info
#             return jsonify({
#                 'id': message_id,
#                 'error': f"Failed to generate AI response: {str(e)}"
#             }), 201
    
#     # For non-user messages, just return the message ID
#     return jsonify({'id': message_id}), 201

@app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
@token_required
def add_conversation_message(conversation_id):
    content = request.json.get('content')
    role = request.json.get('role', 'user')
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
    
    # Add the user message to the database
    message_id = db.add_message(conversation_id, role, content)
    
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
                    print(f"Updated conversation {conversation_id} title to: {new_title}")
            
            # *** NEW: Check if this is a dialect-related query ***
            dialect_response = dialect_middleware.process_dialect_request(content, is_authenticated=True)
            
            if dialect_response:
                # Save the dialect response as AI message
                ai_message_id = db.add_message(conversation_id, 'akuru', dialect_response)
                
                response_data = {
                    'id': message_id,
                    'ai_response': {
                        'id': ai_message_id,
                        'content': dialect_response
                    },
                    'source': 'dialect_database'  # Indicate this came from database
                }
            else:
                # Get all messages in this conversation for context
                messages = gemini_integration.process_conversation_messages(conversation_id, db)
                
                # Get response from Gemini
                ai_response = gemini_integration.get_gemini_response(messages)
                
                # Save the AI response to the database
                ai_message_id = db.add_message(conversation_id, 'akuru', ai_response)
                
                response_data = {
                    'id': message_id,
                    'ai_response': {
                        'id': ai_message_id,
                        'content': ai_response
                    },
                    'source': 'gemini_ai'  # Indicate this came from Gemini
                }
            
            # Include updated title if it was changed
            if updated_title:
                response_data['updated_title'] = updated_title
                response_data['conversation_id'] = conversation_id
            
            return jsonify(response_data), 201
            
        except Exception as e:
            app.logger.error(f"Error generating response: {str(e)}")
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

# @app.route('/api/guest/messages', methods=['POST'])
# def add_guest_message():
#     """Add message to guest session"""
#     content = request.json.get('content')
#     role = request.json.get('role', 'user')
    
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
#             # Convert session messages to format expected by Gemini
#             messages_for_ai = [{'role': msg['role'], 'content': msg['content']} 
#                              for msg in session['guest_messages']]
            
#             ai_response = gemini_integration.get_gemini_response(messages_for_ai)
            
#             ai_message = {
#                 'id': len(session['guest_messages']) + 1,
#                 'role': 'akuru',
#                 'content': ai_response,
#                 'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
#             }
#             session['guest_messages'].append(ai_message)
            
#             return jsonify({
#                 'user_message': user_message,
#                 'ai_response': ai_message
#             }), 201
            
#         except Exception as e:
#             return jsonify({
#                 'user_message': user_message,
#                 'error': f"Failed to generate AI response: {str(e)}"
#             }), 201
    
#     return jsonify({'message': user_message}), 201

@app.route('/api/guest/messages', methods=['POST'])
def add_guest_message():
    """Add message to guest session"""
    content = request.json.get('content')
    role = request.json.get('role', 'user')
   
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
            # *** NEW: Check if this is a dialect-related query ***
            dialect_response = dialect_middleware.process_dialect_request(content, is_authenticated=False)
           
            if dialect_response:
                # For guest users, return login requirement message instead of dialect response
                ai_response = "Dialect translation feature is only available for logged in users. Please create an account or log in to access this feature."
                source = 'login_required'
            else:
                # Convert session messages to format expected by Gemini
                messages_for_ai = [{'role': msg['role'], 'content': msg['content']}
                                 for msg in session['guest_messages']]
               
                ai_response = gemini_integration.get_gemini_response(messages_for_ai)
                source = 'gemini_ai'
           
            ai_message = {
                'id': len(session['guest_messages']) + 1,
                'role': 'akuru',
                'content': ai_response,
                'created_at': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            session['guest_messages'].append(ai_message)
           
            return jsonify({
                'user_message': user_message,
                'ai_response': ai_message,
                'source': source  # Indicate the response source
            }), 201
           
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