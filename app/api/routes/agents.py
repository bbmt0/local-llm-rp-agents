from typing import Dict, List
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.agents_manager import agents_manager, AgentNotFoundError
from app.services.memory_manager import memory_manager, SessionNotFoundError

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


class MessageReply(BaseModel):
    text: str
    ooc: bool


class MessageResponse(BaseModel):
    session_id: str
    agent_id: str
    reply: MessageReply


AGENTS: List[Agent] = [
    Agent(
        id="gangster_los_santos",
        name="Gangster de Los Santos",
        description="PNJ RP gangster, style GTA-like, parle français familier.",
    )
]


@router.get("", response_model=List[Agent])
async def list_agents() -> List[Agent]:
    return AGENTS


@router.post("/{agent_id}/sessions", response_model=CreateSessionResponse)
async def create_session(agent_id: str) -> CreateSessionResponse:
    agent = next((a for a in AGENTS if a.id == agent_id), None)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    session_id = str(uuid4())

    memory_manager.create_session(session_id=session_id, agent_id=agent_id)

    return CreateSessionResponse(session_id=session_id, agent_id=agent_id)


@router.post("/{agent_id}/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    agent_id: str,
    session_id: str,
    payload: MessageRequest,
) -> MessageResponse:
    # 1) Charger la session
    try:
        session_data: Dict[str, object] = memory_manager.load_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    session_agent_id = session_data.get("agent_id")
    if session_agent_id != agent_id:
        raise HTTPException(status_code=404, detail="Session not found for this agent!")

    # 2) Récupérer les messages bruts (ceux du fichier, avec timestamp éventuel)
    raw_messages_obj = session_data.get("messages")
    if not isinstance(raw_messages_obj, list):
        raw_messages: List[Dict[str, object]] = []
    else:
        raw_messages = []
        for msg in raw_messages_obj:
            if isinstance(msg, dict):
                raw_messages.append(msg)

    # 3) Construire l'historique à envoyer au LLM (sans timestamp)
    history_for_llm: List[Dict[str, str]] = []
    for msg in raw_messages:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(role, str) and isinstance(content, str):
            history_for_llm.append({"role": role, "content": content})

    # 4) Ajouter le message utilisateur (dans les deux mondes)
    current_time = datetime.now().astimezone().isoformat()

    user_msg_full = {
        "role": "user",
        "content": payload.message,
        "timestamp": current_time,
    }
    raw_messages.append(user_msg_full)

    user_msg_for_llm = {
        "role": "user",
        "content": payload.message,
    }
    history_for_llm.append(user_msg_for_llm)

    # 5) Appeler le LLM via agents_manager
    try:
        reply_dict = await agents_manager.generate_reply(
            agent_id=agent_id,
            history=history_for_llm,
            user_message=payload.message,
        )
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}")

    # 6) Ajouter la réponse de l'assistant (dans les deux mondes)
    current_time_reply = datetime.now().astimezone().isoformat()

    assistant_message_full = {
        "role": "assistant",
        "content": reply_dict["text"],
        "timestamp": current_time_reply,
    }
    raw_messages.append(assistant_message_full)

    # 7) Sauvegarder les messages complets dans la session
    session_data["messages"] = raw_messages
    memory_manager.save_session(session_id=session_id, data=session_data)

    # 8) Construire la réponse HTTP
    reply_model = MessageReply(text=reply_dict["text"], ooc=reply_dict["ooc"])

    return MessageResponse(
        session_id=session_id,
        agent_id=agent_id,
        reply=reply_model,
    )
