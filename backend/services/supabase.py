import logging
import uuid
from supabase import create_client, Client
from backend.core.config import settings
from fastapi import HTTPException, status
from postgrest import APIError
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SupabaseService:
    def __init__(self):
        try:
            self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    # --- NEW AUTHENTICATION METHODS ---
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single user from the database by their email."""
        try:
            response = self.client.table("users").select("*").eq("email", email).limit(1).execute()
            if response.data:
                return response.data[0]
            return None
        except APIError as e:
            logger.error(f"Supabase error fetching user by email {email}: {e.message}")
            return None

    async def create_user(self, email: str, hashed_password: str) -> Optional[Dict[str, Any]]:
        """Creates a new user in the database."""
        try:
            user_id = str(uuid.uuid4())
            response = self.client.table("users").insert({
                "id": user_id,
                "email": email,
                "hashed_password": hashed_password,
                "subscription_tier": "free" # Default tier
            }).execute()
            if response.data:
                return response.data[0]
            return None
        except APIError as e:
            logger.error(f"Supabase error creating user {email}: {e.message}")
            return None

    # --- EXISTING METHODS ---
    async def find_or_create_user_and_session(self, email: str, chat_id: str):
        """Finds user by email, creates if not exists. Then finds session, creates if not exists."""
        try:
            user = await self.get_user_by_email(email)
            if user:
                user_id = user['id']
            else:
                raise HTTPException(status_code=404, detail=f"User with email {email} not found during session creation.")

            session_response = self.client.table("chat_sessions").select("id").eq("id", chat_id).eq("user_id", user_id).execute()
            
            if not session_response.data:
                self.client.table("chat_sessions").insert({"id": chat_id, "user_id": user_id}).execute()
                logger.info(f"Created new chat session {chat_id} for user {user_id}")

        except (APIError, HTTPException) as e:
            detail = getattr(e, 'message', str(e.detail))
            logger.error(f"Supabase API Error during find/create session: {detail}")
            raise HTTPException(status_code=500, detail="Database error during session setup.")

    async def save_chat_history(self, chat_id: str, req_id: str, email: str, query: str, response: str, models_used: list):
        """Saves the chat history to the Supabase database."""
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
        except (APIError, HTTPException) as e:
            detail = getattr(e, 'message', str(e.detail))
            logger.error(f"Error saving chat history for req_id {req_id}: {detail}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save chat history: {detail}")
        except Exception as e:
            logger.error(f"Unexpected error saving chat history for req_id {req_id}: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An internal error occurred while saving chat data.")
