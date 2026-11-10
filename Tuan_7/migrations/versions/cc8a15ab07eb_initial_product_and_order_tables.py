from alembic import op
import sqlalchemy as sa


revision = 'cc8a15ab07eb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('products',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sku', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=True),
    sa.Column('price_cents', sa.Integer(), nullable=False),
    sa.Column('qty_in_stock', sa.Integer(), nullable=False),
    sa.Column('archived', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.CheckConstraint('price_cents >= 0', name='ck_products_price_nonnegative'),
    sa.CheckConstraint('qty_in_stock >= 0', name='ck_products_stock_nonnegative'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_products_archived'), ['archived'], unique=False)
        batch_op.create_index(batch_op.f('ix_products_sku'), ['sku'], unique=True)

    op.create_table('order_items',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('qty', sa.Integer(), nullable=False),
    sa.Column('unit_price_cents', sa.Integer(), nullable=False),
    sa.CheckConstraint('qty > 0', name='ck_order_items_qty_positive'),
    sa.CheckConstraint('unit_price_cents >= 0', name='ck_order_items_price_nonnegative'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_order_items_order_id'), ['order_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_order_items_product_id'), ['product_id'], unique=False)



def downgrade():
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_order_items_product_id'))
        batch_op.drop_index(batch_op.f('ix_order_items_order_id'))

    op.drop_table('order_items')
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_products_sku'))
        batch_op.drop_index(batch_op.f('ix_products_archived'))

    op.drop_table('products')
    op.drop_table('orders')
