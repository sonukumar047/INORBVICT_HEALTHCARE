from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class FlowStep(Enum):
    START="start"; NAME="name"; EMAIL="email"; PHONE="phone"; SERVICE="service"; SUMMARY="summary"; END="end"

class FlowData(BaseModel):
    step: FlowStep
    name: Optional[str]=None
    email: Optional[str]=None
    phone: Optional[str]=None
    service: Optional[str]=None

class FlowResponse(BaseModel):
    message: str
    current_step: str
    next_step: Optional[str]=None
    validation_error: Optional[str]=None
    summary: Optional[Dict[str, Any]]=None
    is_complete: bool=False
    metadata: Optional[Dict[str, Any]]=None
