from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel
from typing import Literal


class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"


class Source(BaseModel):
    title: str
    page: str | None = None
    section: str | None = None
    snippet: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = []


class UploadResponse(BaseModel):
    filename: str
    chunks: int
    conversation_id: str
    document_id: str
    error: str | None = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    results: list[str] = []


DocumentStatus = Literal["uploading", "extracting", "chunking", "embedding", "ready", "failed"]


class DocumentResponse(BaseModel):
    id: str
    filename: str
    size: int
    uploaded_at: datetime
    status: DocumentStatus
    chunks: int
    error: str | None = None


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]


class DocumentStatusResponse(BaseModel):
    id: str
    status: DocumentStatus


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    name: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime
