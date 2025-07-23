"""
Servicio de Gestión de Perfiles de Usuario
==========================================

Este servicio maneja la creación, actualización y gestión de perfiles de usuario
para personalizar la experiencia de optimización de compras.

Autor: Manus AI
Fecha: 2024
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json
import logging
from dataclasses import asdict

from ..models.user_profile import UserProfile, UserPreferences, ShoppingHistory
from ..models.optimization_result import ShoppingScenario
from ..schemas.user_profile import UserProfileCreate, UserProfileUpdate

logger = logging.getLogger(__name__)


class UserProfileService:
    """
    Servicio para gestionar perfiles de usuario temporales y persistentes.
    
    Funcionalidades:
    - Creación de perfiles temporales (sin registro)
    - Gestión de preferencias de optimización
    - Historial de compras y patrones
    - Aprendizaje adaptativo de preferencias
    - Limpieza automática de perfiles expirados
    """
    
    def __init__(self, database_session):
        self.db = database_session
        self.default_expiry_hours = 12  # Perfiles temporales expiran en 12 horas
        
    async def create_temporary_profile(
        self,
        initial_preferences: Optional[Dict] = None
    ) -> UserProfile:
        """
        Crea un perfil temporal para usuarios sin registro.
        
        Args:
            initial_preferences: Preferencias iniciales opcionales
            
        Returns:
            UserProfile: Perfil temporal creado
        """
        try:
            session_id = self._generate_session_id()
            
            # Crear preferencias por defecto
            preferences = UserPreferences()
            if initial_preferences:
                preferences = self._merge_preferences(preferences, initial_preferences)
            
            # Crear perfil temporal
            profile = UserProfile(
                session_id=session_id,
                is_temporary=True,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=self.default_expiry_hours),
                preferencias_optimizacion=preferences,
                historial_compras=[],
                productos_frecuentes={},
                ubicaciones_frecuentes=[]
            )
            
            # Guardar en base de datos
            await self._save_profile(profile)
            
            logger.info(f"Perfil temporal creado: {session_id}")
            return profile
            
        except Exception as e:
            logger.error(f"Error creando perfil temporal: {str(e)}")
            raise
    
    async def get_profile(self, session_id: str) -> Optional[UserProfile]:
        """
        Obtiene un perfil de usuario por session_id.
        
        Args:
            session_id: ID de sesión del usuario
            
        Returns:
            UserProfile o None si no existe o expiró
        """
        try:
            # Buscar perfil en base de datos
            profile_data = await self._fetch_profile_from_db(session_id)
            
            if not profile_data:
                return None
            
            # Verificar si el perfil ha expirado
            profile = self._deserialize_profile(profile_data)
            if self._is_profile_expired(profile):
                await self._delete_profile(session_id)
                return None
            
            return profile
            
        except Exception as e:
            logger.error(f"Error obteniendo perfil {session_id}: {str(e)}")
            return None
    
    async def update_preferences(
        self,
        session_id: str,
        new_preferences: Dict
    ) -> bool:
        """
        Actualiza las preferencias de un usuario.
        
        Args:
            session_id: ID de sesión del usuario
            new_preferences: Nuevas preferencias a aplicar
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            profile = await self.get_profile(session_id)
            if not profile:
                return False
            
            # Actualizar preferencias
            profile.preferencias_optimizacion = self._merge_preferences(
                profile.preferencias_optimizacion,
                new_preferences
            )
            
            # Marcar como actualizado
            profile.updated_at = datetime.utcnow()
            
            # Guardar cambios
            await self._save_profile(profile)
            
            logger.info(f"Preferencias actualizadas para {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando preferencias {session_id}: {str(e)}")
            return False
    
    async def update_shopping_history(
        self,
        session_id: str,
        productos: List[str],
        scenario_usado: Optional[ShoppingScenario] = None
    ) -> bool:
        """
        Actualiza el historial de compras del usuario.
        
        Args:
            session_id: ID de sesión del usuario
            productos: Lista de productos comprados
            scenario_usado: Escenario que el usuario eligió
            
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            profile = await self.get_profile(session_id)
            if not profile:
                return False
            
            # Crear entrada de historial
            historial_entry = ShoppingHistory(
                fecha=datetime.utcnow(),
                productos=productos,
                scenario_id=scenario_usado.id if scenario_usado else None,
                precio_total=scenario_usado.precio_total if scenario_usado else None,
                tiendas_visitadas=[t.nombre for t in scenario_usado.tiendas] if scenario_usado else []
            )
            
            # Agregar al historial
            profile.historial_compras.append(historial_entry)
            
            # Mantener solo los últimos 50 registros
            if len(profile.historial_compras) > 50:
                profile.historial_compras = profile.historial_compras[-50:]
            
            # Actualizar productos frecuentes
            self._update_frequent_products(profile, productos)
            
            # Aprender de patrones
            await self._learn_from_shopping_pattern(profile, scenario_usado)
            
            # Guardar cambios
            profile.updated_at = datetime.utcnow()
            await self._save_profile(profile)
            
            logger.info(f"Historial actualizado para {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando historial {session_id}: {str(e)}")
            return False
    
    async def get_shopping_recommendations(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Genera recomendaciones basadas en el historial del usuario.
        
        Args:
            session_id: ID de sesión del usuario
            
        Returns:
            Dict con recomendaciones personalizadas
        """
        try:
            profile = await self.get_profile(session_id)
            if not profile or not profile.historial_compras:
                return self._get_default_recommendations()
            
            recommendations = {
                "productos_sugeridos": self._get_suggested_products(profile),
                "supermercados_preferidos": self._get_preferred_supermarkets(profile),
                "horarios_optimos": self._get_optimal_times(profile),
                "patrones_detectados": self._detect_shopping_patterns(profile)
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones {session_id}: {str(e)}")
            return self._get_default_recommendations()
    
    async def cleanup_expired_profiles(self) -> int:
        """
        Limpia perfiles temporales expirados.
        
        Returns:
            int: Número de perfiles eliminados
        """
        try:
            expired_count = await self._delete_expired_profiles()
            logger.info(f"Limpieza completada: {expired_count} perfiles eliminados")
            return expired_count
            
        except Exception as e:
            logger.error(f"Error en limpieza de perfiles: {str(e)}")
            return 0
    
    def _generate_session_id(self) -> str:
        """Genera un ID único para la sesión"""
        return f"temp_{uuid.uuid4().hex[:12]}"
    
    def _merge_preferences(
        self,
        current_prefs: UserPreferences,
        new_prefs: Dict
    ) -> UserPreferences:
        """Combina preferencias actuales con nuevas preferencias"""
        # Convertir a dict, actualizar, y volver a crear objeto
        current_dict = asdict(current_prefs)
        current_dict.update(new_prefs)
        return UserPreferences(**current_dict)
    
    def _is_profile_expired(self, profile: UserProfile) -> bool:
        """Verifica si un perfil ha expirado"""
        if not profile.is_temporary:
            return False
        return datetime.utcnow() > profile.expires_at
    
    def _update_frequent_products(self, profile: UserProfile, productos: List[str]):
        """Actualiza la lista de productos frecuentes"""
        for producto in productos:
            if producto in profile.productos_frecuentes:
                profile.productos_frecuentes[producto] += 1
            else:
                profile.productos_frecuentes[producto] = 1
        
        # Mantener solo los top 20 productos más frecuentes
        sorted_products = sorted(
            profile.productos_frecuentes.items(),
            key=lambda x: x[1],
            reverse=True
        )
        profile.productos_frecuentes = dict(sorted_products[:20])
    
    async def _learn_from_shopping_pattern(
        self,
        profile: UserProfile,
        scenario_usado: Optional[ShoppingScenario]
    ):
        """
        Aprende de los patrones de compra para ajustar preferencias.
        
        Analiza qué tipo de escenarios elige el usuario para
        ajustar automáticamente sus preferencias de optimización.
        """
        if not scenario_usado or len(profile.historial_compras) < 3:
            return
        
        # Analizar últimas decisiones
        recent_scenarios = [
            h for h in profile.historial_compras[-10:]
            if h.scenario_id
        ]
        
        if len(recent_scenarios) < 3:
            return
        
        # Detectar patrones en las decisiones
        patterns = self._analyze_decision_patterns(recent_scenarios)
        
        # Ajustar preferencias basándose en patrones
        if patterns.get("prefers_single_store", False):
            profile.preferencias_optimizacion.max_supermercados = 1
        
        if patterns.get("price_sensitive", False):
            # Usuario consistentemente elige opciones más baratas
            profile.preferencias_optimizacion.peso_ahorro = min(
                profile.preferencias_optimizacion.peso_ahorro + 0.1, 0.8
            )
    
    def _analyze_decision_patterns(self, scenarios: List[ShoppingHistory]) -> Dict:
        """Analiza patrones en las decisiones del usuario"""
        patterns = {
            "prefers_single_store": False,
            "price_sensitive": False,
            "time_conscious": False
        }
        
        # Implementar lógica de análisis de patrones
        # Por ahora, retorna patrones vacíos
        
        return patterns
    
    def _get_suggested_products(self, profile: UserProfile) -> List[str]:
        """Sugiere productos basándose en el historial"""
        # Retornar productos más frecuentes
        return list(profile.productos_frecuentes.keys())[:10]
    
    def _get_preferred_supermarkets(self, profile: UserProfile) -> List[str]:
        """Identifica supermercados preferidos del usuario"""
        supermarket_counts = {}
        
        for historial in profile.historial_compras:
            for tienda in historial.tiendas_visitadas:
                supermarket_counts[tienda] = supermarket_counts.get(tienda, 0) + 1
        
        # Retornar top 3 supermercados
        sorted_supermarkets = sorted(
            supermarket_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [name for name, count in sorted_supermarkets[:3]]
    
    def _get_optimal_times(self, profile: UserProfile) -> Dict:
        """Identifica horarios óptimos de compra"""
        # Analizar horarios del historial
        # Por ahora retorna horarios por defecto
        return {
            "dias_preferidos": ["sabado", "domingo"],
            "horas_preferidas": ["10:00-12:00", "16:00-18:00"]
        }
    
    def _detect_shopping_patterns(self, profile: UserProfile) -> List[str]:
        """Detecta patrones en el comportamiento de compra"""
        patterns = []
        
        if len(profile.historial_compras) >= 5:
            patterns.append("Comprador regular")
        
        if profile.productos_frecuentes:
            patterns.append("Tiene productos favoritos")
        
        return patterns
    
    def _get_default_recommendations(self) -> Dict[str, Any]:
        """Retorna recomendaciones por defecto para usuarios nuevos"""
        return {
            "productos_sugeridos": [],
            "supermercados_preferidos": ["Jumbo", "Lider", "Tottus"],
            "horarios_optimos": {
                "dias_preferidos": ["sabado", "domingo"],
                "horas_preferidas": ["10:00-12:00"]
            },
            "patrones_detectados": ["Usuario nuevo"]
        }
    
    # Métodos de base de datos (implementación específica según DB)
    async def _save_profile(self, profile: UserProfile):
        """Guarda perfil en base de datos"""
        # Implementación específica según el ORM/DB usado
        pass
    
    async def _fetch_profile_from_db(self, session_id: str) -> Optional[Dict]:
        """Obtiene perfil de la base de datos"""
        # Implementación específica según el ORM/DB usado
        pass
    
    def _deserialize_profile(self, profile_data: Dict) -> UserProfile:
        """Convierte datos de DB a objeto UserProfile"""
        # Implementación específica según el formato de DB
        pass
    
    async def _delete_profile(self, session_id: str):
        """Elimina perfil de la base de datos"""
        # Implementación específica según el ORM/DB usado
        pass
    
    async def _delete_expired_profiles(self) -> int:
        """Elimina perfiles expirados de la base de datos"""
        # Implementación específica según el ORM/DB usado
        pass

