from __future__ import annotations

import json
from typing import Dict, List, Any

from app.services.llm_client import LLMClient


class AgentNotFoundError(Exception):
    pass


class AgentManager:
    """
    Gère les prompts des agents, l'appel au LLM et le parsing de la réponse.
    """

    def __init__(self) -> None:
        self.llm_client = LLMClient()
        self.agents_config: Dict[str, Dict[str, Any]] = self._load_agents_config()

    def _load_agents_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Pour le MVP, config hardcodée.
        Plus tard : chargement depuis fichiers JSON / BDD.
        """
        gangster_system_prompt = (
    "Tu es un PNJ dans un serveur de roleplay texte francophone. "
    "Ton personnage est un gangster de Los Santos, ambiance GTA, langage familier, "
    "mais tu restes jouable et compréhensible. "
    "Tu dois STRICTEMENT rester dans le personnage (in-character). "
    "Tu ne dois jamais mentionner que tu es une IA ou un modèle de langage. "
    "Lorsque le joueur te donne des informations sur lui-même (par exemple son nom, son surnom, "
    "son âge, ses affiliations, etc.), tu dois les mémoriser pour toute la session et les réutiliser "
    "plus tard dans la conversation. "
    "Si le nom du joueur est déjà apparu plus tôt dans la conversation, tu ne dois JAMAIS prétendre "
    "que tu l'as oublié ou redemander son nom ; tu dois le réutiliser directement. "
    "Tu réponds UNIQUEMENT au format JSON suivant :\n\n"
    "{\n"
    '  \"reply_text\": \"la réplique RP que tu envoies au joueur\",\n'
    '  \"is_ooc\": false\n'
    "}\n\n"
    "Pas de texte en dehors du JSON. Pas de balises, pas d'explication."
)


        return {
            "gangster_los_santos": {
                "system_prompt": gangster_system_prompt,
            }
        }

    def _get_agent_config(self, agent_id: str) -> Dict[str, Any]:
        config = self.agents_config.get(agent_id)
        if config is None:
            raise AgentNotFoundError(f"Agent inconnu: {agent_id}")
        return config

    async def generate_reply(
        self,
        agent_id: str,
        history: List[Dict[str, str]],
        user_message: str,
    ) -> Dict[str, Any]:
        """
        Construit le prompt complet, appelle le LLM, parse la réponse JSON
        et renvoie un dict: {\"text\": str, \"ooc\": bool}.
        """
        agent_config = self._get_agent_config(agent_id)
        system_prompt = agent_config["system_prompt"]

        messages: List[Dict[str, str]] = []

        messages.append(
            {
                "role": "system",
                "content": system_prompt,
            }
        )

        # Historique des messages : on le passe tel quel pour le MVP.
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

        reply_text: str
        is_ooc: bool

        try:
            parsed = json.loads(raw_response)
            if not isinstance(parsed, dict):
                raise ValueError("JSON de réponse non dict.")

            reply_text_value = parsed.get("reply_text")
            if not isinstance(reply_text_value, str):
                raise ValueError("Champ 'reply_text' manquant ou non textuel.")

            is_ooc_value = parsed.get("is_ooc", False)
            is_ooc_bool = bool(is_ooc_value)

            reply_text = reply_text_value
            is_ooc = is_ooc_bool
        except Exception:
            # Fallback : si le modèle n'a pas respecté le format,
            # on renvoie le texte brut et on marque ooc = False.
            reply_text = raw_response
            is_ooc = False

        return {
            "text": reply_text,
            "ooc": is_ooc,
        }


agents_manager = AgentManager()
