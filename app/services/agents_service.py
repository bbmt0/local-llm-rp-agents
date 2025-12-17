from typing import Dict, List, Optional
from uuid import uuid4
from datetime import datetime

from app.services.agents_manager import agents_manager, AgentNotFoundError
from app.services.memory_manager import memory_manager, SessionNotFoundError
from app.services.memory_engine import memory_engine

class SessionMismatchError(Exception):
    """ erreur si session ne correspond pas à l'agent """
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
            raise AgentNotFoundError(f"Agent {agent_id} not found")
        
        sess_id = str(uuid4())
        memory_manager.create_session(session_id=sess_id, agent_id=agent_id)
        return sess_id  
    
    
    
    async def handle_message(
        self,
        agent_id: str,
        session_id: str,
        message: str,
        meta: Optional[Dict[str, str]] = None,
    ) -> Dict[str, object]:
        # 1) Charger la ses sion
        try:
            session_data: Dict[str, object] = memory_manager.load_session(session_id)
        except SessionNotFoundError as exc:
            raise exc

        session_agent_id = session_data.get("agent_id")
        if session_agent_id != agent_id:
            raise SessionMismatchError("Session not found for this agent")

        # 2) Préparer la mémoire de session
        raw_sess_memory = session_data.get("memory")
        if not isinstance(raw_sess_memory, dict):
            agent_cfg = agents_manager.agents_config.get(agent_id)
            if agent_cfg is not None and getattr(agent_cfg, "memory", None) is not None:
                base_memory = agent_cfg.memory.model_dump()
            else:
                base_memory = {
                    "facts_about_player": [],
                    "recent_events": [],
                    "emotion_towards_player": None,
                    "trust_level": 0.0,
                }
            raw_sess_memory = base_memory

        # 3) Récupérer les messages bruts
        raw_messages_obj = session_data.get("messages")
        if not isinstance(raw_messages_obj, list):
            raw_messages: List[Dict[str, object]] = []
        else:
            raw_messages = []
            for msg in raw_messages_obj:
                if isinstance(msg, dict):
                    raw_messages.append(msg)

        # 4) Construire l'historique pour le LLM (sans timestamp)
        history_for_llm: List[Dict[str, str]] = []
        for msg in raw_messages:
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(role, str) and isinstance(content, str):
                history_for_llm.append({"role": role, "content": content})
                history_for_llm = history_for_llm[-12:]

        # 5) Ajouter le message utilisateur
        current_time = datetime.now().astimezone().isoformat()

        user_msg_full = {
            "role": "user",
            "content": message,
            "timestamp": current_time,
        }
        raw_messages.append(user_msg_full)


        # 6) Appeler le LLM via agents_manager
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
            raise RuntimeError("Invalid reply format from LLM: missing 'text'")

        # 7) Ajouter la réponse de l'agent
        current_time_reply = datetime.now().astimezone().isoformat()

        agent_message_full = {
            "role": "assistant",
            "content": reply_text,
            "timestamp": current_time_reply,
        }
        raw_messages.append(agent_message_full)

        # 8) Mettre à jour la mémoire
        updated_memory = memory_engine.apply_contract_memory_update( 
        session_memory=raw_sess_memory,
        memory_update=contract.memory_update,
)


        # 9) Sauvegarder la session
        session_data["messages"] = raw_messages
        session_data["memory"] = updated_memory
        memory_manager.save_session(session_id=session_id, data=session_data)
        
        
        print("[DEBUG] memory_update:", contract.memory_update.model_dump())

        # 10) Retourner les infos utiles au layer API
        return {
            "reply_text": reply_text,
            "reply_ooc": bool(reply_ooc),
        }
    
agents_service = AgentService()