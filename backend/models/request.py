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
    convId: List[str] = Field(..., description="List of conversation identifiers")
    reqId: str = Field(..., description="Unique request identifier")
    chatId: str = Field(..., description="Chat session identifier")
    
    # CORRECTED LINE: Using snake_case for the attribute name
    # and aliasing it to accept 'userSubs' from the JSON request.
    user_subs: Literal["free", "pro", "enterprise"] = Field(..., alias="userSubs", description="User subscription level")
    
    email: EmailStr = Field(..., description="User email address")
    jwt_token: str = Field(..., description="JSON Web Token for authentication")

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