import os
from fastapi import Header, HTTPException, status

API_TOKEN = os.getenv("API_BEARER_TOKEN")

def verify_token(authorization: str = Header(...)):
    """
    Vérifie le header Authorization: Bearer <token>
    """
    if not API_TOKEN:
        raise RuntimeError("API_BEARER_TOKEN not configured")

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )

    token = authorization.removeprefix("Bearer ").strip()

    if token != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API token",
        )


