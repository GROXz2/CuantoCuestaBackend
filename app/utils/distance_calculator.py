"""
Utilidad de Cálculo de Distancias
=================================

Esta utilidad proporciona funciones para calcular distancias geográficas
y tiempos de viaje entre ubicaciones.

Autor: Manus AI
Fecha: 2024
"""

from typing import Tuple, Optional, Dict, List
import math
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Coordenadas:
    """Representa coordenadas geográficas"""
    lat: float
    lng: float
    
    def __post_init__(self):
        """Validar coordenadas"""
        if not (-90 <= self.lat <= 90):
            raise ValueError(f"Latitud inválida: {self.lat}")
        if not (-180 <= self.lng <= 180):
            raise ValueError(f"Longitud inválida: {self.lng}")


@dataclass
class DistanceResult:
    """Resultado de cálculo de distancia"""
    distance_km: float
    duration_minutes: Optional[int] = None
    route_type: str = "straight_line"  # straight_line, driving, walking


class DistanceCalculator:
    """
    Calculadora de distancias geográficas y tiempos de viaje.
    
    Funcionalidades:
    - Cálculo de distancia en línea recta (Haversine)
    - Estimación de tiempo de viaje
    - Integración con APIs de mapas (opcional)
    - Cache de cálculos frecuentes
    """
    
    def __init__(self, maps_api_key: Optional[str] = None):
        self.maps_api_key = maps_api_key
        self.distance_cache = {}
        
        # Velocidades promedio para estimaciones
        self.average_speeds = {
            "driving": 30,  # km/h en ciudad
            "walking": 5,   # km/h caminando
            "cycling": 15   # km/h en bicicleta
        }
    
    async def calculate_distance(
        self,
        origin: Coordenadas,
        destination: Coordenadas,
        mode: str = "driving"
    ) -> DistanceResult:
        """
        Calcula la distancia entre dos puntos.
        
        Args:
            origin: Coordenadas de origen
            destination: Coordenadas de destino
            mode: Modo de transporte (driving, walking, cycling)
            
        Returns:
            DistanceResult: Resultado con distancia y tiempo estimado
        """
        try:
            # Verificar cache primero
            cache_key = self._generate_cache_key(origin, destination, mode)
            if cache_key in self.distance_cache:
                return self.distance_cache[cache_key]
            
            # Calcular distancia en línea recta (siempre disponible)
            straight_distance = self._haversine_distance(origin, destination)
            
            # Intentar obtener distancia real si hay API disponible
            if self.maps_api_key and mode == "driving":
                real_result = await self._get_real_distance(origin, destination, mode)
                if real_result:
                    self.distance_cache[cache_key] = real_result
                    return real_result
            
            # Usar estimación basada en línea recta
            estimated_result = self._estimate_travel_time(straight_distance, mode)
            self.distance_cache[cache_key] = estimated_result
            
            return estimated_result
            
        except Exception as e:
            logger.error(f"Error calculando distancia: {str(e)}")
            # Retornar estimación básica en caso de error
            return DistanceResult(
                distance_km=self._haversine_distance(origin, destination),
                duration_minutes=None,
                route_type="straight_line"
            )
    
    def _haversine_distance(self, origin: Coordenadas, destination: Coordenadas) -> float:
        """
        Calcula la distancia en línea recta usando la fórmula de Haversine.
        
        Args:
            origin: Coordenadas de origen
            destination: Coordenadas de destino
            
        Returns:
            float: Distancia en kilómetros
        """
        # Radio de la Tierra en kilómetros
        R = 6371.0
        
        # Convertir grados a radianes
        lat1_rad = math.radians(origin.lat)
        lon1_rad = math.radians(origin.lng)
        lat2_rad = math.radians(destination.lat)
        lon2_rad = math.radians(destination.lng)
        
        # Diferencias
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Fórmula de Haversine
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = R * c
        return round(distance, 2)
    
    def _estimate_travel_time(self, distance_km: float, mode: str) -> DistanceResult:
        """
        Estima el tiempo de viaje basándose en la distancia y modo de transporte.
        
        Args:
            distance_km: Distancia en kilómetros
            mode: Modo de transporte
            
        Returns:
            DistanceResult: Resultado con tiempo estimado
        """
        if mode not in self.average_speeds:
            mode = "driving"
        
        # Ajustar distancia para rutas reales (factor de corrección)
        if mode == "driving":
            adjusted_distance = distance_km * 1.3  # +30% para rutas reales
        elif mode == "walking":
            adjusted_distance = distance_km * 1.2  # +20% para rutas peatonales
        else:
            adjusted_distance = distance_km * 1.25
        
        # Calcular tiempo
        speed = self.average_speeds[mode]
        duration_hours = adjusted_distance / speed
        duration_minutes = int(duration_hours * 60)
        
        return DistanceResult(
            distance_km=adjusted_distance,
            duration_minutes=duration_minutes,
            route_type=f"estimated_{mode}"
        )
    
    async def _get_real_distance(
        self,
        origin: Coordenadas,
        destination: Coordenadas,
        mode: str
    ) -> Optional[DistanceResult]:
        """
        Obtiene distancia real usando API de mapas (Google Maps, etc.).
        
        Args:
            origin: Coordenadas de origen
            destination: Coordenadas de destino
            mode: Modo de transporte
            
        Returns:
            DistanceResult o None si falla la API
        """
        try:
            # Aquí iría la integración con Google Maps API u otra API
            # Por ahora retorna None para usar estimación
            
            # Ejemplo de implementación con Google Maps:
            # url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
            # params = {
            #     "origins": f"{origin.lat},{origin.lng}",
            #     "destinations": f"{destination.lat},{destination.lng}",
            #     "mode": mode,
            #     "key": self.maps_api_key
            # }
            # 
            # async with aiohttp.ClientSession() as session:
            #     async with session.get(url, params=params) as response:
            #         data = await response.json()
            #         # Procesar respuesta...
            
            return None
            
        except Exception as e:
            logger.warning(f"Error obteniendo distancia real: {str(e)}")
            return None
    
    async def calculate_route_distance(
        self,
        waypoints: List[Coordenadas],
        mode: str = "driving"
    ) -> DistanceResult:
        """
        Calcula la distancia total de una ruta con múltiples puntos.
        
        Args:
            waypoints: Lista de coordenadas en orden de visita
            mode: Modo de transporte
            
        Returns:
            DistanceResult: Distancia y tiempo total de la ruta
        """
        if len(waypoints) < 2:
            return DistanceResult(distance_km=0.0, duration_minutes=0)
        
        total_distance = 0.0
        total_duration = 0
        
        # Calcular distancia entre cada par de puntos consecutivos
        for i in range(len(waypoints) - 1):
            segment_result = await self.calculate_distance(
                waypoints[i], waypoints[i + 1], mode
            )
            
            total_distance += segment_result.distance_km
            if segment_result.duration_minutes:
                total_duration += segment_result.duration_minutes
        
        return DistanceResult(
            distance_km=round(total_distance, 2),
            duration_minutes=total_duration if total_duration > 0 else None,
            route_type=f"multi_point_{mode}"
        )
    
    def find_nearest_locations(
        self,
        reference_point: Coordenadas,
        locations: List[Tuple[str, Coordenadas]],
        max_results: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Encuentra las ubicaciones más cercanas a un punto de referencia.
        
        Args:
            reference_point: Punto de referencia
            locations: Lista de (nombre, coordenadas)
            max_results: Número máximo de resultados
            
        Returns:
            Lista de (nombre, distancia_km) ordenada por distancia
        """
        distances = []
        
        for name, coords in locations:
            distance = self._haversine_distance(reference_point, coords)
            distances.append((name, distance))
        
        # Ordenar por distancia y retornar los más cercanos
        distances.sort(key=lambda x: x[1])
        return distances[:max_results]
    
    def is_within_radius(
        self,
        center: Coordenadas,
        point: Coordenadas,
        radius_km: float
    ) -> bool:
        """
        Verifica si un punto está dentro de un radio específico.
        
        Args:
            center: Centro del círculo
            point: Punto a verificar
            radius_km: Radio en kilómetros
            
        Returns:
            bool: True si está dentro del radio
        """
        distance = self._haversine_distance(center, point)
        return distance <= radius_km
    
    def _generate_cache_key(
        self,
        origin: Coordenadas,
        destination: Coordenadas,
        mode: str
    ) -> str:
        """Genera clave única para cache de distancias"""
        # Redondear coordenadas para agrupar consultas similares
        origin_rounded = (round(origin.lat, 3), round(origin.lng, 3))
        dest_rounded = (round(destination.lat, 3), round(destination.lng, 3))
        
        return f"{origin_rounded}_{dest_rounded}_{mode}"
    
    def clear_cache(self):
        """Limpia el cache de distancias"""
        self.distance_cache.clear()
        logger.info("Cache de distancias limpiado")
    
    def get_cache_stats(self) -> Dict:
        """Obtiene estadísticas del cache"""
        return {
            "cache_size": len(self.distance_cache),
            "cache_keys": list(self.distance_cache.keys())[:10]  # Primeras 10
        }


# Funciones de utilidad adicionales

def degrees_to_radians(degrees: float) -> float:
    """Convierte grados a radianes"""
    return degrees * math.pi / 180


def radians_to_degrees(radians: float) -> float:
    """Convierte radianes a grados"""
    return radians * 180 / math.pi


def calculate_bearing(origin: Coordenadas, destination: Coordenadas) -> float:
    """
    Calcula el rumbo (bearing) desde origen a destino.
    
    Returns:
        float: Rumbo en grados (0-360)
    """
    lat1 = math.radians(origin.lat)
    lat2 = math.radians(destination.lat)
    diff_lng = math.radians(destination.lng - origin.lng)
    
    x = math.sin(diff_lng) * math.cos(lat2)
    y = (math.cos(lat1) * math.sin(lat2) - 
         math.sin(lat1) * math.cos(lat2) * math.cos(diff_lng))
    
    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing


def get_bounding_box(
    center: Coordenadas,
    radius_km: float
) -> Tuple[Coordenadas, Coordenadas]:
    """
    Calcula el bounding box (rectángulo) que contiene un círculo.
    
    Args:
        center: Centro del círculo
        radius_km: Radio en kilómetros
        
    Returns:
        Tuple[Coordenadas, Coordenadas]: (suroeste, noreste)
    """
    # Aproximación: 1 grado ≈ 111 km
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * math.cos(math.radians(center.lat)))
    
    southwest = Coordenadas(
        lat=center.lat - lat_delta,
        lng=center.lng - lng_delta
    )
    
    northeast = Coordenadas(
        lat=center.lat + lat_delta,
        lng=center.lng + lng_delta
    )
    
    return southwest, northeast

