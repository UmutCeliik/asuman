# instagram-worker/security.py

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
import hmac
import logging

from config import ORCHESTRATOR_SECRET_TOKEN

API_KEY_HEADER = APIKeyHeader(name="X-Orchestrator-Token")

def verify_token(token: str = Security(API_KEY_HEADER)):
    """Gelen token'ın geçerli olup olmadığını kontrol eder."""
    if not ORCHESTRATOR_SECRET_TOKEN:
        logging.critical("ORCHESTRATOR_SECRET_TOKEN sırrı ayarlanmamış!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Uygulama güvenlik sırrı yapılandırılmamış."
        )
    
    # Güvenli karşılaştırma
    if not hmac.compare_digest(token, ORCHESTRATOR_SECRET_TOKEN):
        logging.warning(f"Geçersiz token ile istek denemesi: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz veya eksik kimlik doğrulama token'ı."
        )
    return True
