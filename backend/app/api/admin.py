"""Admin login endpoint — exchange the shared password for a bearer token."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.auth import check_password, create_token

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login(body: LoginRequest):
    if not check_password(body.password):
        raise HTTPException(401, "invalid password")
    return {"token": create_token()}
