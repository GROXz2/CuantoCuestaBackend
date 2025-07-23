"""
Endpoints para el Conversation Service
=====================================

Endpoints para gestionar el contexto conversacional y superar las limitaciones
de memoria de ChatGPT mediante el sistema de Weighted Moving Average con 
Contextual Anchors.
"""

from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import logging
import time

from app.schemas.conversation import (
    ConversationRequest,
    ConversationResponse,
    ContextSummaryResponse,
    DriftDetectionResponse,
    UserProfileRequest,
    UserProfileResponse
)
from app.services.conversation_service import ConversationService
from app.core.database import get_database_session

# Configurar logging
logger = logging.getLogger(__name__)

# Router para endpoints de conversación
router = APIRouter(prefix="/conversacion", tags=["Conversación"])

# Instancia del servicio de conversación
conversation_service = None


async def get_conversation_service():
    """Dependency para obtener el servicio de conversación"""
    global conversation_service
    if conversation_service is None:
        db_session = await get_database_session()
        conversation_service = ConversationService(db_session)
    return conversation_service


@router.post("/procesar", response_model=ConversationResponse)
async def procesar_interaccion(
    request: ConversationRequest,
    background_tasks: BackgroundTasks,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Procesar una nueva interacción del usuario y mantener contexto conversacional.
    
    Este endpoint es el núcleo del sistema de gestión de contexto. Recibe una
    interacción del usuario, la procesa usando el sistema de Weighted Moving Average
    con Contextual Anchors, detecta posibles cambios de contexto (drift) y
    retorna recomendaciones contextualizadas.
    
    Args:
        request: Datos de la interacción del usuario
        background_tasks: Tareas en segundo plano para optimización
        service: Servicio de conversación inyectado
        
    Returns:
        ConversationResponse: Respuesta con contexto actualizado y recomendaciones
        
    Raises:
        HTTPException: Si hay errores en el procesamiento
    """
    try:
        start_time = time.time()
        
        logger.info(f"Procesando interacción para usuario: {request.user_id}")
        
        # Procesar la interacción usando el conversation service
        result = await service.process_user_interaction(
            user_id=request.user_id,
            interaction_data=request.interaction_data,
            session_metadata=request.session_metadata
        )
        
        # Calcular tiempo de procesamiento
        processing_time = time.time() - start_time
        
        # Agregar tareas en segundo plano si es necesario
        if result.get("requires_background_processing"):
            background_tasks.add_task(
                _process_background_tasks,
                user_id=request.user_id,
                interaction_id=result.get("interaction_id")
            )
        
        # Preparar respuesta
        response = ConversationResponse(
            success=True,
            context_summary=result["context_summary"],
            recommendations=result["recommendations"],
            drift_info=result["drift_info"],
            conversation_guidance=result.get("conversation_guidance", {}),
            processing_time_ms=round(processing_time * 1000, 2),
            timestamp=time.time()
        )
        
        logger.info(
            f"Interacción procesada exitosamente en {processing_time:.3f}s "
            f"para usuario {request.user_id}"
        )
        
        return response
        
    except ValueError as e:
        logger.warning(f"Error de validación en interacción: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Datos de interacción inválidos: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error procesando interacción: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno procesando la interacción"
        )


@router.get("/contexto/{user_id}", response_model=ContextSummaryResponse)
async def obtener_contexto_usuario(
    user_id: str,
    include_history: bool = False,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Obtener resumen del contexto actual de un usuario.
    
    Retorna un resumen del perfil contextual del usuario, incluyendo anclas
    contextuales, nivel de confianza del perfil, y opcionalmente el historial
    de interacciones recientes.
    
    Args:
        user_id: Identificador único del usuario
        include_history: Si incluir historial de interacciones
        service: Servicio de conversación inyectado
        
    Returns:
        ContextSummaryResponse: Resumen del contexto del usuario
        
    Raises:
        HTTPException: Si el usuario no existe o hay errores
    """
    try:
        logger.info(f"Obteniendo contexto para usuario: {user_id}")
        
        # Obtener contexto del usuario
        context_summary = await service.get_user_context_summary(
            user_id=user_id,
            include_history=include_history
        )
        
        if not context_summary:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario {user_id} no encontrado"
            )
        
        response = ContextSummaryResponse(
            success=True,
            user_id=user_id,
            context_summary=context_summary,
            timestamp=time.time()
        )
        
        logger.info(f"Contexto obtenido exitosamente para usuario {user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo contexto: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno obteniendo contexto"
        )


