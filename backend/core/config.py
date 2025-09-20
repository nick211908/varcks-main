import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import List, Dict, Any

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """
    Application settings and configuration.
    Reads environment variables.
    """
    # Supabase credentials
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # JWT Secret Key for security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Model configurations with subscription-based access control
    # Each model has a list of subscription tiers that are allowed to use it.
    MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
        "model-1": {
            "provider": "openai", 
            "capabilities": ["text", "code"],
            "allowed_subs": ["free", "pro", "enterprise"] # Available to all
        },
        "model-2": {
            "provider": "huggingface", 
            "capabilities": ["text", "summarization"],
            "allowed_subs": ["pro", "enterprise"] # Pro and Enterprise only
        },
        "model-3": {
            "provider": "local", 
            "capabilities": ["text", "translation", "high-speed"],
            "allowed_subs": ["enterprise"] # Enterprise only
        },
    }

    class Config:
        case_sensitive = True

settings = Settings()

