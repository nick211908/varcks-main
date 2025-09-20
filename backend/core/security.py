import logging
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from backend.core.config import settings
from typing import Dict

# --- Configuration ---

# 1. Password Hashing Setup (using bcrypt)
# This creates a context for hashing and verifying passwords.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 2. OAuth2 Scheme Setup
# This tells FastAPI where to look for the token (in the Authorization header).
# The tokenUrl should point to your login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

logger = logging.getLogger(__name__)

# --- Core Functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    """Hashes a plain-text password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Creates a new JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default to the expiration time from settings
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

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

# --- FastAPI Dependency ---

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    Dependency to decode JWT and get the current user.
    This would be used to protect endpoints. In a full app, it would return a User model.
    For now, it returns the token's payload (e.g., {'sub': 'user@example.com', ...}).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        # In a real application, you would fetch the user from the database here
        # using the email and return a user model object.
        # user = await supabase_service.get_user_by_email(email)
        # if user is None:
        #     raise credentials_exception
        return payload # For now, just return the decoded payload
    except JWTError:
        logger.error("JWT Error: Could not validate credentials.", exc_info=True)
        raise credentials_exception

