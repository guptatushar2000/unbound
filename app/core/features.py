# app/core/features.py
import os
from typing import Dict, Any
from app.core.config import settings

class FeatureFlags:
    """Manage feature flags for the application"""
    
    def __init__(self):
        # Define feature flags with default values
        self._flags: Dict[str, bool] = {
            # Core features
            "use_shared_context": True,
            "use_entity_extraction": True,
            
            # Agent features
            "batch_agent_enabled": True,
            "results_agent_enabled": True,
            
            # Advanced features
            "conversation_history": True,
            "cross_agent_workflow": True,
            "suggestions_enabled": True,
            
            # Development features
            "debug_logs": settings.app.DEBUG,
            "trace_llm_calls": settings.app.DEBUG,
            "mock_services": False
        }
        
        # Override with environment variables if present
        self._load_from_env()
    
    def _load_from_env(self):
        """Load feature flags from environment variables"""
        for flag in self._flags.keys():
            env_var = f"FEATURE_{flag.upper()}"
            env_value = os.environ.get(env_var)
            
            if env_value is not None:
                # Convert string to boolean
                self._flags[flag] = env_value.lower() in ("true", "1", "yes", "y")
    
    def is_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled"""
        return self._flags.get(flag_name, False)
    
    def set_flag(self, flag_name: str, value: bool):
        """Set a feature flag (for testing or runtime configuration)"""
        if flag_name in self._flags:
            self._flags[flag_name] = value
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags and their values"""
        return self._flags.copy()

# Create singleton instance
feature_flags = FeatureFlags()