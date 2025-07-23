"""
Servicio de Cache Inteligente
============================

Este servicio gestiona el cache de consultas y resultados para optimizar
el rendimiento y reutilizar datos entre usuarios de forma anónima.

Autor: Manus AI
Fecha: 2024
"""

from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import hashlib
import json
import logging
from dataclasses import asdict

from ..schemas.optimization import OptimizationResponse

logger = logging.getLogger(__name__)


class CacheService:
    """
    Servicio de cache inteligente para optimización de consultas.
    
    Funcionalidades:
    - Cache de resultados de optimización
    - Reutilización anónima de consultas similares
    - Limpieza automática de cache expirado
    - Análisis de patrones de consulta
    """
    
    def __init__(self, redis_client=None, default_ttl_minutes=60):
        self.redis = redis_client  # Cliente Redis para cache distribuido
        self.default_ttl = default_ttl_minutes
        self.memory_cache = {}  # Cache en memoria como fallback
        
    async def get_optimization_result(
        self,
        cache_key: str
    ) -> Optional[OptimizationResponse]:
        """
        Obtiene un resultado de optimización del cache.
        
        Args:
            cache_key: Clave única del cache
            
        Returns:
            OptimizationResponse o None si no existe o expiró
        """
        try:
            # Intentar obtener de Redis primero
            if self.redis:
                cached_data = await self._get_from_redis(cache_key)
                if cached_data:
                    return self._deserialize_optimization_result(cached_data)
            
            # Fallback a cache en memoria
            cached_data = self.memory_cache.get(cache_key)
            if cached_data and not self._is_expired(cached_data):
                return cached_data['result']
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo del cache {cache_key}: {str(e)}")
            return None
    
    async def save_optimization_result(
        self,
        cache_key: str,
        result: OptimizationResponse,
        ttl_minutes: Optional[int] = None
    ) -> bool:
        """
        Guarda un resultado de optimización en el cache.
        
        Args:
            cache_key: Clave única del cache
            result: Resultado a guardar
            ttl_minutes: Tiempo de vida en minutos (opcional)
            
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            ttl = ttl_minutes or self.default_ttl
            
            # Guardar en Redis
            if self.redis:
                await self._save_to_redis(cache_key, result, ttl)
            
            # Guardar en memoria como backup
            self.memory_cache[cache_key] = {
                'result': result,
                'expires_at': datetime.utcnow() + timedelta(minutes=ttl),
                'created_at': datetime.utcnow()
            }
            
            logger.debug(f"Resultado guardado en cache: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando en cache {cache_key}: {str(e)}")
            return False
    
    async def get_similar_query_result(
        self,
        productos: List[str],
        ubicacion_hash: str,
        similarity_threshold: float = 0.8
    ) -> Optional[OptimizationResponse]:
        """
        Busca resultados de consultas similares para reutilizar.
        
        Args:
            productos: Lista de productos buscados
            ubicacion_hash: Hash de la ubicación
            similarity_threshold: Umbral de similitud (0-1)
            
        Returns:
            OptimizationResponse o None si no hay consultas similares
        """
        try:
            # Buscar consultas similares en el cache
            similar_keys = await self._find_similar_cache_keys(
                productos, ubicacion_hash, similarity_threshold
            )
            
            for key in similar_keys:
                result = await self.get_optimization_result(key)
                if result:
                    # Marcar como reutilizado para métricas
                    await self._track_cache_reuse(key)
                    return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error buscando consultas similares: {str(e)}")
            return None
    
    def generate_cache_key(
        self,
        productos: List[str],
        ubicacion: Optional[Dict] = None,
        preferencias: Optional[Dict] = None
    ) -> str:
        """
        Genera una clave única para el cache basada en los parámetros.
        
        Args:
            productos: Lista de productos
            ubicacion: Datos de ubicación (anonimizados)
            preferencias: Preferencias de optimización
            
        Returns:
            str: Clave única del cache
        """
        # Crear hash de productos (ordenados para consistencia)
        productos_sorted = sorted(productos)
        productos_str = "|".join(productos_sorted)
        
        # Hash de ubicación (redondeada para anonimizar)
        ubicacion_str = ""
        if ubicacion:
            # Redondear coordenadas para agrupar ubicaciones cercanas
            lat_rounded = round(ubicacion.get('lat', 0), 2)
            lng_rounded = round(ubicacion.get('lng', 0), 2)
            ubicacion_str = f"{lat_rounded},{lng_rounded}"
        
        # Hash de preferencias
        preferencias_str = ""
        if preferencias:
            # Solo incluir preferencias que afecten el resultado
            relevant_prefs = {
                k: v for k, v in preferencias.items()
                if k in ['prioridad', 'max_supermercados', 'peso_ahorro']
            }
            preferencias_str = json.dumps(relevant_prefs, sort_keys=True)
        
        # Combinar todo y generar hash
        combined_str = f"{productos_str}|{ubicacion_str}|{preferencias_str}"
        cache_key = hashlib.md5(combined_str.encode()).hexdigest()
        
        return f"opt_{cache_key}"
    
    async def cleanup_expired_cache(self) -> int:
        """
        Limpia entradas de cache expiradas.
        
        Returns:
            int: Número de entradas eliminadas
        """
        try:
            cleaned_count = 0
            
            # Limpiar cache en memoria
            expired_keys = [
                key for key, data in self.memory_cache.items()
                if self._is_expired(data)
            ]
            
            for key in expired_keys:
                del self.memory_cache[key]
                cleaned_count += 1
            
            # Limpiar Redis (si está configurado)
            if self.redis:
                redis_cleaned = await self._cleanup_redis_cache()
                cleaned_count += redis_cleaned
            
            logger.info(f"Cache limpiado: {cleaned_count} entradas eliminadas")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error limpiando cache: {str(e)}")
            return 0
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cache para monitoreo.
        
        Returns:
            Dict con estadísticas del cache
        """
        try:
            stats = {
                "memory_cache_size": len(self.memory_cache),
                "memory_cache_entries": list(self.memory_cache.keys()),
                "redis_connected": self.redis is not None,
                "cache_hit_rate": await self._calculate_hit_rate(),
                "most_cached_products": await self._get_popular_products(),
                "cache_efficiency": await self._calculate_cache_efficiency()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {str(e)}")
            return {}
    
    def _is_expired(self, cache_data: Dict) -> bool:
        """Verifica si una entrada de cache ha expirado"""
        return datetime.utcnow() > cache_data['expires_at']
    
    async def _find_similar_cache_keys(
        self,
        productos: List[str],
        ubicacion_hash: str,
        threshold: float
    ) -> List[str]:
        """
        Encuentra claves de cache con consultas similares.
        
        Usa algoritmo de similitud de Jaccard para productos.
        """
        similar_keys = []
        productos_set = set(productos)
        
        # Buscar en cache en memoria
        for key, data in self.memory_cache.items():
            if self._is_expired(data):
                continue
            
            # Extraer productos de la consulta cacheada
            cached_productos = self._extract_products_from_result(data['result'])
            cached_set = set(cached_productos)
            
            # Calcular similitud de Jaccard
            intersection = len(productos_set.intersection(cached_set))
            union = len(productos_set.union(cached_set))
            
            if union > 0:
                similarity = intersection / union
                if similarity >= threshold:
                    similar_keys.append(key)
        
        return similar_keys
    
    def _extract_products_from_result(self, result: OptimizationResponse) -> List[str]:
        """Extrae la lista de productos de un resultado cacheado"""
        productos = []
        
        if result.recomendacion_principal:
            for item in result.recomendacion_principal.productos:
                productos.append(item.nombre)
        
        return productos
    
    async def _track_cache_reuse(self, cache_key: str):
        """Registra el reuso de cache para métricas"""
        # Implementar tracking de métricas
        pass
    
    async def _calculate_hit_rate(self) -> float:
        """Calcula la tasa de aciertos del cache"""
        # Implementar cálculo de hit rate
        return 0.0
    
    async def _get_popular_products(self) -> List[str]:
        """Obtiene los productos más consultados"""
        # Implementar análisis de productos populares
        return []
    
    async def _calculate_cache_efficiency(self) -> float:
        """Calcula la eficiencia del cache"""
        # Implementar cálculo de eficiencia
        return 0.0
    
    # Métodos específicos de Redis
    async def _get_from_redis(self, key: str) -> Optional[Dict]:
        """Obtiene datos de Redis"""
        if not self.redis:
            return None
        
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error obteniendo de Redis {key}: {str(e)}")
            return None
    
    async def _save_to_redis(
        self,
        key: str,
        result: OptimizationResponse,
        ttl_minutes: int
    ):
        """Guarda datos en Redis"""
        if not self.redis:
            return
        
        try:
            # Serializar resultado
            data = self._serialize_optimization_result(result)
            
            # Guardar con TTL
            await self.redis.setex(
                key,
                ttl_minutes * 60,  # Redis usa segundos
                json.dumps(data)
            )
        except Exception as e:
            logger.error(f"Error guardando en Redis {key}: {str(e)}")
    
    async def _cleanup_redis_cache(self) -> int:
        """Limpia cache expirado en Redis"""
        # Redis maneja TTL automáticamente, pero podemos hacer limpieza manual
        return 0
    
    def _serialize_optimization_result(self, result: OptimizationResponse) -> Dict:
        """Serializa OptimizationResponse para cache"""
        return asdict(result)
    
    def _deserialize_optimization_result(self, data: Dict) -> OptimizationResponse:
        """Deserializa datos de cache a OptimizationResponse"""
        return OptimizationResponse(**data)

