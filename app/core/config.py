# app/core/config.py
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseSettings, Field
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LoggingSettings(BaseSettings):
    """Configuration for logging"""
    LOG_LEVEL: str = Field(default="INFO")
    
    class Config:
        env_file = ".env"

class ServiceSettings(BaseSettings):
    """Configuration for external services"""
    BATCH_SERVICE_URL: str = Field(default="http://localhost:8000")
    RESULTS_SERVICE_URL: str = Field(default="http://localhost:8080")
    
    class Config:
        env_file = ".env"

class DatabaseSettings(BaseSettings):
    """Configuration for SQLite database"""
    DB_PATH: str = Field(default="./data/chatbot.db")
    CONVERSATION_TTL: int = Field(default=86400)  # 24 hours in seconds
    
    class Config:
        env_file = ".env"

class ModelSettings(BaseSettings):
    """Configuration for LLM models"""
    MODEL_NAME: str = Field(default="gpt-4o")
    MODEL_TEMPERATURE: float = Field(default=0.1)
    
    class Config:
        env_file = ".env"

class APISettings(BaseSettings):
    """Configuration for API keys"""
    OPENAI_API_KEY: str
    
    class Config:
        env_file = ".env"

class AppSettings(BaseSettings):
    """Application-level settings"""
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")
    
    class Config:
        env_file = ".env"

class Settings(BaseSettings):
    """Main settings class that includes all sub-settings"""
    app: AppSettings = AppSettings()
    logging: LoggingSettings = LoggingSettings()
    services: ServiceSettings = ServiceSettings()
    database: DatabaseSettings = DatabaseSettings()
    model: ModelSettings = ModelSettings()
    api: APISettings = APISettings()
    
    # User group definitions
    USER_GROUPS: Dict[str, List[str]] = {
        "financial_user": ["basic-users", "premium-users"],
        "admin_user": ["basic-users", "premium-users", "admins"]
    }
    
    # Permission definitions
    AGENT_PERMISSIONS: Dict[str, Dict[str, List[str]]] = {
        "batch_agent": {
            "required_groups": ["basic-users", "premium-users", "admins"]
        },
        "results_agent": {
            "required_groups": ["premium-users", "admins"]
        }
    }
    
    def validate_config(self) -> List[str]:
        """Validate critical configuration parameters"""
        missing = []
        
        # Validate API keys
        if not self.api.OPENAI_API_KEY or self.api.OPENAI_API_KEY == "your_openai_api_key_here":
            missing.append("OPENAI_API_KEY")
        
        # Validate service URLs
        if not self.services.BATCH_SERVICE_URL:
            missing.append("BATCH_SERVICE_URL")
        if not self.services.RESULTS_SERVICE_URL:
            missing.append("RESULTS_SERVICE_URL")
        
        # Ensure database directory exists
        db_dir = os.path.dirname(self.database.DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir)
            except OSError:
                missing.append("DB_PATH (directory could not be created)")
        
        return missing

@lru_cache()
def get_settings() -> Settings:
    """Create cached settings instance"""
    settings = Settings()
    return settings

# Export the settings for easy import
settings = get_settings()