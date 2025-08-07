# backend/auth.py
"""Funciones de autenticación y utilidades relacionadas."""

import os

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)



# Token de acceso utilizado por el GPT
API_TOKEN = os.getenv("GPT_API_TOKEN", "tu_token_secreto_para_gpt")

# Esquema HTTP Bearer para autenticación por token simple
security = HTTPBearer()


async def verify_gpt_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Verifica que el request provenga del GPT autorizado."""
    from app.main import ERROR_MESSAGES

    if credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail=ERROR_MESSAGES["INVALID_TOKEN"])
    return credentials.credentials


# Esquema OAuth2 para futura autenticación JWT
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "user": "Acceso de usuario estándar",
        "admin": "Privilegios administrativos",
    },
)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Placeholder para validación de JWT y scopes."""
    raise HTTPException(status_code=501, detail="Autenticación JWT no implementada")

