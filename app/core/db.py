# app/core/db.py
import sqlite3
import json
import os
import time
from typing import Dict, Any, List, Optional, Union
from contextlib import contextmanager

from app.core.config import settings

# Ensure the database directory exists
os.makedirs(os.path.dirname(settings.database.DB_PATH), exist_ok=True)

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(settings.database.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def initialize_database():
    """Create database tables if they don't exist"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create conversations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            last_updated INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )
        ''')
        
        # Create messages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            agent_id TEXT,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        ''')
        
        # Create state table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS state_data (
            conversation_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at INTEGER NOT NULL,
            PRIMARY KEY (conversation_id, key),
            FOREIGN KEY (conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
        )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_state_conversation_id ON state_data (conversation_id)')
        
        conn.commit()

class StateManager:
    """SQLite-based state manager for conversation state"""
    
    def __init__(self):
        """Initialize the state manager"""
        initialize_database()
    
    def create_conversation(self, user_id: str) -> str:
        """Create a new conversation and return the ID"""
        import uuid
        conversation_id = str(uuid.uuid4())
        
        current_time = int(time.time())
        ttl = settings.database.CONVERSATION_TTL
        expires_at = current_time + ttl
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO conversations (id, user_id, created_at, last_updated, expires_at) VALUES (?, ?, ?, ?, ?)',
                (conversation_id, user_id, current_time, current_time, expires_at)
            )
            conn.commit()
        
        return conversation_id
    
    def get_conversation_state(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get the complete state for a conversation"""
        with get_db_connection() as conn:
            # Check if conversation exists and not expired
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM conversations WHERE id = ? AND expires_at > ?',
                (conversation_id, int(time.time()))
            )
            conversation = cursor.fetchone()
            
            if not conversation:
                return None
            
            # Get all messages
            cursor.execute(
                'SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at',
                (conversation_id,)
            )
            messages = cursor.fetchall()
            
            # Get all state data
            cursor.execute(
                'SELECT key, value FROM state_data WHERE conversation_id = ?',
                (conversation_id,)
            )
            state_data = cursor.fetchall()
            
            # Construct state dictionary
            state = {
                "conversation_id": conversation_id,
                "user_id": conversation["user_id"],
                "created_at": conversation["created_at"],
                "messages": [
                    {
                        "role": message["role"],
                        "content": message["content"],
                        "agent_id": message["agent_id"]
                    }
                    for message in messages
                ]
            }
            
            # Add state data
            for key, value in state_data:
                state[key] = json.loads(value)
            
            return state
    
    def save_conversation_state(self, conversation_id: str, state: Dict[str, Any]) -> bool:
        """Save the conversation state"""
        current_time = int(time.time())
        ttl = settings.database.CONVERSATION_TTL
        expires_at = current_time + ttl
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Update conversation last updated time
            cursor.execute(
                'UPDATE conversations SET last_updated = ?, expires_at = ? WHERE id = ?',
                (current_time, expires_at, conversation_id)
            )
            
            # Handle messages
            if "messages" in state:
                # Get existing messages
                cursor.execute(
                    'SELECT id FROM messages WHERE conversation_id = ?',
                    (conversation_id,)
                )
                existing_count = len(cursor.fetchall())
                
                # Add new messages
                for i, message in enumerate(state["messages"][existing_count:], start=existing_count):
                    cursor.execute(
                        'INSERT INTO messages (conversation_id, role, content, agent_id, created_at) VALUES (?, ?, ?, ?, ?)',
                        (
                            conversation_id,
                            message["role"],
                            message["content"],
                            message.get("agent_id"),
                            current_time + i  # Ensure order
                        )
                    )
            
            # Handle state data - remove messages to avoid duplication
            state_copy = state.copy()
            if "messages" in state_copy:
                del state_copy["messages"]
            if "conversation_id" in state_copy:
                del state_copy["conversation_id"]
            
            # Save each state key separately
            for key, value in state_copy.items():
                # Skip user_id as it's already in conversations table
                if key == "user_id":
                    continue
                    
                value_json = json.dumps(value)
                cursor.execute(
                    'INSERT OR REPLACE INTO state_data (conversation_id, key, value, updated_at) VALUES (?, ?, ?, ?)',
                    (conversation_id, key, value_json, current_time)
                )
            
            conn.commit()
            return True
    
    def list_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List conversations for a user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM conversations WHERE user_id = ? AND expires_at > ? ORDER BY last_updated DESC LIMIT ?',
                (user_id, int(time.time()), limit)
            )
            conversations = cursor.fetchall()
            
            return [dict(conv) for conv in conversations]
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all associated data"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def cleanup_expired_conversations(self) -> int:
        """Clean up expired conversations"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE expires_at <= ?', (int(time.time()),))
            conn.commit()
            return cursor.rowcount