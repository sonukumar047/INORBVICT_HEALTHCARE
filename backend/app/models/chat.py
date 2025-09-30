from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    message: str
    session_id: str
    metadata: Optional[Dict[str, Any]] = None
