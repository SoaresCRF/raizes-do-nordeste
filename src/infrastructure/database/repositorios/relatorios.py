from datetime import date

from sqlalchemy import (
    ColumnElement,
    Connection,
    Date,
    Integer,
    Select,
    cast,
    desc,
    distinct,
    func,
    null,
    select,
)

from src.domain.relatorio.relatorio import STATUS_DE_VENDA, Agrupamento, LinhaRelatorio
from src.infrastructure.database.tabelas import item_pedido, pedido, produto, unidade


def _condicoes(
    unidade_id: int | None, de: date | None, ate: date | None
) -> list[ColumnElement[bool]]:
    condicoes = [pedido.c.status.in_(STATUS_DE_VENDA)]
    if unidade_id is not None:
        condicoes.append(pedido.c.unidade_id == unidade_id)
    # A sessão do banco está em UTC: o cast pega o dia UTC do pedido sem somar um
    # dia ao `ate`, o que estouraria em 9999-12-31.
    dia_do_pedido = cast(pedido.c.created_at, Date)
    if de is not None:
        condicoes.append(dia_do_pedido >= de)
    if ate is not None:
        condicoes.append(dia_do_pedido <= ate)
    return condicoes


def _por_pedido(agrupamento: Agrupamento) -> Select:
    chaves = {
        Agrupamento.UNIDADE: (unidade.c.id, unidade.c.nome),
        Agrupamento.REGIAO: (None, unidade.c.regiao),
        Agrupamento.CANAL: (None, pedido.c.canal_pedido),
    }
    grupo_id, grupo = chaves[agrupamento]
    # Soma as quantidades por pedido antes da junção: juntar os itens direto
    # repetiria o total do pedido uma vez por item.
    quantidades = (
        select(
            item_pedido.c.pedido_id,
            func.sum(item_pedido.c.quantidade).label("quantidade"),
        )
        .group_by(item_pedido.c.pedido_id)
        .subquery()
    )
    colunas_do_grupo = [coluna for coluna in (grupo_id, grupo) if coluna is not None]
    return (
        select(
            (grupo_id if grupo_id is not None else null()).label("grupo_id"),
            grupo.label("grupo"),
            func.count(pedido.c.id).label("pedidos"),
            # sum de bigint vira numeric no Postgres; o cast devolve inteiro.
            cast(func.sum(quantidades.c.quantidade), Integer).label("quantidade"),
            func.sum(pedido.c.total).label("total"),
        )
        .select_from(
            pedido.join(unidade, unidade.c.id == pedido.c.unidade_id).join(
                quantidades, quantidades.c.pedido_id == pedido.c.id
            )
        )
        .group_by(*colunas_do_grupo)
    )


def _por_produto() -> Select:
    return (
        select(
            produto.c.id.label("grupo_id"),
            produto.c.nome.label("grupo"),
            func.count(distinct(pedido.c.id)).label("pedidos"),
            func.sum(item_pedido.c.quantidade).label("quantidade"),
            func.sum(item_pedido.c.quantidade * item_pedido.c.preco_unitario).label("total"),
        )
        .select_from(
            item_pedido.join(pedido, pedido.c.id == item_pedido.c.pedido_id).join(
                produto, produto.c.id == item_pedido.c.produto_id
            )
        )
        .group_by(produto.c.id, produto.c.nome)
    )


class RepositorioRelatorios:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def somar_vendas(
        self,
        agrupamento: Agrupamento,
        unidade_id: int | None,
        de: date | None,
        ate: date | None,
    ) -> list[LinhaRelatorio]:
        base = _por_produto() if agrupamento == Agrupamento.PRODUTO else _por_pedido(agrupamento)
        # Ordena pelos rótulos, que existem nos dois formatos de consulta.
        consulta = base.where(*_condicoes(unidade_id, de, ate)).order_by(desc("total"), "grupo")
        return [LinhaRelatorio(**linha._mapping) for linha in self._conexao.execute(consulta)]
