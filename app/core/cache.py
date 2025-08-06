"""
Configuración de cache Redis para Cuanto Cuesta
"""
import json
from typing import Any, Optional, Union
import redis
import structlog
from redis.exceptions import RedisError

from app.core.config import settings

logger = structlog.get_logger(__name__)


class RedisCache:
    """Cliente Redis para cache"""
    
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Conectar a Redis"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Probar conexión
            self.redis_client.ping()
            logger.info("Conexión a Redis exitosa")
        except RedisError:
            logger.exception("Error conectando a Redis")
            self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Obtener valor del cache"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError):
            logger.exception("Error obteniendo del cache", key=key)
            return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """Establecer valor en el cache"""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            if ttl:
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                return self.redis_client.set(key, serialized_value)
        except (RedisError, json.JSONEncodeError):
            logger.exception("Error estableciendo en cache", key=key)
            return False
    
    def delete(self, key: str) -> bool:
        """Eliminar valor del cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except RedisError:
            logger.exception("Error eliminando del cache", key=key)
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Eliminar claves que coincidan con el patrón"""
        if not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except RedisError:
            logger.exception("Error eliminando patrón", pattern=pattern)
            return 0
    
    def exists(self, key: str) -> bool:
        """Verificar si existe una clave"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except RedisError:
            logger.exception("Error verificando existencia", key=key)
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Incrementar valor numérico"""
        if not self.redis_client:
            return None
        
        try:
            return self.redis_client.incrby(key, amount)
        except RedisError:
            logger.exception("Error incrementando", key=key)
            return None
    
    def expire(self, key: str, ttl: int) -> bool:
        """Establecer TTL para una clave"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.expire(key, ttl))
        except RedisError:
            logger.exception("Error estableciendo TTL", key=key)
            return False


# Instancia global del cache
cache = RedisCache()


def get_cache() -> RedisCache:
    """Dependency para obtener instancia de cache"""
    return cache


# Funciones de utilidad para cache específico
def cache_product_key(product_id: str) -> str:
    """Generar clave de cache para producto"""
    return f"product:{product_id}"


def cache_store_key(store_id: str) -> str:
    """Generar clave de cache para tienda"""
    return f"store:{store_id}"


def cache_price_key(product_id: str, store_id: str) -> str:
    """Generar clave de cache para precio"""
    return f"price:{product_id}:{store_id}"


def cache_search_key(query: str, filters: dict) -> str:
    """Generar clave de cache para búsqueda"""
    filter_str = "_".join([f"{k}:{v}" for k, v in sorted(filters.items())])
    return f"search:{query}:{filter_str}"

