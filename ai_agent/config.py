from pydantic_settings import BaseSettings
from typing import Dict, Any

class Settings(BaseSettings):
    gemini_api_key: str
    mcp_servers_config: str = '{}'

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
