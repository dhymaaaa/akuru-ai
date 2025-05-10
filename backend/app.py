from flask import Flask, request, jsonify
from flask_cors import CORS
import bcrypt
import jwt
import datetime
import os
from dotenv import load_dotenv
import db  # Import our database module

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

# Initialize database
db.setup_database()

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
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }, SECRET_KEY, algorithm='HS256')
        
        return jsonify({
            'message': 'Login successful',
            'token': token
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
def create_new_conversation():  # Renamed this function to avoid conflicts
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

@app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
@token_required
def add_conversation_message(conversation_id):  # Renamed this function to avoid conflicts
    content = request.json.get('content')
    role = request.json.get('role', 'user')
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
    
    message_id = db.add_message(conversation_id, role, content)
    
    # Here you would typically generate a response from your AI model
    # For now, let's just echo back with an "akuru" role
    if role == 'user':
        db.add_message(conversation_id, 'akuru', f"Echo: {content}")
    
    return jsonify({'id': message_id}), 201

# Test endpoint to verify CORS is working
@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({'message': 'CORS is working correctly!'}), 200

if __name__ == '__main__':
    app.run(debug=True)