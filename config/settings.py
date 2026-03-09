"""Application settings loaded from environment variables."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root regardless of working directory
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)


class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    app_name: str = os.getenv("APP_NAME", "AI Agents Platform")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
