from pydantic import BaseModel, Field, EmailStr
from typing import Literal, List, Optional

class File(BaseModel):
    """
    Represents a file object in the request.
    """
    content_type: str = Field(..., description="Content type of the file (e.g., 'text/plain')")
    file_name: str = Field(..., description="Name of the file")
    file_path: str = Field(..., description="Path or URL of the file")


class Req(BaseModel):
    """
    Defines the structure for an incoming request.
    """
    convId: Optional[List[str]] = Field(None, description="Optional list of conversation identifiers.")
    # reqId is now generated on the server for each request.
    chatId: Optional[str] = Field(None, description="Chat session identifier. Omit to start a new chat, include to continue an existing one.")
    
    # The user's identity (email, subscription) will be determined from the
    # authentication token (JWT) provided in the Authorization header,
    # not from the request body.

    query: str = Field(..., description="The main user prompt or query")
    
    files: Optional[List[File]] = Field(None, description="List of files associated with the query")
    
    model: str = Field("auto", description="Model to use. 'auto' enables routing. Specific model names are validated against user subscription.")
    
    isPowerMode: bool = Field(False, description="Flag to enable power mode for more intensive processing")

    class Config:
        # This allows Pydantic to map aliased fields correctly
        populate_by_name = True

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str