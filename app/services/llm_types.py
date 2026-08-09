from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ReplyContent(BaseModel):
    text: str
    tone: str | None = None
    emotion: str | None = None

class Action(BaseModel):
    type: str
    target: str | None = None
    data: Dict[str, Any] | None = None

class MemoryUpdate(BaseModel):
    facts_about_player: List[str] = []
    recent_events: List[str] = []
    trust_level: float = 0.0
    emotion_towards_player: str | None = None
    
class Metagame(BaseModel):
    ooc_flag: bool = False
    safety_flag: bool = False
    
class PNJReplyContract(BaseModel):
    reply: ReplyContent
    actions: List[Action] = Field(default_factory = list)
    memory_update: MemoryUpdate = Field(default_factory = MemoryUpdate)
    meta: Metagame = Field(default_factory = Metagame)


    