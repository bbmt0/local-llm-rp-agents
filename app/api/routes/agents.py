from typing import Dict, List

from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from app.services.agents_service import agents_service, SessionMismatchError, AgentNotFoundError, SessionNotFoundError

from app.core.auth import verify_token


router = APIRouter(prefix="/v0/agents", tags=["agents"])


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



@router.get("", response_model=List[Agent])
async def list_agents() -> List[Agent]:
    try: 
        raw_agents = agents_service.list_agents()
    except RuntimeError as exc: 
        raise HTTPException(status_code=500,detail=str(exc))
    return [Agent(**a) for a in raw_agents]


@router.post("/{agent_id}/sessions", response_model=CreateSessionResponse)
async def create_session(agent_id: str) -> CreateSessionResponse:
    try:
        session_id = agents_service.create_session(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except RuntimeError as exc: 
        raise HTTPException(status_code=500, detail=str(exc))

    return CreateSessionResponse(session_id=session_id, agent_id=agent_id)


@router.post("/{agent_id}/sessions/{session_id}/messages", response_model=MessageResponse, dependencies=[Depends(verify_token)])
async def send_message(
    agent_id: str,
    session_id: str,
    payload: MessageRequest,
    ) -> MessageResponse:
    try:
        result = await agents_service.handle_message(
            agent_id=agent_id,
            session_id=session_id,
            message=payload.message,
            meta=payload.meta,
        )
    except SessionNotFoundError: 
        raise HTTPException(status_code=404, detail="Session not found")
    except SessionMismatchError:
        raise HTTPException(status_code=404, detail="Session not found for this agent")
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    reply_model = MessageReply(
        text=result["reply_text"],
        ooc=result["reply_ooc"],
    )

    return MessageResponse(
            session_id=session_id,
            agent_id=agent_id,
            reply=reply_model,
        )
