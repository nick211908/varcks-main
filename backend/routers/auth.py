from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from backend.models.request import UserCreate, UserLogin
from backend.services.supabase import SupabaseService
from backend.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, supabase_service: SupabaseService = Depends()):
    """
    Handles user registration. Hashes the password and saves the new user to the database.
    """
    # Check if user already exists
    existing_user = await supabase_service.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    
    # Hash the password
    hashed_password = hash_password(user_data.password)
    
    # Create the user in Supabase
    new_user = await supabase_service.create_user(email=user_data.email, hashed_password=hashed_password)
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user account."
        )

    return {"message": f"User account for {new_user['email']} created successfully."}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), supabase_service: SupabaseService = Depends()):
    """
    Handles user login. Verifies credentials and returns a JWT access token.
    FastAPI's OAuth2PasswordRequestForm expects form data with 'username' and 'password'.
    We will use the 'username' field to carry the email.
    """
    user = await supabase_service.get_user_by_email(form_data.username)
    
    # Check if user exists and password is correct
    if not user or not verify_password(form_data.password, user['hashed_password']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate a JWT token
    access_token = create_access_token(data={"sub": user['email']})
    
    return {"access_token": access_token, "token_type": "bearer"}

