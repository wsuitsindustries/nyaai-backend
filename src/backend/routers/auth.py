import uuid
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.database import get_db
from backend.middleware.auth import create_access_token, get_current_user
from backend.models.schemas import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Simple in-memory auth rate limiter (per IP)
_auth_attempts: dict[str, list[float]] = {}
AUTH_MAX_ATTEMPTS = 5
AUTH_WINDOW = 300  # 5 minutes
_last_auth_cleanup = 0.0


def _check_auth_rate_limit(ip: str) -> None:
    global _last_auth_cleanup
    now = time.time()
    attempts = _auth_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < AUTH_WINDOW]
    if len(attempts) >= AUTH_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
    attempts.append(now)
    _auth_attempts[ip] = attempts

    if now - _last_auth_cleanup > AUTH_WINDOW:
        _last_auth_cleanup = now
        expired = [ip for ip, ts in _auth_attempts.items() if max(ts) < now - AUTH_WINDOW]
        for ip in expired:
            del _auth_attempts[ip]


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(ip)

    if len(req.password) < 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 6 characters")
    if len(req.password) > 128:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password too long")
    if len(req.email) > 254:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email too long")
    if len(req.name) > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name too long")

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


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    current_password: str | None = None
    new_password: str | None = None


@router.put("/profile")
async def update_profile(req: UpdateProfileRequest, current_user: dict = Depends(get_current_user)):
    db = get_db()
    user = await db.users.find_one({"email": current_user["email"]})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update = {}
    if req.name is not None:
        if len(req.name) < 1 or len(req.name) > 100:
            raise HTTPException(status_code=422, detail="Name must be between 1 and 100 characters")
        update["name"] = req.name.strip()

    if req.new_password:
        if not req.current_password:
            raise HTTPException(status_code=400, detail="Current password is required to set a new password")
        if not pwd_ctx.verify(req.current_password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        if len(req.new_password) < 6:
            raise HTTPException(status_code=422, detail="New password must be at least 6 characters")
        if len(req.new_password) > 128:
            raise HTTPException(status_code=422, detail="New password too long")
        update["password_hash"] = pwd_ctx.hash(req.new_password)

    if not update:
        raise HTTPException(status_code=400, detail="No changes provided")

    await db.users.update_one({"email": current_user["email"]}, {"$set": update})

    new_name = update.get("name", user.get("name", ""))
    token = create_access_token({"sub": current_user["email"], "name": new_name})
    return TokenResponse(access_token=token, email=current_user["email"], name=new_name)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    _check_auth_rate_limit(ip)

    db = get_db()
    user = await db.users.find_one({"email": req.email.lower().strip()})
    if not user or not pwd_ctx.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token({"sub": user["email"], "name": user["name"]})
    return TokenResponse(access_token=token, email=user["email"], name=user["name"])
