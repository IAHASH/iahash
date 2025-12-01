# iahash/models.py

from pydantic import BaseModel
from typing import Optional

class IssueFromTextRequest(BaseModel):
    prompt: str
    response: str
    prompt_id: Optional[str] = None
    prompt_description: Optional[str] = None
    model: Optional[str] = None
    subject: Optional[str] = None
    