@router.post("/perfil", response_model=UserProfileResponse)
async def crear_actualizar_perfil(
    request: UserProfileRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Crear o actualizar el perfil de un usuario.
    
    Permite crear un nuevo perfil de usuario o actualizar uno existente
    con nuevas preferencias, ubicaciones o configuraciones.
    
    Args:
        request: Datos del perfil del usuario
        service: Servicio de conversación inyectado
        
    Returns:
        UserProfileResponse: Confirmación y datos del perfil actualizado
        
    Raises:
        HTTPException: Si hay errores en la actualización
    """
    try:
        logger.info(f"Actualizando perfil para usuario: {request.user_id}")
        
        # Crear o actualizar perfil
        profile_result = await service.create_or_update_user_profile(
            user_id=request.user_id,
            profile_data=request.profile_data,
            is_temporary=request.is_temporary
        )
        
        response = UserProfileResponse(
            success=True,
            user_id=request.user_id,
            profile_data=profile_result["profile_data"],
            profile_strength=profile_result["profile_strength"],
            created_at=profile_result["created_at"],
            updated_at=profile_result["updated_at"],
            timestamp=time.time()
        )
        
        logger.info(f"Perfil actualizado exitosamente para usuario {request.user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error actualizando perfil: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno actualizando perfil"
        )


@router.get("/drift/{user_id}", response_model=DriftDetectionResponse)
async def analizar_drift_contexto(
    user_id: str,
    days_back: int = 30,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Analizar cambios de contexto (drift) para un usuario.
    
    Ejecuta análisis de drift contextual para detectar cambios significativos
    en el comportamiento o contexto del usuario en el período especificado.
    
    Args:
        user_id: Identificador único del usuario
        days_back: Días hacia atrás para el análisis
        service: Servicio de conversación inyectado
        
    Returns:
        DriftDetectionResponse: Análisis de drift detectado
        
    Raises:
        HTTPException: Si hay errores en el análisis
    """
    try:
        logger.info(f"Analizando drift para usuario: {user_id}")
        
        # Ejecutar análisis de drift
        drift_analysis = await service.analyze_context_drift(
            user_id=user_id,
            days_back=days_back
        )
        
        response = DriftDetectionResponse(
            success=True,
            user_id=user_id,
            drift_detected=drift_analysis["drift_detected"],
            drift_type=drift_analysis.get("drift_type"),
            confidence_score=drift_analysis["confidence_score"],
            affected_anchors=drift_analysis["affected_anchors"],
            detection_details=drift_analysis["detection_details"],
            recommended_actions=drift_analysis["recommended_actions"],
            analysis_period_days=days_back,
            timestamp=time.time()
        )
        
        logger.info(
            f"Análisis de drift completado para usuario {user_id}: "
            f"drift_detected={drift_analysis['drift_detected']}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error analizando drift: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno analizando drift"
        )


@router.delete("/usuario/{user_id}")
async def eliminar_datos_usuario(
    user_id: str,
    confirm: bool = False,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Eliminar todos los datos de un usuario (GDPR compliance).
    
    Elimina completamente todos los datos asociados a un usuario,
    incluyendo perfil, contexto, historial e interacciones.
    
    Args:
        user_id: Identificador único del usuario
        confirm: Confirmación explícita de eliminación
        service: Servicio de conversación inyectado
        
    Returns:
        JSONResponse: Confirmación de eliminación
        
    Raises:
        HTTPException: Si no se confirma o hay errores
    """
    try:
        if not confirm:
            raise HTTPException(
                status_code=400,
                detail="Debe confirmar la eliminación con confirm=true"
            )
        
        logger.warning(f"Eliminando datos de usuario: {user_id}")
        
        # Eliminar todos los datos del usuario
        deletion_result = await service.delete_user_data(user_id=user_id)
        
        logger.warning(
            f"Datos eliminados para usuario {user_id}: "
            f"{deletion_result['deleted_records']} registros"
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Datos del usuario {user_id} eliminados completamente",
                "deleted_records": deletion_result["deleted_records"],
                "timestamp": time.time()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando datos de usuario: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno eliminando datos"
        )


@router.get("/estadisticas")
async def obtener_estadisticas_sistema(
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Obtener estadísticas generales del sistema de conversación.
    
    Retorna métricas agregadas y anonimizadas sobre el uso del sistema,
    calidad de perfiles, efectividad de detección de drift, etc.
    
    Returns:
        Dict: Estadísticas del sistema
    """
    try:
        logger.info("Obteniendo estadísticas del sistema")
        
        # Obtener estadísticas del servicio
        stats = await service.get_system_statistics()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "statistics": stats,
                "timestamp": time.time()
            }
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno obteniendo estadísticas"
        )


# Funciones auxiliares

async def _process_background_tasks(user_id: str, interaction_id: str):
    """
    Procesar tareas en segundo plano para optimización.
    
    Args:
        user_id: ID del usuario
        interaction_id: ID de la interacción
    """
    try:
        logger.info(f"Procesando tareas en segundo plano para {user_id}")
        
        # Aquí se pueden agregar tareas como:
        # - Análisis predictivo de próximas necesidades
        # - Optimización de cache
        # - Análisis de patrones agregados
        # - Limpieza de datos antiguos
        
        # Por ahora, solo log
        logger.info(f"Tareas en segundo plano completadas para {user_id}")
        
    except Exception as e:
        logger.error(f"Error en tareas en segundo plano: {e}", exc_info=True)


# Incluir el router en el módulo
__all__ = ["router"]

