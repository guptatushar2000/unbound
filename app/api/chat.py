# app/api/chat.py
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.db import StateManager
from app.core.api_manager import APIManager
from app.engine.langgraph_engine import LangGraphEngine

# Create instances of core services
state_manager = StateManager()
api_manager = APIManager()
engine = LangGraphEngine(state_manager, api_manager)

router = APIRouter()

class ChatRequest(BaseModel):
    """Chat request schema"""
    user_id: str
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    """Chat response schema"""
    conversation_id: str
    response: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message"""
    try:
        response = await engine.process_message(
            request.user_id,
            request.message,
            request.conversation_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

class ConversationListItem(BaseModel):
    """Conversation list item schema"""
    id: str
    user_id: str
    created_at: int
    last_updated: int

@router.get("/conversations/{user_id}")
async def list_conversations(user_id: str, limit: int = 10):
    """List conversations for a user"""
    conversations = state_manager.list_conversations(user_id, limit)
    return {"conversations": conversations}

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    success = state_manager.delete_conversation(conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted successfully"}