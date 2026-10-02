"""cria tabela unidade

Revision ID: c92e8dc0429d
Revises:
Create Date: 2026-10-02 19:03:52.488091

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c92e8dc0429d"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "unidade",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("cidade", sa.String(length=80), nullable=False),
        sa.Column("uf", sa.String(length=2), nullable=False),
        sa.Column("regiao", sa.String(length=40), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "COZINHA_COMPLETA",
                "FORMATO_REDUZIDO",
                name="tipo_unidade",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("ativa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_unidade")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("unidade")
