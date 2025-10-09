#!/usr/bin/env python3
"""
Helper functions for managing LLM conversations in the NewsJuice database
"""

import os
import psycopg
from pgvector.psycopg import register_vector
from datetime import datetime
from typing import List, Dict, Optional, Any
import json

class ConversationManager:
    """Manager class for LLM conversation operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the conversation manager
        
        Args:
            database_url: PostgreSQL connection string. If None, uses DATABASE_URL env var.
        """
        self.db_url = database_url or os.environ.get("DATABASE_URL")
        if not self.db_url:
            raise ValueError("Database URL not provided. Set DATABASE_URL environment variable or pass database_url parameter.")
    
    def _get_connection(self):
        """Get database connection with vector support"""
        conn = psycopg.connect(self.db_url, autocommit=True)
        register_vector(conn)
        return conn
    
    def save_conversation(self, user_id: str, model_name: str, messages: List[Dict[str, Any]]) -> int:
        """Save a conversation to the database
        
        Args:
            user_id: Unique identifier for the user
            model_name: Name of the LLM model used (e.g., 'gpt-4', 'claude-3')
            messages: List of message dictionaries with 'role', 'content', and optional 'token_count'
            
        Returns:
            conversation_id: The ID of the saved conversation
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Validate messages format
                for msg in messages:
                    if 'role' not in msg or 'content' not in msg:
                        raise ValueError("Each message must have 'role' and 'content' fields")
                    if msg['role'] not in ['user', 'assistant', 'system']:
                        raise ValueError("Message role must be 'user', 'assistant', or 'system'")
                
                # Insert conversation
                cur.execute("""
                    INSERT INTO llm_conversations (user_id, model_name, conversation_data)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """, (user_id, model_name, json.dumps(messages)))
                
                conversation_id = cur.fetchone()[0]
                
                # Optionally insert individual messages
                for msg in messages:
                    cur.execute("""
                        INSERT INTO llm_messages (conversation_id, role, content, token_count)
                        VALUES (%s, %s, %s, %s);
                    """, (conversation_id, msg['role'], msg['content'], msg.get('token_count')))
                
                return conversation_id
    
    def get_conversation_by_id(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific conversation by ID
        
        Args:
            conversation_id: The ID of the conversation to retrieve
            
        Returns:
            Dictionary containing conversation data, or None if not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, model_name, conversation_data, created_at, updated_at
                    FROM llm_conversations
                    WHERE id = %s;
                """, (conversation_id,))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                return {
                    'id': row[0],
                    'user_id': row[1],
                    'model_name': row[2],
                    'conversation_data': json.loads(row[3]),
                    'created_at': row[4],
                    'updated_at': row[5]
                }
    
    def get_user_conversations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all conversations for a specific user
        
        Args:
            user_id: The user ID to get conversations for
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dictionaries
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, model_name, conversation_data, created_at, updated_at
                    FROM llm_conversations
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (user_id, limit))
                
                conversations = []
                for row in cur.fetchall():
                    conversations.append({
                        'id': row[0],
                        'user_id': row[1],
                        'model_name': row[2],
                        'conversation_data': json.loads(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    })
                
                return conversations
    
    def get_conversations_by_model(self, model_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversations by model name
        
        Args:
            model_name: The model name to filter by
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dictionaries
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, model_name, conversation_data, created_at, updated_at
                    FROM llm_conversations
                    WHERE model_name = %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (model_name, limit))
                
                conversations = []
                for row in cur.fetchall():
                    conversations.append({
                        'id': row[0],
                        'user_id': row[1],
                        'model_name': row[2],
                        'conversation_data': json.loads(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    })
                
                return conversations
    
    def update_conversation(self, conversation_id: int, new_messages: List[Dict[str, Any]]) -> bool:
        """Update an existing conversation with new messages
        
        Args:
            conversation_id: The ID of the conversation to update
            new_messages: New list of messages to replace the existing ones
            
        Returns:
            True if successful, False if conversation not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Check if conversation exists
                cur.execute("SELECT id FROM llm_conversations WHERE id = %s;", (conversation_id,))
                if not cur.fetchone():
                    return False
                
                # Validate messages format
                for msg in new_messages:
                    if 'role' not in msg or 'content' not in msg:
                        raise ValueError("Each message must have 'role' and 'content' fields")
                    if msg['role'] not in ['user', 'assistant', 'system']:
                        raise ValueError("Message role must be 'user', 'assistant', or 'system'")
                
                # Update conversation data
                cur.execute("""
                    UPDATE llm_conversations 
                    SET conversation_data = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s;
                """, (json.dumps(new_messages), conversation_id))
                
                # Delete old individual messages and insert new ones
                cur.execute("DELETE FROM llm_messages WHERE conversation_id = %s;", (conversation_id,))
                
                for msg in new_messages:
                    cur.execute("""
                        INSERT INTO llm_messages (conversation_id, role, content, token_count)
                        VALUES (%s, %s, %s, %s);
                    """, (conversation_id, msg['role'], msg['content'], msg.get('token_count')))
                
                return True
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """Delete a conversation and all its messages
        
        Args:
            conversation_id: The ID of the conversation to delete
            
        Returns:
            True if successful, False if conversation not found
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM llm_conversations WHERE id = %s;", (conversation_id,))
                return cur.rowcount > 0
    
    def search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search conversations by content using JSONB operators
        
        Args:
            query: Search query string
            limit: Maximum number of conversations to return
            
        Returns:
            List of matching conversation dictionaries
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, user_id, model_name, conversation_data, created_at, updated_at
                    FROM llm_conversations
                    WHERE conversation_data::text ILIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s;
                """, (f"%{query}%", limit))
                
                conversations = []
                for row in cur.fetchall():
                    conversations.append({
                        'id': row[0],
                        'user_id': row[1],
                        'model_name': row[2],
                        'conversation_data': json.loads(row[3]),
                        'created_at': row[4],
                        'updated_at': row[5]
                    })
                
                return conversations
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about conversations in the database
        
        Returns:
            Dictionary with conversation statistics
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Total conversations
                cur.execute("SELECT COUNT(*) FROM llm_conversations;")
                total_conversations = cur.fetchone()[0]
                
                # Conversations by model
                cur.execute("""
                    SELECT model_name, COUNT(*) as count
                    FROM llm_conversations
                    GROUP BY model_name
                    ORDER BY count DESC;
                """)
                by_model = {row[0]: row[1] for row in cur.fetchall()}
                
                # Average messages per conversation
                cur.execute("""
                    SELECT AVG(jsonb_array_length(conversation_data)) as avg_messages
                    FROM llm_conversations;
                """)
                avg_messages = cur.fetchone()[0] or 0
                
                # Recent activity (last 24 hours)
                cur.execute("""
                    SELECT COUNT(*) FROM llm_conversations
                    WHERE created_at >= NOW() - INTERVAL '24 hours';
                """)
                recent_conversations = cur.fetchone()[0]
                
                return {
                    'total_conversations': total_conversations,
                    'by_model': by_model,
                    'avg_messages_per_conversation': round(avg_messages, 2),
                    'recent_conversations_24h': recent_conversations
                }