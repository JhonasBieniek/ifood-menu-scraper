from __future__ import annotations

from fastapi import HTTPException, Request

from src.config import config


def check_api_key(request: Request) -> None:
    if not config.API_KEY:
        return
    key = request.headers.get("x-api-key")
    if key != config.API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida ou ausente.")
