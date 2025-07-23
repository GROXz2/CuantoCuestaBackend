from app.core.database import SessionLocal
from app.models import Category, Product, Price
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import select
from uuid import uuid4

def run():
    db = SessionLocal()
    try:
        print("  Creando categorías...")
        existing = db.execute(select(Category).where(Category.name == "Lácteos")).scalar_one_or_none()
        if existing:
            categoria = existing
            print("  ⚠ Categoría 'Lácteos' ya existe, usando existente.")
        else:
            categoria = Category(id=uuid4(), name="Lácteos", slug="lacteos")
            db.add(categoria)
            db.commit()
            db.refresh(categoria)
            print("  ✓ Categoría creada")

        print("  Creando productos...")
        producto = Product(id=uuid4(), name="Leche entera", category_id=categoria.id)
        db.add(producto)
        db.commit()
        db.refresh(producto)
        print("  ✓ Producto creado")

        print("  Creando precios...")
        precio = Price(id=uuid4(), product_id=producto.id, store_id=1, price=1200)
        db.add(precio)
        db.commit()
        print("  ✓ Precio creado")

        print("\n✅ Datos insertados correctamente")

    except SQLAlchemyError as e:
        db.rollback()
        print(f"❌ Error insertando datos: {e}")
    finally:
        db.close()
