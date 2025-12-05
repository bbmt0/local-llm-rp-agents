import os
from typing import List, Dict, Any

import httpx


class LLMClient:
    """
    Client simple pour interagir avec Ollama en mode /api/chat.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("OLLAMA_MODEL_NAME", "mistral-nemo")
        self.timeout = 60.0

    async def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Envoie une liste de messages au modèle et renvoie le contenu texte brut
        de la dernière réponse de l'assistant.
        """
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)

        response.raise_for_status()
        data = response.json()

        # Format de réponse Ollama /api/chat :
        # {
        #   "model": "...",
        #   "created_at": "...",
        #   "message": {"role": "assistant", "content": "..."},
        #   ...
        # }
        message = data.get("message") or {}
        content = message.get("content")
        timestamp = message.get("timestamp") or {}

        if not isinstance(content, str):
            raise ValueError("Réponse LLM invalide : 'content' manquant ou non textuel.")

        return content
