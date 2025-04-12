from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.engine.langgraph_engine import LangGraphEngine

engine = LangGraphEngine()

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

async def func():
    # Placeholder function to simulate chat response
    return ChatResponse(response="This is a simulated response.")

@router.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = await engine.process_message(request.message)
        return response
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
