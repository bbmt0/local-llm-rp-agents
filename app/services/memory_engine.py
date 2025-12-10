from __future__ import annotations

from typing import Dict, Any, List

class MemoryEngine:
    """
    Moteur permettant de mettre à jour la mémoire via la session : 
        - garde les derniers échanges dans recent_events
        - détecte les key_facts_about_player
        - ajuste le trust_level
    """
    
    def ensure_structure(self, session_memory: Dict[str, Any] | None) -> Dict[str, Any]:
        """
            Sécurité pour que la mémoire garde toujours la même structure
        """
        if not isinstance(session_memory, dict):
            session_memory = {}
        
        recent_events = session_memory.get("recent_events")
        if not isinstance(recent_events, list):
            recent_events = []

        facts = session_memory.get("facts_about_player")
        if not isinstance(facts, list):
            facts = []
            
        trust_level = session_memory.get("trust_level")
        if not isinstance(trust_level, float):
            trust_level = 0.0
            
        emotion = session_memory.get("emotion_towards_player")
        if not isinstance(emotion, str) and emotion is not None:
            emotion = None
        
        return {
            "recent_events": recent_events, 
            "facts_about_player": facts, 
            "trust_level": trust_level,
            "trust_level": float(trust_level)
        }
        
    
    def _extract_fact_from_user(self, user_message: str) -> str | None:
        text = user_message.lower().strip()
        triggers_words = ["je suis ", "je m'appelle ", "moi c'est ", "mon nom est ", "mon nom c'est ", "mon prénom"]
        for trig in triggers_words: 
            if trig in text: 
                return user_message
        
        return None
    
    def _update_trust_level(self, trust_level: float, user_message: str, agent_reply: str) -> float: 
        text = user_message.lower()
        
        positive_keywords = ["merci", "enchanté", "sympa", "tu gères", "top"]
        negative_keywords = ["enfoiré"]
        
        d = 0.0
        if any (k in text for k in positive_keywords):
            d += 0.05
        if any (k in text for k in negative_keywords):
            d -= 0.1
            
        new_trust = trust_level + d
        if new_trust < 0.0:
            new_trust = 0.0
        if new_trust > 1.0:
            new_trust = 1.0
            
        return new_trust
    
    def update_session_memory(self, session_memory: Dict[str, Any] | None,
                               user_message: str, agent_reply: str) -> Dict[str, Any]:
        """
        Mise à jour de la mémoire de la sessions  
        """
        
        memory = self.ensure_structure(session_memory)
        
        # AJout évènement récent
        recent_events: List[str] = memory["recent_events"]
        recent_events.append(user_message)
        
        # garder les 20 derniers msg
        if len(recent_events) > 20:
            recent_events = recent_events[-20:]
        memory["recent_events"] = recent_events
        
        #extract facts sur le joueur
        fact = self._extract_fact_from_user(user_message)
        if fact is not None: 
                facts: List[str] = memory("facts_about_player")
                if fact not in facts:
                    facts.append(fact)
                memory["facts_about_player"] = facts
                
        #update le trust level
        memory["trust_level"] = self._update_trust_level(
            trust_level=memory["trust_level"],
            user_message=user_message,
            agent_reply=agent_reply
        )
        
        return memory

memory_engine = MemoryEngine()
        
           
        
        
        