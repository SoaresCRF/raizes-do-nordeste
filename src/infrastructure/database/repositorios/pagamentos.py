from decimal import Decimal

from sqlalchemy import Connection, insert, select

from src.domain.pagamento import FormaPagamento, Pagamento, StatusPagamento
from src.infrastructure.database.tabelas import pagamento


class RepositorioPagamentos:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def buscar_ultimo_do_pedido(self, pedido_id: int) -> Pagamento | None:
        consulta = (
            select(pagamento)
            .where(pagamento.c.pedido_id == pedido_id)
            .order_by(pagamento.c.id.desc())
            .limit(1)
        )
        linha = self._conexao.execute(consulta).one_or_none()
        return Pagamento(**linha._mapping) if linha else None

    def inserir(
        self,
        pedido_id: int,
        valor: Decimal,
        forma_pagamento: FormaPagamento,
        *,
        status: StatusPagamento,
        transacao_externa_id: str | None,
        motivo_recusa: str | None,
        payload_gateway: dict | None,
    ) -> Pagamento:
        comando = (
            insert(pagamento)
            .values(
                pedido_id=pedido_id,
                valor=valor,
                forma_pagamento=forma_pagamento,
                status=status,
                transacao_externa_id=transacao_externa_id,
                motivo_recusa=motivo_recusa,
                payload_gateway=payload_gateway,
            )
            .returning(pagamento)
        )
        return Pagamento(**self._conexao.execute(comando).one()._mapping)
