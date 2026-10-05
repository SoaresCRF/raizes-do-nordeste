from decimal import Decimal

from sqlalchemy import Connection, insert, select, update

from src.domain.pagamento.pagamento import FormaPagamento, Pagamento, StatusPagamento
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

    def buscar_por_id(self, pagamento_id: int) -> Pagamento | None:
        linha = self._conexao.execute(
            select(pagamento).where(pagamento.c.id == pagamento_id)
        ).one_or_none()
        return Pagamento(**linha._mapping) if linha else None

    def inserir_pendente(
        self, pedido_id: int, valor: Decimal, forma_pagamento: FormaPagamento
    ) -> Pagamento:
        comando = (
            insert(pagamento)
            .values(
                pedido_id=pedido_id,
                status=StatusPagamento.PENDENTE,
                valor=valor,
                forma_pagamento=forma_pagamento,
            )
            .returning(pagamento)
        )
        return Pagamento(**self._conexao.execute(comando).one()._mapping)

    def registrar_resultado(
        self,
        pagamento_id: int,
        *,
        status: StatusPagamento,
        transacao_externa_id: str | None,
        motivo_recusa: str | None,
        payload_gateway: dict | None,
    ) -> Pagamento:
        comando = (
            update(pagamento)
            .where(pagamento.c.id == pagamento_id)
            .values(
                status=status,
                transacao_externa_id=transacao_externa_id,
                motivo_recusa=motivo_recusa,
                payload_gateway=payload_gateway,
            )
            .returning(pagamento)
        )
        return Pagamento(**self._conexao.execute(comando).one()._mapping)

    def atualizar_status(self, pagamento_id: int, status: StatusPagamento) -> None:
        self._conexao.execute(
            update(pagamento).where(pagamento.c.id == pagamento_id).values(status=status)
        )
