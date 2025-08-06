"""
Configuración de tests para Cuanto Cuesta
"""
import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import CHAR
from geoalchemy2.types import Geography


@compiles(PGUUID, "sqlite")
def compile_pg_uuid(element, compiler, **kw):
    return "CHAR(36)"


@compiles(JSONB, "sqlite")
def compile_jsonb(element, compiler, **kw):
    return "TEXT"


@compiles(Geography, "sqlite")
def compile_geography(element, compiler, **kw):
    return "TEXT"

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings

# URL de base de datos de test
TEST_DATABASE_URL = "sqlite:///./test.db"

# Crear engine de test
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    execution_options={
        "schema_translate_map": {"products": None, "stores": None, "pricing": None}
    }
)

# Crear session de test
TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=test_engine
)


def override_get_db():
    """Override de la dependencia de base de datos para tests"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override de la dependencia
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def test_app():
    """Fixture de la aplicación FastAPI para tests"""
    return app


@pytest.fixture(scope="session")
def client(test_app):
    """Fixture del cliente de test"""
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_session():
    """Fixture de sesión de base de datos para cada test"""
    # Crear tablas
    from app.models import category, product, store, price
    Base.metadata.create_all(
        bind=test_engine,
        tables=[
            category.Category.__table__,
            product.Product.__table__,
            store.Store.__table__,
            price.Price.__table__,
        ],
    )
    
    # Crear sesión
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        # Limpiar tablas después de cada test
        from app.models import category, product, store, price
        Base.metadata.drop_all(
            bind=test_engine,
            tables=[
                category.Category.__table__,
                product.Product.__table__,
                store.Store.__table__,
                price.Price.__table__,
            ],
        )


@pytest.fixture
def sample_category(db_session):
    """Fixture de categoría de ejemplo"""
    from app.models.category import Category
    import uuid
    
    category = Category(
        id=uuid.uuid4(),
        name="Test Category",
        slug="test-category",
        description="Categoría de prueba"
    )
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)
    return category


@pytest.fixture
def sample_supermarket(db_session):
    """Fixture de supermercado de ejemplo"""
    from app.models.supermarket import Supermarket
    import uuid
    
    supermarket = Supermarket(
        id=uuid.uuid4(),
        name="Test Supermarket",
        slug="test-supermarket",
        type="retail",
        logo_url="https://test.com/logo.png",
        website_url="https://test.com",
        delivery_available=True,
        pickup_available=True
    )
    db_session.add(supermarket)
    db_session.commit()
    db_session.refresh(supermarket)
    return supermarket


@pytest.fixture
def sample_store(db_session, sample_supermarket):
    """Fixture de tienda de ejemplo"""
    from app.models.store import Store
    import uuid
    
    store = Store(
        id=uuid.uuid4(),
        supermarket_id=sample_supermarket.id,
        name="Test Store Ñuñoa",
        address="Av. Test 1234",
        commune="Ñuñoa",
        region="Región Metropolitana",
        phone="+56 2 2345 6789",
        email="test@test.com",
        coordinates="POINT(-70.6693 -33.4489)",
        opening_hours={
            "lunes": "08:00-22:00",
            "martes": "08:00-22:00"
        },
        has_pharmacy=True,
        has_bakery=False,
        has_parking=True
    )
    db_session.add(store)
    db_session.commit()
    db_session.refresh(store)
    return store


@pytest.fixture
def sample_product(db_session, sample_category):
    """Fixture de producto de ejemplo"""
    from app.models.product import Product
    import uuid
    
    product = Product(
        id=uuid.uuid4(),
        name="Test Product",
        brand="Test Brand",
        category_id=sample_category.id,
        barcode="1234567890123",
        description="Producto de prueba",
        unit_type="unidad",
        unit_size="500g",
        image_url="https://test.com/product.jpg"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_product_alt(db_session, sample_category):
    """Producto alternativo de ejemplo"""
    from app.models.product import Product
    import uuid

    product = Product(
        id=uuid.uuid4(),
        name="Alt Product",
        brand="Alternative Brand",
        category_id=sample_category.id,
        barcode="9876543210987",
        description="Producto alternativo",
        unit_type="unidad",
        unit_size="500g",
        image_url="https://test.com/alt_product.jpg"
    )
    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)
    return product


@pytest.fixture
def sample_price(db_session, sample_product, sample_store):
    """Fixture de precio de ejemplo"""
    from app.models.price import Price
    from datetime import datetime
    import uuid
    
    price = Price(
        id=uuid.uuid4(),
        product_id=sample_product.id,
        store_id=sample_store.id,
        normal_price=1500,
        discount_price=1200,
        discount_percentage=20.0,
        stock_status="available",
        promotion_description="20% de descuento",
        scraped_at=datetime.now()
    )
    db_session.add(price)
    db_session.commit()
    db_session.refresh(price)
    return price


@pytest.fixture
def sample_price_alt(db_session, sample_product_alt, sample_store):
    """Precio para producto alternativo"""
    from app.models.price import Price
    from datetime import datetime
    import uuid

    price = Price(
        id=uuid.uuid4(),
        product_id=sample_product_alt.id,
        store_id=sample_store.id,
        normal_price=1400,
        discount_price=1100,
        discount_percentage=21.0,
        stock_status="available",
        promotion_description="21% de descuento",
        scraped_at=datetime.now()
    )
    db_session.add(price)
    db_session.commit()
    db_session.refresh(price)
    return price


# Utilidades para tests
class TestUtils:
    """Utilidades para tests"""
    
    @staticmethod
    def create_test_uuid():
        """Crear UUID de test"""
        import uuid
        return uuid.uuid4()
    
    @staticmethod
    def assert_response_success(response, expected_status=200):
        """Verificar que la respuesta sea exitosa"""
        assert response.status_code == expected_status
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            if "success" in data:
                assert data["success"] is True
    
    @staticmethod
    def assert_response_error(response, expected_status=400):
        """Verificar que la respuesta sea de error"""
        assert response.status_code == expected_status
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            if "success" in data:
                assert data["success"] is False


# Configuración de pytest
def pytest_configure(config):
    """Configuración de pytest"""
    # Configurar variables de entorno para tests
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # DB diferente para tests


def pytest_unconfigure(config):
    """Limpieza después de tests"""
    # Limpiar archivo de base de datos de test
    if os.path.exists("./test.db"):
        os.remove("./test.db")

