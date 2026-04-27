
# app/modules/services/llm.py

from google import genai
from google.genai import types
from app.core.config import settings
import asyncio
import logging
logger = logging.getLogger(__name__)

def get_client():
    return genai.Client(api_key=settings.gemini_api_key)

# llm.py
async def call_llm(system_prompt: str, prompt: str) -> str:
    client = get_client()
    
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=settings.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.1,
                )
            ),

            timeout=settings.llm_timeout_seconds  # .env se aayega
        )

        if response is None:
            logger.error("LLM returned None response")
            raise ValueError("Empty response from LLM")

        if not hasattr(response, "text") or not response.text:
            logger.error("LLM response missing text")
            raise ValueError("Invalid LLM response format")
        
        return response.text
    
    except asyncio.TimeoutError:
        logger.error(
            f"LLM timeout after {settings.llm_timeout_seconds}s"
        )
        raise TimeoutError(
            f"LLM did not respond within {settings.llm_timeout_seconds} seconds"
        )
    
    except Exception as e:  
        logger.error(f"LLM unexpected error: {e}")
        raise