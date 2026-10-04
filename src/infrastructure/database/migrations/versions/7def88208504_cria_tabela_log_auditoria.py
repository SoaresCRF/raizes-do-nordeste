"""cria tabela log_auditoria

Revision ID: 7def88208504
Revises: 37a5dc0b2ada
Create Date: 2026-10-03 00:45:10.101012

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7def88208504"
down_revision: str | Sequence[str] | None = "37a5dc0b2ada"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("unidade_id", sa.Integer(), nullable=True),
        sa.Column("acao", sa.String(length=60), nullable=False),
        sa.Column("entidade", sa.String(length=40), nullable=False),
        sa.Column("entidade_id", sa.Integer(), nullable=False),
        sa.Column("dados_antes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dados_depois", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_id", sa.String(length=40), nullable=True),
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
            ["unidade_id"], ["unidade.id"], name=op.f("fk_log_auditoria_unidade_id_unidade")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_log_auditoria_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_log_auditoria")),
    )
    op.create_index(
        "ix_log_auditoria_entidade_entidade_id",
        "log_auditoria",
        ["entidade", "entidade_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_log_auditoria_entidade_entidade_id", table_name="log_auditoria")
    op.drop_table("log_auditoria")
