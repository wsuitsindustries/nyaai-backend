import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = APP_DIR / "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB = os.getenv("MONGO_DB", "nyaai")
REDIS_URL = os.getenv("REDIS_URL", "")

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET or JWT_SECRET in ("change-me-in-production", "dev-jwt-secret-change-in-production"):
    if os.getenv("ENV", "development") == "production":
        raise RuntimeError("JWT_SECRET must be set to a strong random value in production")
    JWT_SECRET = JWT_SECRET or secrets.token_hex(32)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if not CORS_ORIGINS:
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:4173"]
