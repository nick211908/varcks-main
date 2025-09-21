import logging
from supabase import create_client, Client
from fastapi import HTTPException, status
from postgrest import APIError
from typing import Optional, Dict, Any
from gotrue.errors import AuthError
from backend.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        try:
            # Client for normal user auth (with anon key)
            self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

            # Admin client for user management (with service role key)
            self.admin_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    # ---------------------- AUTH METHODS ----------------------

    async def signup_user(self, email: str, password: str, user_metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Sign up a new user using Supabase Auth.
        This will automatically send a confirmation email if email confirmation is enabled and SMTP is configured.
        """
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata or {"subscription_tier": "free"}
                }
            })

            if response.user:
                return {
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "email_confirmed": response.user.email_confirmed_at is not None,
                        "created_at": response.user.created_at,
                    },
                    "message": "User created successfully. Please check your email for confirmation."
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user account"
                )

        except AuthError as e:
            logger.error(f"Supabase Auth error during signup: {e}")
            if "already registered" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authentication error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during signup: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred during signup"
            )

    async def signin_user(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in a user using Supabase Auth."""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user and response.session:
                user_profile = await self.get_user_profile(response.user.id)
                return {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "token_type": "bearer",
                    "expires_in": response.session.expires_in,
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "email_confirmed": response.user.email_confirmed_at is not None,
                        "subscription_tier": user_profile.get("subscription_tier", "free") if user_profile else "free"
                    }
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )

        except AuthError as e:
            logger.error(f"Supabase Auth error during signin: {e}")
            if "invalid login credentials" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            elif "email not confirmed" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Please confirm your email address before signing in"
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Authentication error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error during signin: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred during signin"
            )

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a Supabase JWT token and return user information."""
        try:
            self.client.auth.set_session(token, "")
            user = self.client.auth.get_user(token)

            if user.user:
                user_profile = await self.get_user_profile(user.user.id)
                return {
                    "id": user.user.id,
                    "email": user.user.email,
                    "email_confirmed": user.user.email_confirmed_at is not None,
                    "subscription_tier": user_profile.get("subscription_tier", "free") if user_profile else "free"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )

        except Exception as e:
            logger.error(f"Token verification error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed"
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token using a refresh token."""
        try:
            response = self.client.auth.refresh_session(refresh_token)
            if response.session:
                return {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                    "token_type": "bearer",
                    "expires_in": response.session.expires_in,
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

    async def signout_user(self, token: str) -> Dict[str, str]:
        """Sign out a user by invalidating their session."""
        try:
            self.client.auth.set_session(token, "")
            self.client.auth.sign_out()
            return {"message": "Successfully signed out"}
        except Exception as e:
            logger.error(f"Error during signout: {e}")
            return {"message": "Signed out"}

    async def resend_confirmation(self, email: str) -> Dict[str, str]:
        """Resend email confirmation (requires SMTP configured)."""
        try:
            self.admin_client.auth.admin.invite_user_by_email(email)
            return {"message": "Confirmation email sent"}
        except Exception as e:
            logger.error(f"Error resending confirmation: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to resend confirmation: {str(e)}"
            )

    async def reset_password(self, email: str) -> Dict[str, str]:
        """Send password reset email."""
        try:
            self.client.auth.reset_password_email(email)
            return {"message": "Password reset email sent"}
        except Exception as e:
            logger.error(f"Error sending password reset: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to send password reset: {str(e)}"
            )

    # ---------------------- USER PROFILE ----------------------

    async def create_user_profile(self, user_id: str, email: str, metadata: Dict) -> Optional[Dict[str, Any]]:
        """Create a user profile in your custom 'users' table."""
        try:
            response = self.client.table("users").insert({
                "id": user_id,
                "email": email,
                "subscription_tier": metadata.get("subscription_tier", "free"),
                "created_at": "now()"
            }).execute()
            if response.data:
                return response.data[0]
            return None
        except APIError as e:
            logger.error(f"Error creating user profile: {e}")
            return None

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from 'users' table."""
        try:
            response = self.client.table("users").select("*").eq("id", user_id).limit(1).execute()
            if response.data:
                return response.data[0]
            return None
        except APIError as e:
            logger.error(f"Error fetching user profile: {e}")
            return None

    async def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user profile in 'users' table."""
        try:
            response = self.client.table("users").update(updates).eq("id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except APIError as e:
            logger.error(f"Error updating user profile: {e}")
            return None

    # ---------------------- LEGACY ----------------------

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from 'users' table."""
        try:
            response = self.client.table("users").select("*").eq("email", email).limit(1).execute()
            if response.data:
                return response.data[0]
            return None
        except APIError as e:
            logger.error(f"Error fetching user by email: {e}")
            return None

    # ---------------------- CHAT METHODS ----------------------

    async def find_or_create_user_and_session(self, email: str, chat_id: str):
        """Find user by email, create if not found, and ensure chat session exists."""
        try:
            user = await self.get_user_by_email(email)
            if not user:
                logger.info(f"User with email {email} not found. Creating new user.")
                insert_resp = self.client.table("users").insert({"email": email}).execute()
                if insert_resp.data:
                    user = insert_resp.data[0]
                else:
                    raise HTTPException(status_code=500, detail="Failed to create new user profile.")

            user_id = user['id']
            session_response = self.client.table("chat_sessions").select("id").eq("id", chat_id).eq("user_id", user_id).execute()
            if not session_response.data:
                self.client.table("chat_sessions").insert({"id": chat_id, "user_id": user_id}).execute()
                logger.info(f"Created new chat session {chat_id} for user {user_id}")

        except Exception as e:
            logger.error(f"Error during session creation for user {email}: {e}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(status_code=500, detail=f"Database error during session setup: {str(e)}")

    async def save_chat_history(self, chat_id: str, req_id: str, email: str, query: str, response: str, models_used: list):
        """Save chat history to 'chat_history' table."""
        try:
            await self.find_or_create_user_and_session(email, chat_id)
            self.client.table("chat_history").insert({
                "id": req_id,
                "session_id": chat_id,
                "user_prompt": query,
                "llm_response": response,
                "models_used": models_used
            }).execute()
            logger.info(f"Successfully saved chat history for req_id {req_id}")
        except Exception as e:
            logger.error(f"Error saving chat history: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save chat history")
