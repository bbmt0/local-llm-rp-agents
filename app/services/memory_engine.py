from __future__ import annotations

from typing import Optional, List

from app.services.memory_types import SessionMemory, AgentMemory
from app.services.llm_types import MemoryUpdate  


class MemoryEngine:
    def ensure_structure(self, session_memory: Dict[str, Any] | None) -> Dict[str, Any]:
        if not isinstance(session_memory, dict):
            session_memory = {}

        facts = session_memory.get("facts_about_player")
        if not isinstance(facts, list):
            facts = []

        events = session_memory.get("recent_events")
        if not isinstance(events, list):
            events = []

        trust_level = session_memory.get("trust_level")
        if not isinstance(trust_level, (int, float)):
            trust_level = 0.0
        trust_level = float(trust_level)

        emotion = session_memory.get("emotion_towards_player")
        if emotion is not None and not isinstance(emotion, str):
            emotion = None

        return {
            "facts_about_player": [f for f in facts if isinstance(f, str) and f.strip()],
            "recent_events": [e for e in events if isinstance(e, str) and e.strip()],
            "trust_level": trust_level,
            "emotion_towards_player": emotion,
        }

    def apply_contract_memory_update(
        self,
        session_memory: Optional[SessionMemory],
        memory_update: MemoryUpdate,
        *,
        max_facts: int = 50,
        max_events: int = 30,
    ) -> SessionMemory:
        memory = self.ensure_structure(session_memory)

        # --- facts_about_player ---
        if memory_update.facts_about_player:
            for fact in memory_update.facts_about_player:
                if not isinstance(fact, str):
                    continue
                fact = fact.strip()
                if not fact:
                    continue
                if fact not in memory["facts_about_player"]:
                    memory["facts_about_player"].append(fact)

        memory["facts_about_player"] = memory["facts_about_player"][-max_facts:]

        # --- recent_events ---
        if memory_update.recent_events:
            for ev in memory_update.recent_events:
                if not isinstance(ev, str):
                    continue
                ev = ev.strip()
                if not ev:
                    continue
                memory["recent_events"].append(ev)

        memory["recent_events"] = memory["recent_events"][-max_events:]

        # --- trust level ---
        delta = float(memory_update.trust_level or 0.0)

        # clamp delta
        if delta > 0.2:
            delta = 0.2
        elif delta < -0.2:
            delta = -0.2

        trust_level = float(memory["trust_level"]) + delta

        # clamp trust_level 0..1
        if trust_level < 0.0:
            trust_level = 0.0
        elif trust_level > 1.0:
            trust_level = 1.0

        memory["trust_level"] = trust_level

        #  emotion_towards_player 
        if memory_update.emotion_towards_player:
            memory["emotion_towards_player"] = memory_update.emotion_towards_player

        return memory


memory_engine = MemoryEngine()
