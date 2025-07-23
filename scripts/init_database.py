"""
Script de inicialización de base de datos con datos de prueba para Chile
VERSIÓN CORREGIDA - Maneja duplicados correctamente
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.category import Category
from app.models.product import Product
from app.models.supermarket import Supermarket
from app.models.store import Store
from app.models.price import Price
from app.models.user import User
from app.models.shopping_list import ShoppingList, ShoppingListItem
import uuid
from datetime import datetime, timedelta
import random

def create_extensions():
    """Crear extensiones necesarias de PostgreSQL"""
    print("Creando extensiones de PostgreSQL...")
    
    with engine.connect() as conn:
        # Extensión para UUID
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))
        
        # Extensión para búsqueda de texto
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        
        # Extensión para normalización de texto (quitar acentos)
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
        
        # Extensión PostGIS para geolocalización
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            print("✓ PostGIS instalado correctamente")
        except Exception as e:
            print(f"⚠ PostGIS no disponible: {e}")
            print("  Continuando sin funcionalidades geográficas avanzadas")
        
        conn.commit()
    
    print("✓ Extensiones creadas")

def create_search_functions():
    """Crear funciones personalizadas para búsqueda"""
    print("Creando funciones de búsqueda...")
    
    with engine.connect() as conn:
        # Función para normalizar texto (quitar acentos y convertir a minúsculas)
        normalize_function = """
        CREATE OR REPLACE FUNCTION normalize_text(input_text TEXT)
        RETURNS TEXT AS $$
        BEGIN
            RETURN lower(unaccent(input_text));
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
        """
        
        # Función para calcular distancia entre dos puntos
        distance_function = """
        CREATE OR REPLACE FUNCTION calculate_distance_km(
            lat1 DOUBLE PRECISION, 
            lon1 DOUBLE PRECISION, 
            lat2 DOUBLE PRECISION, 
            lon2 DOUBLE PRECISION
        )
        RETURNS DOUBLE PRECISION AS $$
        BEGIN
            -- Fórmula de Haversine para calcular distancia
            RETURN (
                6371 * acos(
                    cos(radians(lat1)) * 
                    cos(radians(lat2)) * 
                    cos(radians(lon2) - radians(lon1)) + 
                    sin(radians(lat1)) * 
                    sin(radians(lat2))
                )
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;
        """
        
        conn.execute(text(normalize_function))
        conn.execute(text(distance_function))
        conn.commit()
    
    print("✓ Funciones de búsqueda creadas")

def clear_existing_data():
    """Limpiar datos existentes (OPCIONAL - usar con cuidado)"""
    print("🧹 Limpiando datos existentes...")
    
    db = SessionLocal()
    try:
        # Eliminar en orden correcto (respetando foreign keys)
        db.query(Price).delete()
        db.query(ShoppingListItem).delete()
        db.query(ShoppingList).delete()
        db.query(Product).delete()
        db.query(Store).delete()
        db.query(Supermarket).delete()
        db.query(Category).delete()
        db.query(User).delete()
        
        db.commit()
        print("✓ Datos existentes eliminados")
    except Exception as e:
        print(f"⚠ Error limpiando datos: {e}")
        db.rollback()
    finally:
        db.close()

def insert_sample_data():
    """Insertar datos de prueba realistas para Chile"""
    print("Insertando datos de prueba...")
    
    db = SessionLocal()
    
    try:
        # 1. Crear categorías (con verificación de duplicados)
        print("  Creando categorías...")
        categories_data = [
            {"name": "Panadería", "slug": "panaderia", "description": "Pan, pasteles y productos de panadería"},
            {"name": "Lácteos", "slug": "lacteos", "description": "Leche, quesos, yogurt y derivados lácteos"},
            {"name": "Carnes", "slug": "carnes", "description": "Carnes rojas, pollo, pescado y mariscos"},
            {"name": "Frutas y Verduras", "slug": "frutas-verduras", "description": "Frutas y verduras frescas"},
            {"name": "Bebidas", "slug": "bebidas", "description": "Bebidas alcohólicas y no alcohólicas"},
            {"name": "Limpieza", "slug": "limpieza", "description": "Productos de limpieza y aseo"},
            {"name": "Higiene Personal", "slug": "higiene", "description": "Productos de higiene y cuidado personal"},
            {"name": "Congelados", "slug": "congelados", "description": "Productos congelados y helados"}
        ]
        
        category_objects = []
        for cat_data in categories_data:
            # Verificar si la categoría ya existe
            existing_category = db.query(Category).filter(Category.slug == cat_data["slug"]).first()
            
            if existing_category:
                print(f"    ⚠ Categoría '{cat_data['name']}' ya existe, omitiendo...")
                category_objects.append(existing_category)
            else:
                category = Category(
                    id=uuid.uuid4(),
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"]
                )
                db.add(category)
                category_objects.append(category)
                print(f"    ✓ Creada categoría '{cat_data['name']}'")
        
        db.commit()
        
        # 2. Crear supermercados (con verificación de duplicados)
        print("  Creando supermercados...")
        supermarkets_data = [
            {
                "name": "Jumbo", "slug": "jumbo", "type": "retail",
                "logo_url": "https://jumbo.cl/logo.png",
                "website_url": "https://jumbo.cl",
                "minimum_purchase_amount": 0
            },
            {
                "name": "Lider", "slug": "lider", "type": "retail", 
                "logo_url": "https://lider.cl/logo.png",
                "website_url": "https://lider.cl",
                "minimum_purchase_amount": 0
            },
            {
                "name": "Santa Isabel", "slug": "santa-isabel", "type": "retail",
                "logo_url": "https://santaisabel.cl/logo.png", 
                "website_url": "https://santaisabel.cl",
                "minimum_purchase_amount": 0
            },
            {
                "name": "Tottus", "slug": "tottus", "type": "retail",
                "logo_url": "https://tottus.cl/logo.png",
                "website_url": "https://tottus.cl", 
                "minimum_purchase_amount": 0
            },
            {
                "name": "Mayorista 10", "slug": "mayorista-10", "type": "mayorista",
                "logo_url": "https://mayorista10.cl/logo.png",
                "website_url": "https://mayorista10.cl",
                "minimum_purchase_amount": 30000
            }
        ]
        
        supermarket_objects = []
        for super_data in supermarkets_data:
            # Verificar si el supermercado ya existe
            existing_supermarket = db.query(Supermarket).filter(Supermarket.slug == super_data["slug"]).first()
            
            if existing_supermarket:
                print(f"    ⚠ Supermercado '{super_data['name']}' ya existe, omitiendo...")
                supermarket_objects.append(existing_supermarket)
            else:
                supermarket = Supermarket(
                    id=uuid.uuid4(),
                    name=super_data["name"],
                    slug=super_data["slug"],
                    type=super_data["type"],
                    logo_url=super_data["logo_url"],
                    website_url=super_data["website_url"],
                    minimum_purchase_amount=super_data["minimum_purchase_amount"],
                    delivery_available=True,
                    pickup_available=True
                )
                db.add(supermarket)
                supermarket_objects.append(supermarket)
                print(f"    ✓ Creado supermercado '{super_data['name']}'")
        
        db.commit()
        
        # 3. Crear tiendas en comunas chilenas (con verificación de duplicados)
        print("  Creando tiendas...")
        
        # Comunas de Santiago con coordenadas reales
        comunas_santiago = [
            {"name": "Ñuñoa", "lat": -33.4569, "lon": -70.5977},
            {"name": "Peñalolén", "lat": -33.4889, "lon": -70.5394}, 
            {"name": "Las Condes", "lat": -33.4172, "lon": -70.5476},
            {"name": "Providencia", "lat": -33.4372, "lon": -70.6178},
            {"name": "Santiago Centro", "lat": -33.4489, "lon": -70.6693},
            {"name": "Maipú", "lat": -33.5110, "lon": -70.7580},
            {"name": "La Florida", "lat": -33.5219, "lon": -70.5989},
            {"name": "Puente Alto", "lat": -33.6110, "lon": -70.5756},
            {"name": "San Miguel", "lat": -33.4967, "lon": -70.6578},
            {"name": "Estación Central", "lat": -33.4597, "lon": -70.6789}
        ]
        
        store_objects = []
        stores_created = 0
        stores_skipped = 0
        
        for supermarket in supermarket_objects:
            for comuna in comunas_santiago:
                # Crear 1-2 tiendas por supermercado por comuna
                num_stores = random.randint(1, 2)
                for i in range(num_stores):
                    # Variar ligeramente las coordenadas
                    lat_variation = random.uniform(-0.01, 0.01)
                    lon_variation = random.uniform(-0.01, 0.01)
                    
                    store_name = f"{supermarket.name} {comuna['name']}"
                    if num_stores > 1:
                        store_name += f" {i+1}"
                    
                    # Verificar si la tienda ya existe
                    existing_store = db.query(Store).filter(Store.name == store_name).first()
                    
                    if existing_store:
                        stores_skipped += 1
                        store_objects.append(existing_store)
                        continue
                    
                    # Direcciones realistas
                    direcciones = [
                        f"Av. Irarrázaval {random.randint(1000, 9999)}",
                        f"Av. Providencia {random.randint(1000, 3000)}",
                        f"Av. Las Condes {random.randint(10000, 15000)}",
                        f"Av. Vicuña Mackenna {random.randint(5000, 8000)}",
                        f"Av. Grecia {random.randint(1000, 5000)}"
                    ]
                    
                    store = Store(
                        id=uuid.uuid4(),
                        supermarket_id=supermarket.id,
                        name=store_name,
                        address=random.choice(direcciones),
                        commune=comuna["name"],
                        region="Región Metropolitana",
                        phone=f"+56 2 {random.randint(2000, 2999)} {random.randint(1000, 9999)}",
                        email=f"{supermarket.slug}.{comuna['name'].lower().replace(' ', '').replace('ñ', 'n')}@{supermarket.slug}.cl",
                        coordinates=f"POINT({comuna['lon'] + lon_variation} {comuna['lat'] + lat_variation})",
                        opening_hours={
                            "lunes": "08:00-22:00",
                            "martes": "08:00-22:00", 
                            "miercoles": "08:00-22:00",
                            "jueves": "08:00-22:00",
                            "viernes": "08:00-22:00",
                            "sabado": "08:00-22:00",
                            "domingo": "09:00-21:00"
                        },
                        has_pharmacy=random.choice([True, False]),
                        has_bakery=random.choice([True, False]),
                        has_parking=random.choice([True, False]),
                        services=random.sample(
                            ["cajero_automatico", "foto_copiado", "envio_dinero", "optica"], 
                            random.randint(0, 2)
                        )
                    )
                    db.add(store)
                    store_objects.append(store)
                    stores_created += 1
        
        db.commit()
        print(f"    ✓ Tiendas: {stores_created} creadas, {stores_skipped} ya existían")
        
        # 4. Crear productos realistas chilenos (con verificación de duplicados)
        print("  Creando productos...")
        
        productos_por_categoria = {
            "Panadería": [
                {"name": "Pan Integral", "brands": ["Bimbo", "Ideal", "Castaño"], "unit_type": "unidad", "unit_size": "500g"},
                {"name": "Pan de Molde", "brands": ["Bimbo", "Ideal"], "unit_type": "unidad", "unit_size": "650g"},
                {"name": "Hallulla", "brands": ["Castaño", "Ideal"], "unit_type": "unidad", "unit_size": "100g"},
                {"name": "Marraqueta", "brands": ["Castaño", "Ideal"], "unit_type": "unidad", "unit_size": "120g"}
            ],
            "Lácteos": [
                {"name": "Leche Entera", "brands": ["Soprole", "Colun", "Loncoleche"], "unit_type": "litro", "unit_size": "1L"},
                {"name": "Yogurt Natural", "brands": ["Soprole", "Danone", "Quillayes"], "unit_type": "unidad", "unit_size": "150g"},
                {"name": "Queso Gauda", "brands": ["Soprole", "Colun"], "unit_type": "kg", "unit_size": "200g"},
                {"name": "Mantequilla", "brands": ["Soprole", "Colun"], "unit_type": "unidad", "unit_size": "250g"}
            ],
            "Bebidas": [
                {"name": "Coca Cola", "brands": ["Coca Cola"], "unit_type": "litro", "unit_size": "1.5L"},
                {"name": "Agua Mineral", "brands": ["Cachantun", "Benedictino"], "unit_type": "litro", "unit_size": "1.5L"},
                {"name": "Cerveza", "brands": ["Cristal", "Escudo", "Heineken"], "unit_type": "unidad", "unit_size": "330ml"},
                {"name": "Jugo de Naranja", "brands": ["Watts", "Andina"], "unit_type": "litro", "unit_size": "1L"}
            ]
        }
        
        product_objects = []
        products_created = 0
        products_skipped = 0
        
        for category in category_objects:
            if category.name in productos_por_categoria:
                for product_data in productos_por_categoria[category.name]:
                    for brand in product_data["brands"]:
                        # Verificar si el producto ya existe
                        existing_product = db.query(Product).filter(
                            Product.name == product_data["name"],
                            Product.brand == brand
                        ).first()
                        
                        if existing_product:
                            products_skipped += 1
                            product_objects.append(existing_product)
                            continue
                        
                        product = Product(
                            id=uuid.uuid4(),
                            name=product_data["name"],
                            brand=brand,
                            category_id=category.id,
                            barcode=f"780{random.randint(1000000, 9999999)}",
                            description=f"{brand} {product_data['name']} {product_data['unit_size']}",
                            unit_type=product_data["unit_type"],
                            unit_size=product_data["unit_size"],
                            image_url=f"https://images.cuantocuesta.cl/{brand.lower()}-{product_data['name'].lower().replace(' ', '-')}.jpg"
                        )
                        db.add(product)
                        product_objects.append(product)
                        products_created += 1
        
        db.commit()
        print(f"    ✓ Productos: {products_created} creados, {products_skipped} ya existían")
        
        # 5. Crear precios realistas (con verificación de duplicados)
        print("  Creando precios...")
        
        prices_created = 0
        prices_skipped = 0
        
        for product in product_objects:
            # Precio base según categoría
            base_prices = {
                "Panadería": (800, 2000),
                "Lácteos": (1000, 3000), 
                "Bebidas": (500, 2500),
                "Carnes": (3000, 8000),
                "Frutas y Verduras": (500, 3000)
            }
            
            category_name = next(c.name for c in category_objects if c.id == product.category_id)
            price_range = base_prices.get(category_name, (1000, 3000))
            base_price = random.randint(price_range[0], price_range[1])
            
            # Crear precios en diferentes tiendas
            selected_stores = random.sample(store_objects, min(random.randint(3, 8), len(store_objects)))
            
            for store in selected_stores:
                # Verificar si el precio ya existe
                existing_price = db.query(Price).filter(
                    Price.product_id == product.id,
                    Price.store_id == store.id
                ).first()
                
                if existing_price:
                    prices_skipped += 1
                    continue
                
                # Variación de precio por tienda
                price_variation = random.uniform(0.85, 1.15)
                normal_price = int(base_price * price_variation)
                
                # 30% de probabilidad de descuento
                discount_price = None
                discount_percentage = None
                promotion_description = None
                
                if random.random() < 0.3:
                    discount_percentage = random.randint(10, 40)
                    discount_price = int(normal_price * (1 - discount_percentage / 100))
                    promotion_description = f"{discount_percentage}% de descuento"
                
                price = Price(
                    id=uuid.uuid4(),
                    product_id=product.id,
                    store_id=store.id,
                    normal_price=normal_price,
                    discount_price=discount_price,
                    discount_percentage=discount_percentage,
                    stock_status=random.choice(["available", "available", "available", "low_stock"]),
                    promotion_description=promotion_description,
                    scraped_at=datetime.now() - timedelta(hours=random.randint(0, 24))
                )
                db.add(price)
                prices_created += 1
        
        db.commit()
        print(f"    ✓ Precios: {prices_created} creados, {prices_skipped} ya existían")
        
        print("✓ Datos de prueba insertados correctamente")
        
        # Mostrar estadísticas
        print("\n📊 Estadísticas de datos:")
        print(f"  • Categorías: {db.query(Category).count()}")
        print(f"  • Supermercados: {db.query(Supermarket).count()}")
        print(f"  • Tiendas: {db.query(Store).count()}")
        print(f"  • Productos: {db.query(Product).count()}")
        print(f"  • Precios: {db.query(Price).count()}")
        
        # Mostrar ejemplos de búsqueda de Ñuñoa
        print("\n🔍 Prueba de búsqueda de caracteres especiales:")
        stores_nunoa = db.query(Store).filter(Store.commune.ilike("%ñuñoa%")).all()
        print(f"  • Tiendas en Ñuñoa: {len(stores_nunoa)}")
        if stores_nunoa:
            print(f"    Ejemplo: {stores_nunoa[0].name} - {stores_nunoa[0].address}")
        
    except Exception as e:
        print(f"❌ Error insertando datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def create_indexes():
    """Crear índices para optimizar búsquedas"""
    print("Creando índices de optimización...")
    
    with engine.connect() as conn:
        # Índices para búsqueda de texto
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_products_search 
            ON products (name, brand, description);
        """))
        
        # Índices para búsqueda normalizada de comunas
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_stores_commune 
            ON stores (commune);
        """))
        
        # Índices para precios
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prices_product_store 
            ON prices(product_id, store_id);
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_prices_scraped_at 
            ON prices(scraped_at DESC);
        """))
        
        conn.commit()
    
    print("✓ Índices creados")

