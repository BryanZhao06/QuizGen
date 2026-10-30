import os
from dotenv import load_dotenv

# Load key-value pairs from .env into os.environ
load_dotenv()

class Settings:
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6380/0")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

settings = Settings()
