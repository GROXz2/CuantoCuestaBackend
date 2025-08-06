"""
Configuración de base de datos para Cuanto Cuesta
Incluye soporte para el Conversation Service y gestión de contexto conversacional
"""
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager
import structlog
import asyncio
from typing import AsyncGenerator

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Configuración del engine de base de datos
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,  # Aumentado para conversation service
    max_overflow=30,  # Aumentado para conversation service
    connect_args={
        "client_encoding": "utf8",
        "application_name": "CuantoCuesta_ConversationService"
    }
)

# Configuración de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configuración de metadatos con esquemas
metadata = MetaData()

# Base para modelos
Base = declarative_base(metadata=metadata)


def get_db():
    """
    Dependency para obtener sesión de base de datos (FastAPI)
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        logger.exception("Error en sesión de base de datos")
        db.rollback()
        raise
    finally:
        db.close()


async def get_database_session() -> Session:
    """
    Obtener sesión de base de datos para el conversation service
    
    Returns:
        Session: Sesión de SQLAlchemy
    """
    db = SessionLocal()
    try:
        return db
    except Exception:
        logger.exception("Error creando sesión de base de datos")
        db.close()
        raise


@asynccontextmanager
async def get_async_db_session() -> AsyncGenerator[Session, None]:
    """
    Context manager para sesiones de base de datos asíncronas
    
    Yields:
        Session: Sesión de base de datos
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        logger.exception("Error en sesión asíncrona")
        db.rollback()
        raise
    finally:
        db.close()


def create_database():
    """
    Crear todas las tablas en la base de datos
    Incluye tablas del conversation service
    """
    try:
        # Importar todos los modelos para asegurar que estén registrados
        from app.models import (
            product, store, price, category, shopping_list, user, supermarket,
            conversation_context, contextual_anchor
        )
        
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas de base de datos creadas exitosamente")
        
        # Crear índices adicionales para conversation service
        create_conversation_indexes()
        
        # Crear funciones de base de datos para conversation service
        create_conversation_functions()
        
    except Exception:
        logger.exception("Error creando tablas")
        raise


def create_conversation_indexes():
    """
    Crear índices específicos para optimizar el conversation service
    """
    try:
        with engine.connect() as connection:
            # Índices compuestos para consultas frecuentes (con IF NOT EXISTS)
            indexes = [
                """
                CREATE INDEX IF NOT EXISTS idx_user_interactions_recent 
                ON user_interactions (user_id, timestamp DESC) 
                WHERE timestamp > NOW() - INTERVAL '30 days'
                """,
                
                """
                CREATE INDEX IF NOT EXISTS idx_contextual_anchors_active 
                ON contextual_anchors (user_id, is_active, confidence_score DESC) 
                WHERE is_active = true
                """,
                
                """
                CREATE INDEX IF NOT EXISTS idx_context_changes_recent 
                ON context_changes (user_id, detection_timestamp DESC) 
                WHERE detection_timestamp > NOW() - INTERVAL '7 days'
                """,
                
                """
                CREATE INDEX IF NOT EXISTS idx_anonymous_cache_region_fresh 
                ON anonymous_cache (region_code, created_at DESC) 
                WHERE expires_at > NOW()
                """,
                
                """
                CREATE INDEX IF NOT EXISTS idx_usuarios_active_temp 
                ON usuarios (is_temporary, last_activity DESC) 
                WHERE expires_at IS NULL OR expires_at > NOW()
                """
            ]
            
            for index_sql in indexes:
                try:
                    connection.execute(text(index_sql))
                except Exception as e:
                    if "already exists" in str(e) or "ya existe" in str(e):
                        logger.debug(f"Índice ya existe (normal): {e}")
                    else:
                        logger.exception("Error creando índice")
                
        logger.info("Índices del conversation service creados exitosamente")
        
    except Exception:
        logger.exception("Error creando índices del conversation service")


