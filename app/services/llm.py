
# app/services/llm.py

from google import genai
from google.genai import types
from app.core.config import settings
from app.utils.logger import logger

def get_client():
    return genai.Client(api_key=settings.gemini_api_key)

def call_llm(system_prompt : str, prompt: str) -> str:
    client = get_client()

    logger.debug("Sending request to Gemini...")

    response = client.models.generate_content(
        model=settings.model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.1,        
        )
    )
    return response.text