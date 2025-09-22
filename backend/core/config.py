import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List, Dict, Any

load_dotenv()

class Settings(BaseSettings):
    # --- Other settings remain the same ---
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key")
    ALGORITHM: str = "HS268"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- MODEL CONFIGURATION SECTION ---
    # This dictionary is the single source of truth for your models.
    MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
        
        # To change a model's name, simply change this key.
        # For example, change "model-1" to "gpt-4-o".
        "gpt-4-o": {
            # This links to the interface file. It must be "openai", "huggingface", or "local"
            # to match the logic in `langgraph_agent.py`.
            "provider": "openai", 
            
            # These are descriptive keywords for the Research Agent.
            # Update these to reflect the model's strengths.
            "capabilities": ["text", "strong code generation", "advanced reasoning", "general purpose"],
            
            # This list controls access. Only users with these subscription tiers
            # can be assigned this model by the auto router.
            "allowed_subs": ["pro", "enterprise"] 
        },
        
        "mistral-7b": {
            "provider": "huggingface", 
            "capabilities": ["text", "fast summarization", "efficient for specific tasks"],
            "allowed_subs": ["free", "pro", "enterprise"] # Available to all
        },
        
        "llama3-8b-local": {
            "provider": "local", 
            "capabilities": ["text", "fast translation", "on-device", "privacy-focused"],
            "allowed_subs": ["enterprise"] # Enterprise only
        },
    }

    class Config:
        case_sensitive = True

settings = Settings()