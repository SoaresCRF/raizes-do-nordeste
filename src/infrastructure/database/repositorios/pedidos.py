from decimal import Decimal

from sqlalchemy import ColumnElement, Connection, func, insert, select, update

from src.domain.pagamento.pagamento import FormaPagamento
from src.domain.pedido.pedido import (
    CanalPedido,
    FiltrosPedido,
    ItemPedido,
    ItemPrecificado,
    Pedido,
    StatusPedido,
)
from src.infrastructure.database.tabelas import item_pedido, pedido


def _filtros(filtros: FiltrosPedido) -> list[ColumnElement[bool]]:
    pares = [
        (pedido.c.canal_pedido, filtros.canal_pedido),
        (pedido.c.status, filtros.status),
        (pedido.c.unidade_id, filtros.unidade_id),
        (pedido.c.cliente_id, filtros.cliente_id),
    ]
    return [coluna == valor for coluna, valor in pares if valor is not None]


class RepositorioPedidos:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def inserir(
        self,
        *,
        cliente_id: int | None,
        unidade_id: int,
        canal_pedido: CanalPedido,
        forma_pagamento: FormaPagamento,
        subtotal: Decimal,
        criado_por_id: int,
    ) -> Pedido:
        # Na criação não há desconto: ele só surge com o resgate de pontos (RN19).
        comando = (
            insert(pedido)
            .values(
                cliente_id=cliente_id,
                unidade_id=unidade_id,
                canal_pedido=canal_pedido,
                forma_pagamento=forma_pagamento,
                subtotal=subtotal,
                total=subtotal,
                criado_por_id=criado_por_id,
            )
            .returning(pedido)
        )
        return Pedido(**self._conexao.execute(comando).one()._mapping)

    def inserir_itens(self, pedido_id: int, itens: list[ItemPrecificado]) -> list[ItemPedido]:
        comando = insert(item_pedido).returning(item_pedido, sort_by_parameter_order=True)
        registros = [
            {
                "pedido_id": pedido_id,
                "produto_id": item.produto_id,
                "quantidade": item.quantidade,
                "preco_unitario": item.preco_unitario,
            }
            for item in itens
        ]
        return [ItemPedido(**linha._mapping) for linha in self._conexao.execute(comando, registros)]

    def buscar_por_id(self, pedido_id: int) -> Pedido | None:
        linha = self._conexao.execute(select(pedido).where(pedido.c.id == pedido_id)).one_or_none()
        return Pedido(**linha._mapping) if linha else None

    def listar_itens(self, pedido_id: int) -> list[ItemPedido]:
        consulta = (
            select(item_pedido)
            .where(item_pedido.c.pedido_id == pedido_id)
            .order_by(item_pedido.c.id)
        )
        return [ItemPedido(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def listar(self, filtros: FiltrosPedido, limit: int, offset: int) -> list[Pedido]:
        # Mais recentes primeiro: é a ordem em que balcão e cozinha acompanham a fila.
        consulta = (
            select(pedido)
            .where(*_filtros(filtros))
            .order_by(pedido.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [Pedido(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self, filtros: FiltrosPedido) -> int:
        consulta = select(func.count()).select_from(pedido).where(*_filtros(filtros))
        return self._conexao.execute(consulta).scalar_one()

    def travar(self, pedido_id: int) -> Pedido | None:
        linha = self._conexao.execute(
            select(pedido).where(pedido.c.id == pedido_id).with_for_update()
        ).one_or_none()
        return Pedido(**linha._mapping) if linha else None

    def atualizar_status(self, pedido_id: int, status: StatusPedido) -> Pedido:
        comando = (
            update(pedido).where(pedido.c.id == pedido_id).values(status=status).returning(pedido)
        )
        return Pedido(**self._conexao.execute(comando).one()._mapping)

    def cancelar(self, pedido_id: int, motivo: str) -> Pedido:
        comando = (
            update(pedido)
            .where(pedido.c.id == pedido_id)
            .values(status=StatusPedido.CANCELADO, motivo_cancelamento=motivo)
            .returning(pedido)
        )
        return Pedido(**self._conexao.execute(comando).one()._mapping)

    def aplicar_desconto(self, pedido_id: int, desconto: Decimal) -> Pedido:
        comando = (
            update(pedido)
            .where(pedido.c.id == pedido_id)
            .values(desconto=pedido.c.desconto + desconto, total=pedido.c.total - desconto)
            .returning(pedido)
        )
        return Pedido(**self._conexao.execute(comando).one()._mapping)
