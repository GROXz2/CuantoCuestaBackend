"""
Configuración principal de la aplicación Cuanto Cuesta
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Database
    DATABASE_URL: str

    # Redis Cache
    REDIS_URL: str | None = None

    # JWT
    JWT_SECRET_KEY: str = "leon2017"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Cuanto Cuesta API"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = False
    BASE_URL: str | None = None

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
    ALLOWED_HOSTS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    def model_post_init(self, __context):  # type: ignore[override]
        if not self.REDIS_URL and self.DEBUG:
            self.REDIS_URL = "redis://localhost:6379/0"


@lru_cache()
def get_settings():
    """Obtener configuración singleton"""
    return Settings()


# Instancia global de configuración
settings = get_settings()

