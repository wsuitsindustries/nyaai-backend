import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext

from backend.database import get_db
from backend.middleware.auth import create_access_token
from backend.models.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    db = get_db()
    existing = await db.users.find_one({"email": req.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    now = datetime.now(timezone.utc)
    user = {
        "id": str(uuid.uuid4()),
        "name": req.name.strip(),
        "email": req.email.lower().strip(),
        "password_hash": pwd_ctx.hash(req.password),
        "created_at": now,
    }
    await db.users.insert_one(user)

    token = create_access_token({"sub": user["email"], "name": user["name"]})
    return TokenResponse(access_token=token, email=user["email"], name=user["name"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    db = get_db()
    user = await db.users.find_one({"email": req.email.lower().strip()})
    if not user or not pwd_ctx.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": user["email"], "name": user["name"]})
    return TokenResponse(access_token=token, email=user["email"], name=user["name"])
