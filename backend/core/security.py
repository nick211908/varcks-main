import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.core.config import settings
from backend.services.supabase import SupabaseService
from typing import Dict

# --- Configuration ---

# Use HTTPBearer instead of OAuth2PasswordBearer for Supabase tokens
security = HTTPBearer()

logger = logging.getLogger(__name__)

# --- Core Functions ---

def validate_model_access(requested_model: str, user_sub: str):
    """
    Validates if a user's subscription tier grants access to a requested model.
    Raises HTTPException 403 (Forbidden) if access is denied.
    """
    model_config: Dict = settings.MODEL_CONFIG.get(requested_model)
    
    if not model_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{requested_model}' is not a valid or configured model."
        )
        
    allowed_subs = model_config.get("allowed_subs", [])
    
    if user_sub not in allowed_subs:
        logger.warning(f"Access denied for user with sub '{user_sub}' to model '{requested_model}'.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your '{user_sub}' subscription does not permit use of the '{requested_model}' model."
        )
    logger.info(f"Access granted for user with sub '{user_sub}' to model '{requested_model}'.")

# --- FastAPI Dependencies ---

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_service: SupabaseService = Depends()
) -> Dict:
    """
    Dependency to verify Supabase JWT token and get the current user.
    This replaces the old JWT verification with Supabase Auth verification.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract the token from the Authorization header
        token = credentials.credentials
        
        # Verify the token with Supabase and get user info
        user = await supabase_service.verify_token(token)
        
        if not user:
            raise credentials_exception
            
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions from supabase_service
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}", exc_info=True)
        raise credentials_exception

async def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to get current active user (email confirmed).
    Use this for endpoints that require email confirmation.
    """
    if not current_user.get("email_confirmed", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email address not confirmed. Please check your email and confirm your account."
        )
    return current_user

# --- Optional: Keep legacy functions for backward compatibility ---

def create_access_token(data: dict, expires_delta=None) -> str:
    """
    Legacy function - kept for backward compatibility.
    Note: With Supabase Auth, you should use Supabase's tokens instead.
    """
    logger.warning("create_access_token is deprecated. Use Supabase Auth tokens instead.")
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt