# app/utils/context_manager.py
from typing import Dict, Any, Optional, List
import json
import time
from app.core.db import get_db_connection

class SharedContextManager:
    """Manages shared context between agents"""
    
    async def get_shared_context(self, conversation_id: str, requesting_agent_id: str) -> Dict[str, Any]:
        """Get relevant shared context for a specific agent"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get basic conversation info
            cursor.execute(
                'SELECT user_id FROM conversations WHERE id = ?',
                (conversation_id,)
            )
            conversation = cursor.fetchone()
            
            if not conversation:
                return {}
            
            # Get user info
            user_id = conversation["user_id"]
            
            # Get recent messages
            cursor.execute(
                '''
                SELECT role, content FROM messages 
                WHERE conversation_id = ? AND role = 'user'
                ORDER BY created_at DESC LIMIT 2
                ''',
                (conversation_id,)
            )
            user_messages = [row["content"] for row in cursor.fetchall()]
            
            # Get shared context data
            cursor.execute(
                'SELECT key, value FROM state_data WHERE conversation_id = ? AND key LIKE "shared_context.%"',
                (conversation_id,)
            )
            shared_data = {
                key.replace("shared_context.", ""): json.loads(value)
                for key, value in cursor.fetchall()
            }
            
            # Base shared context all agents need
            shared_context = {
                "user_id": user_id,
                "recent_user_messages": user_messages,
                "conversation_summary": self._generate_summary(shared_data)
            }
            
            # Agent-specific context enrichment
            if requesting_agent_id == "batch_agent":
                # Add context relevant to batch agent
                shared_context["active_run_id"] = shared_data.get("active_run_id")
                shared_context["run_history"] = shared_data.get("run_history", [])
            
            elif requesting_agent_id == "results_agent":
                # Add context relevant to results agent
                shared_context["recent_run_types"] = shared_data.get("recent_run_types", [])
                shared_context["active_run_id"] = shared_data.get("active_run_id")
            
            return shared_context
    
    async def update_shared_context(self, conversation_id: str, agent_id: str, context_updates: Dict[str, Any]) -> bool:
        """Update shared context with agent-provided information"""
        current_time = int(time.time())
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if conversation exists
            cursor.execute(
                'SELECT id FROM conversations WHERE id = ?',
                (conversation_id,)
            )
            if not cursor.fetchone():
                return False
            
            # Update shared context
            for key, value in context_updates.items():
                db_key = f"shared_context.{key}"
                value_json = json.dumps(value)
                
                cursor.execute(
                    'INSERT OR REPLACE INTO state_data (conversation_id, key, value, updated_at) VALUES (?, ?, ?, ?)',
                    (conversation_id, db_key, value_json, current_time)
                )
            
            conn.commit()
            return True
    
    def _generate_summary(self, shared_data: Dict[str, Any]) -> str:
        """Generate a short summary of the conversation based on shared data"""
        topics = set()
        
        if "run_type" in shared_data:
            topics.add(f"{shared_data['run_type']} run")
        
        if "results_type" in shared_data:
            topics.add(f"{shared_data['results_type']} results")
        
        if "active_run_id" in shared_data and shared_data["active_run_id"]:
            topics.add("run management")
        
        if not topics:
            return "Conversation just started"
        
        return f"Conversation about {', '.join(topics)}"