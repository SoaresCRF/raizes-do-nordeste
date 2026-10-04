"""cria tabela sessao

Revision ID: ca588d70d180
Revises: 7def88208504
Create Date: 2026-10-03 12:00:52.245494

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ca588d70d180"
down_revision: str | Sequence[str] | None = "7def88208504"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sessao",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True), nullable=True),
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
            ["usuario_id"], ["usuario.id"], name=op.f("fk_sessao_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessao")),
        sa.UniqueConstraint("refresh_token_hash", name=op.f("uq_sessao_refresh_token_hash")),
    )
    op.create_index(op.f("ix_sessao_usuario_id"), "sessao", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sessao_usuario_id"), table_name="sessao")
    op.drop_table("sessao")
