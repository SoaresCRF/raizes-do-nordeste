from decimal import Decimal

from sqlalchemy import ColumnElement, Connection, Select, func, insert, select, update

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


def _montar_condicoes(filtros: FiltrosPedido) -> list[ColumnElement[bool]]:
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

    def _buscar(self, consulta: Select) -> Pedido | None:
        linha = self._conexao.execute(consulta).one_or_none()
        return Pedido(**linha._mapping) if linha else None

    def buscar_por_id(self, pedido_id: int) -> Pedido | None:
        return self._buscar(select(pedido).where(pedido.c.id == pedido_id))

    def listar_itens(self, pedido_id: int) -> list[ItemPedido]:
        consulta = (
            select(item_pedido)
            .where(item_pedido.c.pedido_id == pedido_id)
            .order_by(item_pedido.c.id)
        )
        return [ItemPedido(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def listar(self, filtros: FiltrosPedido, limit: int, offset: int) -> list[Pedido]:
        consulta = (
            select(pedido)
            .where(*_montar_condicoes(filtros))
            .order_by(pedido.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [Pedido(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self, filtros: FiltrosPedido) -> int:
        consulta = select(func.count()).select_from(pedido).where(*_montar_condicoes(filtros))
        return self._conexao.execute(consulta).scalar_one()

    def travar(self, pedido_id: int) -> Pedido | None:
        return self._buscar(select(pedido).where(pedido.c.id == pedido_id).with_for_update())

    def _atualizar(self, pedido_id: int, **valores: object) -> Pedido:
        comando = update(pedido).where(pedido.c.id == pedido_id).values(**valores).returning(pedido)
        return Pedido(**self._conexao.execute(comando).one()._mapping)

    def atualizar_status(self, pedido_id: int, status: StatusPedido) -> Pedido:
        return self._atualizar(pedido_id, status=status)

    def cancelar(self, pedido_id: int, motivo: str) -> Pedido:
        return self._atualizar(pedido_id, status=StatusPedido.CANCELADO, motivo_cancelamento=motivo)

    def aplicar_desconto(self, pedido_id: int, desconto: Decimal) -> Pedido:
        return self._atualizar(
            pedido_id, desconto=pedido.c.desconto + desconto, total=pedido.c.total - desconto
        )
