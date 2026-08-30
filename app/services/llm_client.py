import os
from typing import List, Dict, Any

import httpx
import logging

logger = logging.getLogger(__name__)

class LLMClient:

    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = os.getenv("OLLAMA_MODEL_NAME", "llama3.2")
        logger.info(f"LLMClient instancié avec model_name={self.model_name}, base_url={self.base_url}")
        self.timeout = httpx.Timeout(
            connect=5.0,   
            read=120.0,    
            write=10.0,
            pool=5.0,
        )
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "2048"))          
        self.num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "256"))   
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
        self.top_p = float(os.getenv("OLLAMA_TOP_P", "0.9"))


    async def chat(self, messages: List[Dict[str, str]]) -> str:

        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }
        
        logger.debug(f"Call à Ollama avec {len(messages)} messages")    
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                logger.debug(f"Réponse reçue de Ollama (status={response.status_code})")


                response.raise_for_status()
                data = response.json()

                message = data.get("message") or {}
                content = message.get("content")

            if not isinstance(content, str):
                logger.debug(f"Ollama answer received:  (status={response.status_code})")
                raise ValueError("LLM answer non valid : 'content' is missing")
            return content
        except httpx.TimeoutException as e:
            logger.error(f"Timeout when calling LLM: {e}")
            raise RuntimeError(f"Timeout when calling the LLM: {e}") from e
