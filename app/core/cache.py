"""
Configuración de cache Redis para Cuanto Cuesta
"""
import json
import logging
from typing import Any, Optional, Union
import redis
from redis.exceptions import RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


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
        except RedisError as e:
            logger.error(f"Error conectando a Redis: {e}")
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
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error obteniendo del cache {key}: {e}")
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
        except (RedisError, json.JSONEncodeError) as e:
            logger.error(f"Error estableciendo en cache {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Eliminar valor del cache"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except RedisError as e:
            logger.error(f"Error eliminando del cache {key}: {e}")
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
        except RedisError as e:
            logger.error(f"Error eliminando patrón {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Verificar si existe una clave"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except RedisError as e:
            logger.error(f"Error verificando existencia {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Incrementar valor numérico"""
        if not self.redis_client:
            return None
        
        try:
            return self.redis_client.incrby(key, amount)
        except RedisError as e:
            logger.error(f"Error incrementando {key}: {e}")
            return None
    
    def expire(self, key: str, ttl: int) -> bool:
        """Establecer TTL para una clave"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.expire(key, ttl))
        except RedisError as e:
            logger.error(f"Error estableciendo TTL {key}: {e}")
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

