from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any

from pydantic import BaseModel, ValidationError

from app.services.llm_client import LLMClient
from app.services.llm_types import (PNJReplyContract, ReplyContent, MemoryUpdate, Metagame)


class AgentNotFoundError(Exception):
    pass

class AgentPersonality(BaseModel):
    traits: List[str] = []
    speaking_style: List[str] = []
    motivations: List[str] = []
    taboos: List[str] = []


class AgentLore(BaseModel):
    background: str | None = None
    relations: Dict[str, str] | None = None


class AgentMemory(BaseModel):
    facts_about_player: List[str] = []
    recent_events: List[str] = []
    emotion_towards_player: str | None = None
    trust_level: float | None = None


class AgentConfig(BaseModel):
    id: str
    name: str
    role: str
    system_prompt: str
    personality: AgentPersonality | None = None
    lore: AgentLore | None = None
    memory: AgentMemory | None = None

class AgentManager:
    """
    Gère les prompts des agents, l'appel au LLM et le parsing de la réponse.
    """

    def __init__(self, base_dir: str = "data/agents") -> None:
        self.base_path = Path(base_dir)
        self.llm_client = LLMClient()
        self.agents_config: Dict[str, AgentConfig]= self._load_agents_config()

    def _load_agents_config(self) -> Dict[str, AgentConfig]:
        configs: Dict[str, AgentConfig] = {}

        if not self.base_path.exists():
            return configs

        for path in self.base_path.glob("*.json"):
            try: 
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                
                agent_conf = AgentConfig(**data)
                configs[agent_conf.id] = agent_conf
            except (json.JSONDecodeError, ValidationError) as exc: 
                print(f"[AgentsManager] Erreur de chargement agent depuis {path}: {exc}")

        return configs

    def _get_agent_config(self, agent_id: str) -> AgentConfig:
        config = self.agents_config.get(agent_id)
        if config is None:
            raise AgentNotFoundError(f"Agent inconnu: {agent_id}")
        return config

    @staticmethod
    def _extract_json_content(raw: str) -> str:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("impossible de trouver un JSON dans la réponse")
        return raw[start : end + 1]
    
    async def generate_reply(
        self,
        agent_id: str,
        history: List[Dict[str, str]],
        user_message: str,
        session_memory: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Construit le prompt complet, appelle le LLM, parse la réponse JSON
        et renvoie un dict: {\"text\": str, \"ooc\": bool}.
        """
        agent_config = self._get_agent_config(agent_id)
        system_prompt = agent_config.system_prompt

        messages: List[Dict[str, str]] = []

        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

        for msg in history:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(role, str) and isinstance(content, str):
                messages.append({"role": role, "content": content})

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        raw_response = await self.llm_client.chat(messages)
        
        try: 
            json_str = self._extract_json_content(raw_response)
            contract = PNJReplyContract.model_validate_json(json_str)
        
        except Exception: 
            """
            Si modèle renvoyé ne respecte pas le contract (structure exacte attendue), création d'un contrat minimal artificiel
            """
            fallback_rep = ReplyContent(
                text=raw_response.strip(),
                tone="neutre",
                emotion=None     
            )
            fallback_memory_upd = MemoryUpdate()
            fallback_meta = Metagame(ooc_flag=False,safety_flag=False)

            contract= PNJReplyContract(
                reply= fallback_rep,
                actions=[],
                memory_update= fallback_memory_upd,
                meta=fallback_meta
            )
        return contract


agents_manager = AgentManager()
