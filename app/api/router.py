from fastapi import APIRouter
from app.api.chat import router as chat_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])