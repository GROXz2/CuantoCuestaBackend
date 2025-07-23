# backend/auth.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_gpt_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verificar que el request viene de tu GPT"""
    expected_token = "tu_token_secreto_para_gpt"
    
    if credentials.credentials != expected_token:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    return credentials.credentials

# Usar en tus endpoints:
@router.get("/products/search")
async def search_products(
    query: str, 
    category: Optional[str] = None,
    token: str = Depends(verify_gpt_token)
):
    # Tu lógica aquí
    pass
