from sqlalchemy import ColumnElement, Connection, func, select, update
from sqlalchemy.dialects.postgresql import insert

from src.domain.estoque.estoque import (
    Estoque,
    ItemHistoricoEstoque,
    MovimentacaoEstoque,
    SaldoProduto,
    TipoMovimentacao,
)
from src.infrastructure.database.tabelas import estoque, movimentacao_estoque, produto

_ESTOQUE_COM_PRODUTO = estoque.join(produto, produto.c.id == estoque.c.produto_id)
_MOVIMENTACAO_COM_ESTOQUE = movimentacao_estoque.join(
    estoque, estoque.c.id == movimentacao_estoque.c.estoque_id
)


def _no_historico(unidade_id: int, produto_id: int | None) -> list[ColumnElement[bool]]:
    filtros = [estoque.c.unidade_id == unidade_id]
    if produto_id is not None:
        filtros.append(estoque.c.produto_id == produto_id)
    return filtros


class RepositorioEstoque:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def listar_saldos(self, unidade_id: int, limit: int, offset: int) -> list[SaldoProduto]:
        consulta = (
            select(estoque.c.produto_id, produto.c.nome, estoque.c.quantidade)
            .select_from(_ESTOQUE_COM_PRODUTO)
            .where(estoque.c.unidade_id == unidade_id)
            .order_by(estoque.c.produto_id)
            .limit(limit)
            .offset(offset)
        )
        return [SaldoProduto(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar_saldos(self, unidade_id: int) -> int:
        consulta = (
            select(func.count()).select_from(estoque).where(estoque.c.unidade_id == unidade_id)
        )
        return self._conexao.execute(consulta).scalar_one()

    def criar_se_nao_existir(self, unidade_id: int, produto_id: int) -> None:
        # ON CONFLICT: duas primeiras entradas simultâneas do mesmo produto não esbarram
        # no único (unidade_id, produto_id). Não espera o lock de quem já movimenta.
        comando = (
            insert(estoque)
            .values(unidade_id=unidade_id, produto_id=produto_id, quantidade=0)
            .on_conflict_do_nothing(index_elements=[estoque.c.unidade_id, estoque.c.produto_id])
        )
        self._conexao.execute(comando)

    def travar(self, unidade_id: int, produto_id: int) -> Estoque:
        # FOR UPDATE: movimentações simultâneas do mesmo produto esperam a vez, e a saída
        # não confere o saldo com um valor que outra transação já mudou (RN06).
        consulta = (
            select(estoque)
            .where(estoque.c.unidade_id == unidade_id, estoque.c.produto_id == produto_id)
            .with_for_update()
        )
        return Estoque(**self._conexao.execute(consulta).one()._mapping)

    def travar_varios(self, unidade_id: int, produto_ids: list[int]) -> dict[int, Estoque]:
        # Ordem fixa por produto: dois pedidos com produtos em comum pegam os locks na
        # mesma sequência e não entram em deadlock.
        consulta = (
            select(estoque)
            .where(estoque.c.unidade_id == unidade_id, estoque.c.produto_id.in_(produto_ids))
            .order_by(estoque.c.produto_id)
            .with_for_update()
        )
        return {
            linha.produto_id: Estoque(**linha._mapping) for linha in self._conexao.execute(consulta)
        }

    def atualizar_quantidade(self, estoque_id: int, quantidade: int) -> None:
        self._conexao.execute(
            update(estoque).where(estoque.c.id == estoque_id).values(quantidade=quantidade)
        )

    def registrar_movimentacao(
        self,
        *,
        estoque_id: int,
        tipo: TipoMovimentacao,
        quantidade: int,
        motivo: str,
        usuario_id: int,
        pedido_id: int | None = None,
    ) -> MovimentacaoEstoque:
        comando = (
            insert(movimentacao_estoque)
            .values(
                estoque_id=estoque_id,
                tipo=tipo,
                quantidade=quantidade,
                motivo=motivo,
                pedido_id=pedido_id,
                usuario_id=usuario_id,
            )
            .returning(movimentacao_estoque)
        )
        return MovimentacaoEstoque(**self._conexao.execute(comando).one()._mapping)

    def listar_movimentacoes(
        self, unidade_id: int, produto_id: int | None, limit: int, offset: int
    ) -> list[ItemHistoricoEstoque]:
        consulta = (
            select(
                movimentacao_estoque.c.id.label("movimentacao_id"),
                estoque.c.produto_id,
                movimentacao_estoque.c.tipo,
                movimentacao_estoque.c.quantidade,
                movimentacao_estoque.c.motivo,
                movimentacao_estoque.c.pedido_id,
                movimentacao_estoque.c.usuario_id,
                movimentacao_estoque.c.created_at,
            )
            .select_from(_MOVIMENTACAO_COM_ESTOQUE)
            .where(*_no_historico(unidade_id, produto_id))
            .order_by(movimentacao_estoque.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [ItemHistoricoEstoque(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar_movimentacoes(self, unidade_id: int, produto_id: int | None) -> int:
        consulta = (
            select(func.count())
            .select_from(_MOVIMENTACAO_COM_ESTOQUE)
            .where(*_no_historico(unidade_id, produto_id))
        )
        return self._conexao.execute(consulta).scalar_one()
