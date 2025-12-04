from typing import Dict, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/agents", tags=["agents"])


class Agent(BaseModel):
    id: str
    name: str
    description: str


class CreateSessionResponse(BaseModel):
    session_id: str = Field(..., alias="session_id")
    agent_id: str = Field(..., alias="agent_id")


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    meta: Dict[str, str] | None = None


class MessageResponse(BaseModel):
    session_id: str
    agent_id: str
    reply: Dict[str, str]


AGENTS: List[Agent] = [
    Agent(
        id="gangster_los_santos",
        name="Gangster de Los Santos",
        description="PNJ RP gangster, style GTA-like, parle français familier.",
    )
]


# sessions_in_memory[session_id] = {"agent_id": "...", "messages": [...]}
SESSIONS: Dict[str, Dict] = {}


@router.get("", response_model=List[Agent])
async def list_agents() -> List[Agent]:
    return AGENTS


@router.post("/{agent_id}/sessions", response_model=CreateSessionResponse)
async def create_session(agent_id: str) -> CreateSessionResponse:
    agent = next((a for a in AGENTS if a.id == agent_id), None)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    session_id = str(uuid4())
    SESSIONS[session_id] = {"agent_id": agent_id, "messages": []}

    return CreateSessionResponse(session_id=session_id, agent_id=agent_id)


@router.post("/{agent_id}/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    agent_id: str,
    session_id: str,
    payload: MessageRequest,
) -> MessageResponse:
    session = SESSIONS.get(session_id)
    if session is None or session.get("agent_id") != agent_id:
        raise HTTPException(status_code=404, detail="Session not found for this agent")

    user_message = {
        "role": "user",
        "content": payload.message,
    }
    session["messages"].append(user_message)

    # Stub pour l’instant : plus tard on appellera ton moteur PNJ + Ollama ici.
    reply_text = f"[STUB] Réponse RP pour: {payload.message}"

    assistant_message = {
        "role": "assistant",
        "content": reply_text,
    }
    session["messages"].append(assistant_message)

    return MessageResponse(
        session_id=session_id,
        agent_id=agent_id,
        reply={
            "text": reply_text,
            "ooc": "false",
        },
    )