def main():
    from app.core.database import Base, engine
    from sqlalchemy import text

    print("🚀 Inicializando base de datos Cuanto Cuesta...")
    print("=" * 50)

    # 🔹 1. Crear esquemas
    print("🧱 Creando esquemas necesarios...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS products;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS stores;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS prices;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS users;"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS shopping;"))
            conn.commit()
        print("✓ Esquemas creados")
    except Exception as e:
        print(f"❌ Error creando esquemas: {e}")
        return 1

    # 🔹 2. Activar extensiones
    print("🧩 Activando extensiones PostgreSQL...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            conn.commit()
        print("✓ Extensiones activadas correctamente")
    except Exception as e:
        print(f"⚠ Error activando extensiones: {e}")
        return 1

    # 🔹 3. Crear tablas
    print("🛠️ Creando tablas...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Tablas creadas")
    except Exception as e:
        print(f"❌ Error creando tablas: {e}")
        return 1

    # 🔹 4. Ejecutar inicialización completa
    try:
        create_extensions()
        create_search_functions()
        insert_sample_data()
        create_indexes()

        print("\n" + "=" * 50)
        print("✅ Base de datos inicializada exitosamente!")
        print("\n🎯 Funcionalidades disponibles:")
        print("  • Búsqueda inteligente de productos")
        print("  • Manejo de caracteres especiales (Ñuñoa, Peñalolén)")
        print("  • Comparación de precios geográfica")
        print("  • Datos realistas de supermercados chilenos")
        print("\n🌐 Para probar la API:")
        print("  python -m uvicorn app.main:app --reload")
        print("  Documentación: http://localhost:8000/docs")
        print("\n💡 Tip: Si necesitas limpiar y recrear datos, usa:")
        print("  python scripts/init_database.py --clear")

    except Exception as e:
        print(f"\n❌ Error durante la inicialización: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys
    
    # Opción para limpiar datos existentes
    if "--clear" in sys.argv:
        print("⚠️  ATENCIÓN: Esto eliminará TODOS los datos existentes.")
        confirm = input("¿Estás seguro? (escribe 'SI' para confirmar): ")
        if confirm == "SI":
            clear_existing_data()
        else:
            print("Operación cancelada.")
            exit(0)
    
    exit(main())

