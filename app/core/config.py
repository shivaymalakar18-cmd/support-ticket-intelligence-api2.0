
# app/core/config.py

from pydantic_settings import BaseSettings
from pydantic import ConfigDict

# pydantic-setting -> this function gets the environment variables
class Settings(BaseSettings):
    app_name: str
    debug: bool = True

    # LLM key
    gemini_api_key: str | None = None
    model_name: str
    llm_timeout_seconds: int

    model_config = ConfigDict(
        env_file=".env"
    )


settings = Settings()