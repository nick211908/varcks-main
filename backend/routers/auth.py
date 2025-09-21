from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from backend.models.request import UserCreate, UserLogin
from backend.services.supabase import SupabaseService
from backend.core.security import get_current_user, security
from pydantic import BaseModel, EmailStr
from typing import Optional

router = APIRouter(tags=["Authentication"])

# --- Request Models ---

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    subscription_tier: Optional[str] = "free"

class SigninRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class EmailRequest(BaseModel):
    email: EmailStr

# --- Response Models ---

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict

class MessageResponse(BaseModel):
    message: str

class UserResponse(BaseModel):
    user: dict
    message: str

# --- Authentication Endpoints ---

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    signup_data: SignupRequest, 
    supabase_service: SupabaseService = Depends()
):
    """
    Register a new user using Supabase Auth.
    This will automatically handle email confirmation if enabled in Supabase.
    """
    user_metadata = {"subscription_tier": signup_data.subscription_tier}
    
    result = await supabase_service.signup_user(
        email=signup_data.email,
        password=signup_data.password,
        user_metadata=user_metadata
    )
    
    return result

@router.post("/signin", response_model=AuthResponse)
async def signin(
    signin_data: SigninRequest,
    supabase_service: SupabaseService = Depends()
):
    """
    Sign in a user using Supabase Auth.
    Returns access token and user information.
    """
    result = await supabase_service.signin_user(
        email=signin_data.email,
        password=signin_data.password
    )
    
    return result

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    supabase_service: SupabaseService = Depends()
):
    """
    Refresh an access token using a refresh token.
    """
    result = await supabase_service.refresh_token(refresh_data.refresh_token)
    return result

@router.post("/signout", response_model=MessageResponse)
async def signout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase_service: SupabaseService = Depends()
):
    """
    Sign out the current user.
    """
    token = credentials.credentials
    result = await supabase_service.signout_user(token)
    return result

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user information.
    Requires valid authentication token.
    """
    return {"user": current_user}

@router.post("/resend-confirmation", response_model=MessageResponse)
async def resend_confirmation(
    email_data: EmailRequest,
    supabase_service: SupabaseService = Depends()
):
    """
    Resend email confirmation.
    """
    result = await supabase_service.resend_confirmation(email_data.email)
    return result

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    email_data: EmailRequest,
    supabase_service: SupabaseService = Depends()
):
    """
    Send password reset email.
    """
    result = await supabase_service.reset_password(email_data.email)
    return result

# --- Legacy Endpoints (for backward compatibility) ---

@router.post("/login", response_model=AuthResponse)
async def login_legacy(
    signin_data: SigninRequest,
    supabase_service: SupabaseService = Depends()
):
    """
    Legacy login endpoint - redirects to signin.
    Kept for backward compatibility.
    """
    return await signin(signin_data, supabase_service)

# --- Protected Endpoint Example ---

@router.get("/protected")
async def protected_route(current_user: dict = Depends(get_current_user)):
    """
    Example of a protected route that requires authentication.
    """
    return {
        "message": f"Hello {current_user['email']}! This is a protected route.",
        "user_id": current_user["id"],
        "subscription_tier": current_user.get("subscription_tier", "free")
    }