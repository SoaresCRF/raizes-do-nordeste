"""cria tabela transacao_fidelidade

Revision ID: 37a5dc0b2ada
Revises: 5bbee3dc3ae1
Create Date: 2026-10-03 00:45:02.573713

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "37a5dc0b2ada"
down_revision: str | Sequence[str] | None = "5bbee3dc3ae1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transacao_fidelidade",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "ACUMULO",
                "RESGATE",
                "ESTORNO",
                name="tipo_transacao_fidelidade",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("pontos", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
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
            "(tipo <> 'ACUMULO' OR pontos > 0) AND (tipo <> 'RESGATE' OR pontos < 0)",
            name=op.f("ck_transacao_fidelidade_sinal_conforme_tipo"),
        ),
        sa.CheckConstraint(
            "pontos <> 0", name=op.f("ck_transacao_fidelidade_pontos_diferente_de_zero")
        ),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["usuario.id"], name=op.f("fk_transacao_fidelidade_cliente_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["pedido.id"], name=op.f("fk_transacao_fidelidade_pedido_id_pedido")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_transacao_fidelidade")),
    )


def downgrade() -> None:
    op.drop_table("transacao_fidelidade")
