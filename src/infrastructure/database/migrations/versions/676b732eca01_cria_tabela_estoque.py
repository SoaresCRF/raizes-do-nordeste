"""cria tabela estoque

Revision ID: 676b732eca01
Revises: 8c3cea3855e8
Create Date: 2026-10-02 19:10:26.609844

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "676b732eca01"
down_revision: str | Sequence[str] | None = "8c3cea3855e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "estoque",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("unidade_id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
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
        sa.CheckConstraint("quantidade >= 0", name=op.f("ck_estoque_quantidade_nao_negativa")),
        sa.ForeignKeyConstraint(
            ["produto_id"], ["produto.id"], name=op.f("fk_estoque_produto_id_produto")
        ),
        sa.ForeignKeyConstraint(
            ["unidade_id"], ["unidade.id"], name=op.f("fk_estoque_unidade_id_unidade")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_estoque")),
        sa.UniqueConstraint("unidade_id", "produto_id", name=op.f("uq_estoque_unidade_id")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("estoque")
