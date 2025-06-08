import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables if not already loaded
load_dotenv()

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME')
}

def setup_database():
    """Initialize the database using schema.sql"""
    conn = mysql.connector.connect(
        host=db_config['host'],
        user=db_config['user'],
        password=db_config['password']
    )
    cursor = conn.cursor()
    
    try:
        # Read schema.sql file
        with open('backend/db/schema.sql', 'r') as schema_file:
            schema_sql = schema_file.read()
            
        # Split SQL commands and execute them
        for command in schema_sql.split(';'):
            # Skip empty commands
            if command.strip():
                cursor.execute(command)
        
        conn.commit()
        print("Database setup completed successfully")
    except Exception as e:
        print(f"Database setup error: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def get_connection():
    """Get a new database connection"""
    return mysql.connector.connect(**db_config)

# User operations
def get_user_by_email(email):
    """Get user by email"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT name, email FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def create_user(name, email, password_hash):
    """Create a new user"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return False, "User already exists"
        
        # Insert new user
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, password_hash)
        )
        conn.commit()
        return True, "User created successfully"
    except Exception as e:
        return False, str(e)
    finally:
        cursor.close()
        conn.close()

# Conversation operations
def create_conversation(user_id, title="New Conversation"):
    """Create a new conversation"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO conversations (user_id, title) VALUES (%s, %s)",
            (user_id, title)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

def get_conversations(user_id):
    """Get all conversations for a user"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT c.*, COUNT(m.id) as message_count 
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            WHERE c.user_id = %s
            GROUP BY c.id
            ORDER BY c.updated_at DESC
        """, (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_conversation(conversation_id):
    """Get a specific conversation"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM conversations WHERE id = %s", (conversation_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def update_conversation_title(conversation_id, title):
    """Update conversation title"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE conversations SET title = %s WHERE id = %s",
            (title, conversation_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()

def delete_conversation(conversation_id):
    """Delete a conversation (messages will be deleted via cascade)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()

# Message operations
def add_message(conversation_id, role, content):
    """Add a message to a conversation"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id, role, content)
        )
        # Update the conversation's updated_at timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (conversation_id,)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()

def get_messages(conversation_id):
    """Get all messages for a conversation"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conversation_id,)
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def get_message(message_id):
    """Get a specific message"""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def delete_message(message_id):
    """Delete a message"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get the conversation ID before deleting
        cursor.execute("SELECT conversation_id FROM messages WHERE id = %s", (message_id,))
        result = cursor.fetchone()
        if not result:
            return False
            
        conversation_id = result[0]
        
        # Delete the message
        cursor.execute("DELETE FROM messages WHERE id = %s", (message_id,))
        
        # Update the conversation's updated_at timestamp
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (conversation_id,)
        )
        
        conn.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()
        conn.close()


def get_dialect_by_english_term(english_term):
    """Get dialect information by exact English term match"""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = "SELECT * FROM dialects WHERE LOWER(eng_term) = LOWER(%s)"
        cursor.execute(query, (english_term,))
        result = cursor.fetchone()
        return result
    except Exception as e:
        print(f"Error fetching dialect by English term: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

def search_dialects(search_term):
    """Search dialects with partial matching"""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Search in all columns for partial matches
        query = """
        SELECT * FROM dialects 
        WHERE LOWER(eng_term) LIKE LOWER(%s) 
           OR LOWER(male_term) LIKE LOWER(%s)
           OR LOWER(huvadhoo_term) LIKE LOWER(%s)
           OR LOWER(addu_term) LIKE LOWER(%s)
        ORDER BY 
            CASE 
                WHEN LOWER(eng_term) = LOWER(%s) THEN 1
                WHEN LOWER(eng_term) LIKE LOWER(%s) THEN 2
                ELSE 3
            END
        LIMIT 10
        """
        
        search_pattern = f"%{search_term}%"
        cursor.execute(query, (
            search_pattern, search_pattern, search_pattern, search_pattern,
            search_term, f"{search_term}%"
        ))
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error searching dialects: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

def get_all_dialects():
    """Get all dialect entries (for admin purposes)"""
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = "SELECT * FROM dialects ORDER BY eng_term"
        cursor.execute(query)
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Error fetching all dialects: {e}")
        return []
    finally:
        cursor.close()
        connection.close()