def create_conversation_functions():
    """
    Crear funciones de base de datos para optimizar el conversation service
    """
    try:
        with engine.connect() as connection:
            # Función para limpiar usuarios expirados
            cleanup_function = """
            CREATE OR REPLACE FUNCTION cleanup_expired_users()
            RETURNS INTEGER AS $$
            DECLARE
                deleted_count INTEGER;
            BEGIN
                DELETE FROM usuarios 
                WHERE is_temporary = true 
                AND expires_at < NOW();
                
                GET DIAGNOSTICS deleted_count = ROW_COUNT;
                RETURN deleted_count;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # Función para calcular drift score
            drift_function = """
            CREATE OR REPLACE FUNCTION calculate_anchor_drift_score(
                anchor_id UUID,
                new_value JSONB
            )
            RETURNS FLOAT AS $$
            DECLARE
                current_value JSONB;
                drift_score FLOAT;
            BEGIN
                SELECT anchor_value INTO current_value 
                FROM contextual_anchors 
                WHERE contextual_anchors.anchor_id = calculate_anchor_drift_score.anchor_id;
                
                IF current_value IS NULL THEN
                    RETURN 0.0;
                END IF;
                
                -- Cálculo simplificado de drift (puede expandirse)
                IF current_value = new_value THEN
                    drift_score := 0.0;
                ELSE
                    drift_score := 1.0;
                END IF;
                
                RETURN drift_score;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            # Función para obtener estadísticas de usuario
            stats_function = """
            CREATE OR REPLACE FUNCTION get_user_interaction_stats(
                user_id_param UUID,
                days_back INTEGER DEFAULT 30
            )
            RETURNS TABLE(
                total_interactions BIGINT,
                avg_satisfaction FLOAT,
                most_common_intent TEXT,
                interaction_frequency FLOAT
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    COUNT(*) as total_interactions,
                    AVG(CAST(ui.satisfaction_score AS FLOAT)) as avg_satisfaction,
                    MODE() WITHIN GROUP (ORDER BY ui.intent) as most_common_intent,
                    COUNT(*)::FLOAT / GREATEST(days_back, 1) as interaction_frequency
                FROM user_interactions ui
                WHERE ui.user_id = user_id_param
                AND ui.timestamp > NOW() - (days_back || ' days')::INTERVAL;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            functions = [cleanup_function, drift_function, stats_function]
            
            for function_sql in functions:
                connection.execute(text(function_sql))
                
        logger.info("Funciones del conversation service creadas exitosamente")
        
    except Exception:
        logger.exception("Error creando funciones del conversation service")


def check_database_connection():
    """
    Verificar conexión a la base de datos
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Conexión a base de datos exitosa")
        return True
    except Exception:
        logger.exception("Error conectando a base de datos")
        return False


def check_conversation_tables():
    """
    Verificar que las tablas del conversation service existan
    
    Returns:
        bool: True si todas las tablas existen
    """
    required_tables = [
        'usuarios', 'user_context', 'user_interactions', 
        'contextual_anchors', 'anonymous_cache', 'context_changes'
    ]
    
    try:
        with engine.connect() as connection:
            for table in required_tables:
                result = connection.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
                ), {"table_name": table})
                
                if not result.scalar():
                    logger.exception("Tabla requerida no existe", table=table)
                    return False
                    
        logger.info("Todas las tablas del conversation service están presentes")
        return True
        
    except Exception:
        logger.exception("Error verificando tablas del conversation service")
        return False


def initialize_conversation_service_db():
    """
    Inicializar completamente la base de datos para el conversation service
    """
    try:
        logger.info("Inicializando base de datos del conversation service...")
        
        # Verificar conexión
        if not check_database_connection():
            raise Exception("No se puede conectar a la base de datos")
        
        # Crear tablas
        create_database()
        
        # Verificar que las tablas se crearon
        if not check_conversation_tables():
            raise Exception("Las tablas del conversation service no se crearon correctamente")
        
        logger.info("Base de datos del conversation service inicializada exitosamente")
        return True
        
    except Exception:
        logger.exception("Error inicializando base de datos del conversation service")
        raise


# Funciones de limpieza y mantenimiento

def cleanup_expired_data():
    """
    Limpiar datos expirados del conversation service
    """
    try:
        with engine.connect() as connection:
            # Limpiar usuarios expirados
            result = connection.execute(text("SELECT cleanup_expired_users()"))
            deleted_users = result.scalar()
            
            # Limpiar cache expirado
            connection.execute(text(
                "DELETE FROM anonymous_cache WHERE expires_at < NOW()"
            ))
            
            # Limpiar interacciones muy antiguas de usuarios temporales
            connection.execute(text("""
                DELETE FROM user_interactions 
                WHERE user_id IN (
                    SELECT user_id FROM usuarios 
                    WHERE is_temporary = true 
                    AND last_activity < NOW() - INTERVAL '90 days'
                )
                AND timestamp < NOW() - INTERVAL '90 days'
            """))
            
            connection.commit()
            
        logger.info(f"Limpieza completada: {deleted_users} usuarios expirados eliminados")
        
    except Exception:
        logger.exception("Error en limpieza de datos")


def get_database_stats():
    """
    Obtener estadísticas de la base de datos del conversation service
    
    Returns:
        dict: Estadísticas de uso
    """
    try:
        with engine.connect() as connection:
            stats = {}
            
            # Contar registros por tabla
            tables = ['usuarios', 'user_context', 'user_interactions', 
                     'contextual_anchors', 'anonymous_cache', 'context_changes']
            
            for table in tables:
                result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                stats[f"{table}_count"] = result.scalar()
            
            # Estadísticas adicionales
            result = connection.execute(text("""
                SELECT 
                    COUNT(*) FILTER (WHERE is_temporary = true) as temp_users,
                    COUNT(*) FILTER (WHERE is_temporary = false) as persistent_users,
                    COUNT(*) FILTER (WHERE expires_at < NOW()) as expired_users
                FROM usuarios
            """))
            
            row = result.fetchone()
            stats.update({
                "temporary_users": row[0],
                "persistent_users": row[1], 
                "expired_users": row[2]
            })
            
            return stats
            
    except Exception:
        logger.exception("Error obteniendo estadísticas")
        return {}

