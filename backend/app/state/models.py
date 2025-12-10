from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ConversationMessage(BaseModel):
    role: str # system, user, assistant, tool
    content: str | None = None
    tool_calls: List[Dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None # For tool role

class RentalSession(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated_at: datetime = Field(default_factory=datetime.now)
    
    # Context
    user_preferences: Dict[str, Any] = Field(default_factory=dict)
