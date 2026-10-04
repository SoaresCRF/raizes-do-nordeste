"""cria tabela consentimento

Revision ID: 5bbee3dc3ae1
Revises: 862877bef109
Create Date: 2026-10-03 00:44:51.836665

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5bbee3dc3ae1"
down_revision: str | Sequence[str] | None = "862877bef109"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "consentimento",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "finalidade",
            sa.Enum(
                "FIDELIDADE",
                "MARKETING",
                name="finalidade_consentimento",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("concedido", sa.Boolean(), nullable=False),
        sa.Column("versao_termo", sa.String(length=20), nullable=False),
        sa.Column(
            "registrado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_consentimento_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consentimento")),
    )


def downgrade() -> None:
    op.drop_table("consentimento")
