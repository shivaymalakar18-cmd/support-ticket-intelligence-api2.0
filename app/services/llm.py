
# app/services/llm.py

from google import genai
from google.genai import types
from app.core.config import settings
from app.utils.logger import logger
import asyncio

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
        return response.text
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"LLM did not respond within {settings.llm_timeout_seconds} seconds"
        )