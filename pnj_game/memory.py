import json
import os
from typing import Dict, Any
from .config import AGENTS_DIR


def get_agent_path(agent_id: str) -> str:
    return os.path.join(AGENTS_DIR, f"{agent_id}.json")


def load_agent(agent_id: str) -> Dict[str, Any]:
    path = get_agent_path(agent_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Aucun fichier agent trouvé pour : {agent_id} ({path})")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_agent(agent_id: str, data: Dict[str, Any]) -> None:
    os.makedirs(AGENTS_DIR, exist_ok=True)
    path = get_agent_path(agent_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
