import requests
from typing import List, Dict, Any
from .config import OLLAMA_URL, DEFAULT_MODEL


def call_ollama_chat(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    stream: bool = False,
) -> str:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()

    # Format de réponse standard d'Ollama : {"message": {"content": "..."}}
    if "message" in data and "content" in data["message"]:
        return data["message"]["content"]

    # fallback si jamais le format change
    raise ValueError(f"Réponse inattendue d'Ollama : {data}")
