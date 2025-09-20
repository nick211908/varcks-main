from pydantic import BaseModel, Field
from typing import Literal,List,Dict

class Res(BaseModel):
    reqId:str = Field(..., description="Unique request identifier")
    chatId:str = Field(..., description="Chat session identifier")
    query: str = Field(..., description="Search query string")
    Models:List[Dict[str,str]]=Field(..., description="List of models used in the response of mircoprompt")
    response: str = Field(..., description="Response to the query")
    statusCode: int = Field(..., description="Status code of the response")
    statusMessage: str = Field(..., description="Status message of the response")