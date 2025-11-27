import json
from typing import Dict, Any
from .llm import call_ollama_chat


def build_system_prompt_from_agent(agent: Dict[str, Any]) -> str:
    name = agent.get("name", "PNJ")
    role = agent.get("role", "personnage non-joueur")
    personality = agent.get("personality", {})
    lore = agent.get("lore", {})
    memory = agent.get("memory", {})

    traits = ", ".join(personality.get("traits", []))
    speaking_style = "; ".join(personality.get("speaking_style", []))
    motivations = "; ".join(personality.get("motivations", []))
    taboos = "; ".join(personality.get("taboos", []))

    background = lore.get("background", "")
    relations = lore.get("relations", {})

    facts_about_player = memory.get("facts_about_player", [])
    recent_events = memory.get("recent_events", [])
    emotion = memory.get("emotion_towards_player", "neutre")
    trust_level = memory.get("trust_level", 0.0)

    relations_lines = []
    for rel_name, rel_desc in relations.items():
        relations_lines.append(f"- {rel_name} : {rel_desc}")
    relations_str = "\n".join(relations_lines)

    facts_lines = [f"- {fact}" for fact in facts_about_player]
    recent_lines = [f"- {ev}" for ev in recent_events]

    facts_str = "\n".join(facts_lines)
    recent_str = "\n".join(recent_lines)

    system_prompt = f"""
Tu es un PNJ dans un jeu de rôle textuel.

Identité :
- Nom : {name}
- Rôle : {role}

Personnalité :
- Traits : {traits}
- Style de parole : {speaking_style}
- Motivations : {motivations}
- Taboos : {taboos}

Lore :
- Contexte : {background}
Relations :
{relations_str}

Mémoire actuelle sur le joueur :
{facts_str}

Événements récents pertinents :
{recent_str}

État émotionnel envers le joueur :
- Emotion : {emotion}
- Niveau de confiance (0 à 1) : {trust_level}

Règles de réponse :
- Tu réponds uniquement en français.
- Tu ne sors jamais de ton rôle.
- Tu peux décrire brièvement l'ambiance autour de toi, mais tu te concentres sur le dialogue.
- Tu tutoies le joueur si c'est cohérent avec ta personnalité.
- Tu restes à la première personne.

Tu vas maintenant répondre au joueur en respectant tout ce contexte.
    """.strip()

    return system_prompt


def generate_pnj_reply(agent: Dict[str, Any], player_message: str, model: str) -> str:
    system_prompt = build_system_prompt_from_agent(agent)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": player_message},
    ]

    reply = call_ollama_chat(messages=messages, model=model, stream=False)
    return reply


def update_agent_memory_with_llm(
    agent: Dict[str, Any],
    conversation_snippet: str,
    model: str,
) -> Dict[str, Any]:
    """
    Utilise le LLM pour mettre à jour la mémoire de l'agent.
    `conversation_snippet` doit contenir le dernier échange (Joueur + PNJ).
    """
    system_prompt = (
        "Tu es un gestionnaire de mémoire pour un PNJ dans un jeu de rôle textuel. "
        "Tu reçois la mémoire actuelle du PNJ au format JSON, ainsi qu'un extrait de "
        "la conversation récente. Tu dois mettre à jour la mémoire en gardant : "
        "les faits importants sur le joueur, les événements récents, et en ajustant "
        "éventuellement l'émotion et le niveau de confiance. "
        "Tu renvoies UNIQUEMENT le JSON mis à jour, sans explication ni texte autour."
    )

    user_content = (
        "Mémoire actuelle du PNJ :\n"
        + json.dumps(agent.get("memory", {}), ensure_ascii=False, indent=2)
        + "\n\nExtrait de conversation récente :\n"
        + conversation_snippet
        + "\n\nDonne la mémoire mise à jour au format JSON."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    updated_memory_str = call_ollama_chat(messages=messages, model=model, stream=False)

    # On parse le JSON renvoyé par le LLM
    updated_memory = json.loads(updated_memory_str)
    agent["memory"] = updated_memory
    return agent
