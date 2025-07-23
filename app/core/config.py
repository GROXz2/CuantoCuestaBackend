"""
Configuración principal de la aplicación Cuanto Cuesta
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:Leon2017@localhost:5432/DealFinder"
    
    # Redis Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    JWT_SECRET_KEY: str = "leon2017"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Cuanto Cuesta API"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    API_RATE_LIMIT_PER_MINUTE: int = 1000
    
    # Chile Configuration
    DEFAULT_TIMEZONE: str = "America/Santiago"
    DEFAULT_CURRENCY: str = "CLP"
    DEFAULT_COUNTRY_CODE: str = "CL"
    DEFAULT_LOCALE: str = "es_CL.UTF-8"
    
    # Cache TTL (seconds)
    CACHE_TTL_PRODUCTS: int = 3600
    CACHE_TTL_PRICES: int = 1800
    CACHE_TTL_STORES: int = 7200
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: str = "logs/app.log"
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignorar campos extra del .env


@lru_cache()
def get_settings():
    """Obtener configuración singleton"""
    return Settings()


# Instancia global de configuración
settings = get_settings()

