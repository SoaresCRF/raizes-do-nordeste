"""cria tabela item_pedido

Revision ID: 5d3f51590801
Revises: 2b19486ba543
Create Date: 2026-10-02 19:15:49.867336

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d3f51590801"
down_revision: str | Sequence[str] | None = "2b19486ba543"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "item_pedido",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("preco_unitario", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "preco_unitario > 0", name=op.f("ck_item_pedido_preco_unitario_positivo")
        ),
        sa.CheckConstraint("quantidade > 0", name=op.f("ck_item_pedido_quantidade_positiva")),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["pedido.id"], name=op.f("fk_item_pedido_pedido_id_pedido")
        ),
        sa.ForeignKeyConstraint(
            ["produto_id"], ["produto.id"], name=op.f("fk_item_pedido_produto_id_produto")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_pedido")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("item_pedido")
