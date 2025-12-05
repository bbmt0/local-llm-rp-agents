from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


class SessionNotFoundError(Exception):
    """
    Levée lorsque la session demandée n'existe pas sur le disque.
    """
    pass


class MemoryManager:
    """
    Gère la persistance des sessions de conversation sur le disque,
    sous forme de fichiers JSON dans data/sessions/{session_id}.json.
    """

    def __init__(self, base_dir: str = "data/sessions") -> None:
        self.base_path = Path(base_dir)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_id: str) -> Path:
        return self.base_path / f"{session_id}.json"

    def create_session(self, session_id: str, agent_id: str) -> None:
        """
        Crée un fichier de session initial avec l'agent associé et une liste vide de messages.
        Écrase si le fichier existe déjà (ce cas ne devrait pas se produire en usage normal).
        """
        data: Dict[str, Any] = {
            "agent_id": agent_id,
            "messages": [],
        }
        path = self._session_path(session_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_session(self, session_id: str) -> Dict[str, Any]:
        """
        Charge les données d'une session depuis le fichier JSON.
        """
        path = self._session_path(session_id)
        if not path.exists():
            raise SessionNotFoundError(f"Session not found: {session_id}")

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid session data format for {session_id}")

        # On s'assure de la présence des clés principales
        data.setdefault("agent_id", "")
        messages = data.get("messages")
        if not isinstance(messages, list):
            data["messages"] = []

        return data

    def save_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """
        Sauvegarde l'état complet d'une session dans le fichier JSON associé.
        """
        path = self._session_path(session_id)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


memory_manager = MemoryManager()
