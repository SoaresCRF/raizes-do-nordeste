"""cria tabela usuario

Revision ID: 5290385665e5
Revises: c92e8dc0429d
Create Date: 2026-10-02 19:04:18.952997

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5290385665e5"
down_revision: str | Sequence[str] | None = "c92e8dc0429d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.Column(
            "perfil",
            sa.Enum(
                "CLIENTE",
                "ATENDENTE",
                "COZINHA",
                "GERENTE",
                "ADMIN",
                name="perfil",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("unidade_id", sa.Integer(), nullable=True),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("anonimizado_em", sa.DateTime(timezone=True), nullable=True),
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
            "(perfil IN ('ATENDENTE', 'COZINHA', 'GERENTE')) = (unidade_id IS NOT NULL)",
            name=op.f("ck_usuario_unidade_conforme_perfil"),
        ),
        sa.ForeignKeyConstraint(
            ["unidade_id"], ["unidade.id"], name=op.f("fk_usuario_unidade_id_unidade")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("email", name=op.f("uq_usuario_email")),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("usuario")
