from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

from app.services.agents_manager import agents_manager, AgentNotFoundError
from app.services.memory_manager import memory_manager, SessionNotFoundError
from app.services.memory_engine import memory_engine

class SessionMismatchError(Exception):
    logging.error(f"Session not found for this agent")
    pass

class AgentService:
    def list_agents(self) -> List[Dict[str, str]]:
        agents: List[Dict[str, str]] = []
        
        for conf in agents_manager.agents_config.values():
            if conf.lore and getattr(conf.lore, "background", None):
                descr=  f"{conf.role} — {conf.lore.background}"
            else:
                descr= conf.role
                
            agents.append(
                {
                    "id": conf.id,
                    "name": conf.name,
                    "description": descr,
                }
            )
        return agents

    def create_session(self, agent_id: str) -> str:
        if agent_id not in agents_manager.agents_config:
            logging.warning(f"Agent {agent_id} not found in agent_manager")
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        
        sess_id = str(uuid4())
        memory_manager.create_session(session_id=sess_id, agent_id=agent_id)
        logging.info(f"New session {sess_id} for agent {agent_id} created")
        return sess_id  
    
    
    
    async def handle_message(
        self,
        agent_id: str,
        session_id: str,
        message: str,
        meta: Optional[Dict[str, str]] = None,
    ) -> Dict[str, object]:
        logging.info(f"Loading session {session_id} for the agent {agent_id}")
        try:
            session_data: Dict[str, object] = memory_manager.load_session(session_id)
        except SessionNotFoundError as exc:
            logging.warning(f"Session {session_id} not found")
            raise exc

        session_agent_id = session_data.get("agent_id")
        if session_agent_id != agent_id:
            logging.warning(f"Session {session_id} not found for {agent_id}")
            raise SessionMismatchError("Session not found for this agent")

        logging.info(f"Loading session memory")
        raw_sess_memory = session_data.get("memory")
        if not isinstance(raw_sess_memory, dict):
            logging.info(f"Session memory not insanciated")
            agent_cfg = agents_manager.agents_config.get(agent_id)
            if agent_cfg is not None and getattr(agent_cfg, "memory", None) is not None:
                logging.info(f"Loading {agent_id} base memory")
                base_memory = agent_cfg.memory.model_dump()
            else:
                logging.info(f"Loading base memory")
                base_memory = {
                    "facts_about_player": [],
                    "recent_events": [],
                    "emotion_towards_player": None,
                    "trust_level": 0.0,
                }
            raw_sess_memory = base_memory

        logging.info(f"Get session {session_id} : {session_agent_id} raw messages object")
        raw_messages_obj = session_data.get("messages")
        if not isinstance(raw_messages_obj, list):
            logging.warning(f"Raw messages not loaded for session {session_id} : {session_agent_id}")
            raw_messages: List[Dict[str, object]] = []
        else:
            logging.info(f"Retrieving all raw messages from session {session_id}")
            raw_messages = []
            for msg in raw_messages_obj:
                if isinstance(msg, dict):
                    raw_messages.append(msg)

        logging.info(f"Creating historique object for the LLM from session {session_id}")
        history_for_llm: List[Dict[str, str]] = []
        for msg in raw_messages:
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(role, str) and isinstance(content, str):
                history_for_llm.append({"role": role, "content": content})
                history_for_llm = history_for_llm[-12:]

        logging.info(f"Adding user message for session {session_id} with timestamp")
        current_time = datetime.now().astimezone().isoformat()

        user_msg_full = {
            "role": "user",
            "content": message,
            "timestamp": current_time,
        }
        raw_messages.append(user_msg_full)


        try:
            contract = await agents_manager.generate_reply(
                agent_id=agent_id,
                history=history_for_llm,
                user_message=message,
                session_memory=raw_sess_memory                
            )
        except AgentNotFoundError as exc:
            raise exc
        except Exception as exc:
            raise RuntimeError(f"LLM error: {exc}") from exc

        reply_text = contract.reply.text
        reply_ooc = contract.meta.ooc_flag

        if not isinstance(reply_text, str):
            logging.warning(f"Missing text, 'reply_text' is not an instance")
            raise RuntimeError("Invalid reply format from LLM: missing 'text'")

        current_time_reply = datetime.now().astimezone().isoformat()

        agent_message_full = {
            "role": "assistant",
            "content": reply_text,
            "timestamp": current_time_reply,
        }
        raw_messages.append(agent_message_full)
    
        logging.info(f"Updating memory...")
        updated_memory = memory_engine.apply_contract_memory_update( 
        session_memory=raw_sess_memory,
        memory_update=contract.memory_update,
)

        session_data["messages"] = raw_messages
        session_data["memory"] = updated_memory
        memory_manager.save_session(session_id=session_id, data=session_data)
        
        
        logging.info(f"Memory updated: memory_update {contract.memory_update.model_dump()}")

        return {
            "reply_text": reply_text,
            "reply_ooc": bool(reply_ooc),
        }
    
agents_service = AgentService()