from sqlalchemy import Connection, func, select, update
from sqlalchemy.dialects.postgresql import insert

from src.domain.estoque.estoque import (
    Estoque,
    MovimentacaoEstoque,
    SaldoProduto,
    TipoMovimentacao,
)
from src.infrastructure.database.tabelas import estoque, movimentacao_estoque, produto

_ESTOQUE_COM_PRODUTO = estoque.join(produto, produto.c.id == estoque.c.produto_id)


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

    def inserir_se_nao_existir(self, unidade_id: int, produto_id: int) -> None:
        comando = (
            insert(estoque)
            .values(unidade_id=unidade_id, produto_id=produto_id, quantidade=0)
            .on_conflict_do_nothing(index_elements=[estoque.c.unidade_id, estoque.c.produto_id])
        )
        self._conexao.execute(comando)

    def travar(self, unidade_id: int, produto_id: int) -> Estoque:
        consulta = (
            select(estoque)
            .where(estoque.c.unidade_id == unidade_id, estoque.c.produto_id == produto_id)
            .with_for_update()
        )
        return Estoque(**self._conexao.execute(consulta).one()._mapping)

    def travar_varios(self, unidade_id: int, produto_ids: list[int]) -> dict[int, Estoque]:
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
