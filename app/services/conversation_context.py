from __future__ import annotations
"""Servicio de contexto conversacional
=====================================

Este servicio permite mapear productos detectados por OCR con las
preferencias almacenadas del usuario.  También ajusta sugerencias de
marcas y precios según dichas preferencias y persiste las interacciones
para aprendizaje posterior.
"""

from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from app.models.conversation_context import UserContext, UserInteraction


class ConversationContextService:
    """Gestiona preferencias de usuario y registro de interacciones."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Preferencias
    # ------------------------------------------------------------------
    def get_preferences(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Obtiene las preferencias activas para un usuario."""
        context = (
            self.db.query(UserContext)
            .filter(UserContext.user_id == user_id, UserContext.is_active == True)
            .order_by(UserContext.created_at.desc())
            .first()
        )
        return context.preferencias if context and context.preferencias else {}

    def map_products_to_preferences(
        self, productos: List[str], preferencias: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Relaciona productos reconocidos con las preferencias del usuario."""
        mapeo: List[Dict[str, Any]] = []
        for prod in productos:
            prod_lower = prod.lower()
            coincidencias: Dict[str, Any] = {}
            for pref_key, pref_val in preferencias.items():
                if pref_key.lower() in prod_lower:
                    coincidencias[pref_key] = pref_val
            mapeo.append({"producto": prod, "preferencias": coincidencias})
        return mapeo

    # ------------------------------------------------------------------
    # Sugerencias
    # ------------------------------------------------------------------
    def adjust_suggestions(
        self, productos: List[Dict[str, Any]], preferencias: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Aplica preferencias de marca y precio sobre una lista de productos."""
        adjusted: List[Dict[str, Any]] = []
        lactose_free = preferencias.get("lacteos", {}).get("sin_lactosa")
        preferred_brands: Dict[str, str] = preferencias.get("marcas", {})
        max_price: Optional[float] = preferencias.get("precio_max")

        for prod in productos:
            nombre = (prod.get("nombre") or prod.get("producto") or "").lower()
            suggestion = prod.copy()

            # Preferencia por lácteos sin lactosa
            if lactose_free and any(t in nombre for t in ["leche", "yogurt", "queso", "mantequilla"]):
                if "sin lactosa" not in nombre and "lactose free" not in nombre:
                    suggestion["relevante"] = False
                    suggestion["motivo"] = "contiene_lactosa"

            # Marcas preferidas
            marca_pref = preferred_brands.get(nombre)
            if marca_pref:
                suggestion["marca_sugerida"] = marca_pref

            # Límite de precio
            if max_price is not None and suggestion.get("precio_mejor"):
                if suggestion["precio_mejor"] > max_price:
                    suggestion["relevante"] = False
                    suggestion["motivo"] = "sobre_precio_maximo"

            adjusted.append(suggestion)

        return adjusted

    # ------------------------------------------------------------------
    # Persistencia de interacciones
    # ------------------------------------------------------------------
    def save_interaction(
        self,
        user_id: uuid.UUID,
        productos: List[str],
        context_id: Optional[uuid.UUID] = None,
        intent: str = "ocr_scan",
        satisfaction: Optional[float] = None,
    ) -> UserInteraction:
        """Guarda una interacción asociada a los productos procesados."""
        interaction = UserInteraction(
            interaction_id=uuid.uuid4(),
            user_id=user_id,
            context_id=context_id,
            interaction_data={"productos": productos},
            intent=intent,
            satisfaction_score=satisfaction,
            products_count=len(productos),
        )
        self.db.add(interaction)
        self.db.commit()
        self.db.refresh(interaction)
        return interaction

    # ------------------------------------------------------------------
    # Flujo completo para OCR
    # ------------------------------------------------------------------
    def process_ocr_products(
        self, user_id: uuid.UUID, productos: List[str], context_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Pipeline completo tras el OCR de productos."""
        preferencias = self.get_preferences(user_id)
        mapeo = self.map_products_to_preferences(productos, preferencias)
        sugerencias = self.adjust_suggestions([{"producto": p} for p in productos], preferencias)
        self.save_interaction(user_id, productos, context_id)
        return {"mapeo": mapeo, "sugerencias": sugerencias}
