"""cria tabela produto

Revision ID: 8c3cea3855e8
Revises: 5290385665e5
Create Date: 2026-10-02 19:10:13.193070

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8c3cea3855e8"
down_revision: str | Sequence[str] | None = "5290385665e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "produto",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("preco", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("disponivel_de", sa.Date(), nullable=True),
        sa.Column("disponivel_ate", sa.Date(), nullable=True),
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
            "disponivel_de IS NULL OR disponivel_ate IS NULL OR disponivel_de <= disponivel_ate",
            name=op.f("ck_produto_periodo_disponibilidade_valido"),
        ),
        sa.CheckConstraint("preco > 0", name=op.f("ck_produto_preco_positivo")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_produto")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("produto")
