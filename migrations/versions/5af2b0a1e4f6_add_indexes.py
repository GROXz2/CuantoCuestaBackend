"""add indexes for products prices stores

Revision ID: 5af2b0a1e4f6
Revises: 
Create Date: 2024-03-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5af2b0a1e4f6'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_index('ix_products_category_id', 'products', ['category_id'], schema='products')
    op.create_index(
        'ix_products_search_vector',
        'products',
        ['search_vector'],
        unique=False,
        postgresql_using='gin',
        schema='products'
    )
    op.create_index(
        'ix_prices_product_store_scraped_at',
        'prices',
        ['product_id', 'store_id', 'scraped_at'],
        schema='pricing'
    )
    op.create_index(
        'ix_stores_location',
        'stores',
        ['location'],
        unique=False,
        postgresql_using='gist',
        schema='stores'
    )

def downgrade():
    op.drop_index('ix_stores_location', table_name='stores', schema='stores')
    op.drop_index('ix_prices_product_store_scraped_at', table_name='prices', schema='pricing')
    op.drop_index('ix_products_search_vector', table_name='products', schema='products')
    op.drop_index('ix_products_category_id', table_name='products', schema='products')
