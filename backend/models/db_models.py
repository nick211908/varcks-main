from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Optional
from datetime import datetime
from uuid import UUID

class User(BaseModel):
    """
    Pydantic model representing a user in the database.
    """
    id: UUID
    email: str
    subscription_tier: Literal["free", "pro", "enterprise"] = "free"
    api_key: UUID
    requests_made_this_month: int = 0
    last_request_timestamp: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ChatSession(BaseModel):
    """
    Pydantic model for a chat session.
    """
    id: UUID # Corresponds to chatId
    user_id: UUID
    session_title: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ChatHistory(BaseModel):
    """
    Pydantic model for a single request/response entry in the chat history.
    """
    id: UUID # Corresponds to reqId
    session_id: UUID # Corresponds to chatId
    user_prompt: str
    llm_response: str
    models_used: List[Dict[str, str]]
    created_at: datetime = Field(default_factory=datetime.now)

