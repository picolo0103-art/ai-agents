#!/usr/bin/env python3
"""Entry point — start the AI Agents Platform server."""
import sys
import os

# Make sure project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

import uvicorn
from config.settings import settings

if __name__ == "__main__":
    if not settings.groq_api_key:
        print("❌  GROQ_API_KEY manquant. Copie .env.example en .env et renseigne ta clé Groq (gratuit sur console.groq.com).")
        sys.exit(1)

    print(f"🚀  {settings.app_name} v{settings.app_version}")
    print("🌐  Ouvre http://localhost:8000 dans ton navigateur\n")

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info",
    )
