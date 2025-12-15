import os
from typing import List, Dict, Any

import httpx


class LLMClient:
    """
    Client simple pour interagir avec Ollama en mode /api/chat.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("OLLAMA_MODEL_NAME", "hermes3")
        self.timeout = httpx.Timeout(
            connect=5.0,   # 5s pour se connecter au serveur
            read=120.0,    # 120s max pour lire la réponse du modèle
            write=10.0,
            pool=5.0,
        )
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "2048"))          # 2k au lieu de 128k
        self.num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))   # limite la réponse
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
        self.top_p = float(os.getenv("OLLAMA_TOP_P", "0.9"))


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

        print(f"[LLMClient] Calling {url} with model={self.model_name}, messages={len(messages)}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            # Ici tu verras clairement si c'est un timeout connect/read
            raise RuntimeError(f"Timeout en appelant le LLM: {exc}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Erreur réseau en appelant le LLM: {exc}") from exc

        response.raise_for_status()
        data = response.json()

        message = data.get("message") or {}
        content = message.get("content")

        if not isinstance(content, str):
            raise ValueError("Réponse LLM invalide : 'content' manquant ou non textuel.")

        return content
