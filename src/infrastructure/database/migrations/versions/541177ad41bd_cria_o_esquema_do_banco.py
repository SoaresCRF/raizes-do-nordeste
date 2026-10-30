from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "541177ad41bd"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "produto",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("preco", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.CheckConstraint("preco > 0", name=op.f("ck_produto_preco_positivo")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_produto")),
    )
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
        sa.UniqueConstraint(
            "unidade_id", "produto_id", name=op.f("uq_estoque_unidade_id_produto_id")
        ),
    )
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
    op.create_table(
        "consentimento",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column(
            "finalidade",
            sa.Enum(
                "FIDELIDADE",
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
    op.create_table(
        "pedido",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("cliente_id", sa.Integer(), nullable=True),
        sa.Column("unidade_id", sa.Integer(), nullable=False),
        sa.Column(
            "canal_pedido",
            sa.Enum(
                "APP",
                "TOTEM",
                "BALCAO",
                "PICKUP",
                "WEB",
                name="canal_pedido",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "AGUARDANDO_PAGAMENTO",
                "EM_PREPARO",
                "PRONTO",
                "ENTREGUE",
                "CANCELADO",
                name="status_pedido",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="AGUARDANDO_PAGAMENTO",
            nullable=False,
        ),
        sa.Column(
            "forma_pagamento",
            sa.Enum("MOCK", name="forma_pagamento", native_enum=False, create_constraint=True),
            nullable=False,
        ),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "desconto", sa.Numeric(precision=10, scale=2), server_default="0", nullable=False
        ),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("criado_por_id", sa.Integer(), nullable=False),
        sa.Column("motivo_cancelamento", sa.String(length=200), nullable=True),
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
            "desconto >= 0 AND desconto <= subtotal", name=op.f("ck_pedido_desconto_valido")
        ),
        sa.CheckConstraint("subtotal >= 0", name=op.f("ck_pedido_subtotal_nao_negativo")),
        sa.CheckConstraint("total = subtotal - desconto", name=op.f("ck_pedido_total_consistente")),
        sa.ForeignKeyConstraint(
            ["cliente_id"], ["usuario.id"], name=op.f("fk_pedido_cliente_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["criado_por_id"], ["usuario.id"], name=op.f("fk_pedido_criado_por_id_usuario")
        ),
        sa.ForeignKeyConstraint(
            ["unidade_id"], ["unidade.id"], name=op.f("fk_pedido_unidade_id_unidade")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pedido")),
    )
    op.create_index(op.f("ix_pedido_canal_pedido"), "pedido", ["canal_pedido"], unique=False)
    op.create_index(op.f("ix_pedido_cliente_id"), "pedido", ["cliente_id"], unique=False)
    op.create_index("ix_pedido_unidade_id_status", "pedido", ["unidade_id", "status"], unique=False)
    op.create_table(
        "sessao",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
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
    )
    op.create_index(op.f("ix_sessao_usuario_id"), "sessao", ["usuario_id"], unique=False)
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
    op.create_table(
        "movimentacao_estoque",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("estoque_id", sa.Integer(), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum(
                "ENTRADA",
                "SAIDA",
                name="tipo_movimentacao",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
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
            "quantidade > 0", name=op.f("ck_movimentacao_estoque_quantidade_positiva")
        ),
        sa.ForeignKeyConstraint(
            ["estoque_id"], ["estoque.id"], name=op.f("fk_movimentacao_estoque_estoque_id_estoque")
        ),
        sa.ForeignKeyConstraint(
            ["pedido_id"], ["pedido.id"], name=op.f("fk_movimentacao_estoque_pedido_id_pedido")
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_movimentacao_estoque_usuario_id_usuario")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_movimentacao_estoque")),
    )
    op.create_index(
        op.f("ix_movimentacao_estoque_estoque_id"),
        "movimentacao_estoque",
        ["estoque_id"],
        unique=False,
    )
    op.create_table(
        "pagamento",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "APROVADO",
                "RECUSADO",
                "ERRO",
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
    )
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
    op.drop_table("pagamento")
    op.drop_index(op.f("ix_movimentacao_estoque_estoque_id"), table_name="movimentacao_estoque")
    op.drop_table("movimentacao_estoque")
    op.drop_table("item_pedido")
    op.drop_index(op.f("ix_sessao_usuario_id"), table_name="sessao")
    op.drop_table("sessao")
    op.drop_index("ix_pedido_unidade_id_status", table_name="pedido")
    op.drop_index(op.f("ix_pedido_cliente_id"), table_name="pedido")
    op.drop_index(op.f("ix_pedido_canal_pedido"), table_name="pedido")
    op.drop_table("pedido")
    op.drop_index("ix_log_auditoria_entidade_entidade_id", table_name="log_auditoria")
    op.drop_table("log_auditoria")
    op.drop_table("consentimento")
    op.drop_table("usuario")
    op.drop_table("estoque")
    op.drop_table("unidade")
    op.drop_table("produto")
