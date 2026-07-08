import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = APP_DIR / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "nyaai")
REDIS_URL = os.getenv("REDIS_URL", "")

JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173").split(",")
