"""cria tabela pagamento

Revision ID: 862877bef109
Revises: bdf942c29573
Create Date: 2026-10-03 00:44:38.604335

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "862877bef109"
down_revision: str | Sequence[str] | None = "bdf942c29573"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pagamento",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDENTE",
                "APROVADO",
                "RECUSADO",
                "ERRO",
                "ESTORNADO",
                name="status_pagamento",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("valor", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "forma_pagamento",
            sa.Enum("MOCK", name="forma_pagamento", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("transacao_externa_id", sa.String(length=80), nullable=True),
        sa.Column("motivo_recusa", sa.String(length=200), nullable=True),
        sa.Column("payload_gateway", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("chave_idempotencia", sa.String(length=80), nullable=True),
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
        sa.CheckConstraint("valor > 0", name=op.f("ck_pagamento_valor_positivo")),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["pedido.id"], name=op.f("fk_pagamento_pedido_id_pedido")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pagamento")),
        sa.UniqueConstraint("chave_idempotencia", name=op.f("uq_pagamento_chave_idempotencia")),
    )


def downgrade() -> None:
    op.drop_table("pagamento")
