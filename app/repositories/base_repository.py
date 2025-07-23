"""
Repositorio base para operaciones CRUD comunes
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Repositorio base con operaciones CRUD comunes"""
    
    def __init__(self, model: Type[ModelType]):
        """
        Repositorio CRUD con modelo por defecto.
        
        **Parámetros**
        * `model`: Clase del modelo SQLAlchemy
        """
        self.model = model
    
    def get(self, db: Session, id: Union[UUID, str]) -> Optional[ModelType]:
        """Obtener registro por ID"""
        return db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Obtener múltiples registros con paginación y filtros"""
        query = db.query(self.model)
        
        # Aplicar filtros si se proporcionan
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Crear nuevo registro"""
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error de integridad al crear registro: {str(e)}")
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """Actualizar registro existente"""
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        try:
            db.commit()
            db.refresh(db_obj)
            return db_obj
        except IntegrityError as e:
            db.rollback()
            raise ValueError(f"Error de integridad al actualizar registro: {str(e)}")
    
    def remove(self, db: Session, *, id: Union[UUID, str]) -> Optional[ModelType]:
        """Eliminar registro por ID"""
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def count(self, db: Session, filters: Optional[Dict[str, Any]] = None) -> int:
        """Contar registros con filtros opcionales"""
        query = db.query(self.model)
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.count()
    
    def exists(self, db: Session, id: Union[UUID, str]) -> bool:
        """Verificar si existe un registro por ID"""
        return db.query(self.model).filter(self.model.id == id).first() is not None
    
    def get_active(self, db: Session, id: Union[UUID, str]) -> Optional[ModelType]:
        """Obtener registro activo por ID"""
        query = db.query(self.model).filter(self.model.id == id)
        
        # Verificar si el modelo tiene campo is_active
        if hasattr(self.model, 'is_active'):
            query = query.filter(self.model.is_active == True)
        
        return query.first()
    
    def get_multi_active(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """Obtener múltiples registros activos"""
        query = db.query(self.model)
        
        # Filtrar solo activos si el modelo tiene el campo
        if hasattr(self.model, 'is_active'):
            query = query.filter(self.model.is_active == True)
        
        # Aplicar filtros adicionales
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.offset(skip).limit(limit).all()

