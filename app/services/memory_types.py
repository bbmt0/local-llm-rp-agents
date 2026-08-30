from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field

class SessionMemory(TypedDict, total=False):
    facts_about_player: List[str]
    recent_events: List[str]
    trust_level: float
    emotion_towards_player: Optional[str]
    
class AgentMemory(BaseModel):
    facts_about_player: List[str] = Field(default_factory=list)
    recent_events: List[str] = Field(default_factory=list)
    trust_level: Optional[float] = None
    emotion_towards_player: Optional[str] = None
