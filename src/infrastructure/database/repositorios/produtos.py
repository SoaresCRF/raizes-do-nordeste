from dataclasses import asdict
from datetime import date

from sqlalchemy import ColumnElement, Connection, func, insert, or_, select, update

from src.domain.produto.produto import DadosProduto, ItemCardapio, Produto
from src.infrastructure.database.tabelas import estoque, produto

_PRODUTO_COM_ESTOQUE = produto.join(estoque, estoque.c.produto_id == produto.c.id)


def _filtros(nome: str | None) -> list[ColumnElement[bool]]:
    if nome is None:
        return []
    # autoescape: % e _ digitados pelo cliente são texto, não curingas do LIKE.
    return [produto.c.nome.icontains(nome, autoescape=True)]


def _no_cardapio(unidade_id: int, hoje: date) -> list[ColumnElement[bool]]:
    # RN03: oferecido na unidade = tem linha de estoque lá (Q23). RN24: dentro do período.
    return [
        estoque.c.unidade_id == unidade_id,
        produto.c.ativo.is_(True),
        or_(produto.c.disponivel_de.is_(None), produto.c.disponivel_de <= hoje),
        or_(produto.c.disponivel_ate.is_(None), produto.c.disponivel_ate >= hoje),
    ]


class RepositorioProdutos:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def buscar_por_id(self, produto_id: int) -> Produto | None:
        linha = self._conexao.execute(
            select(produto).where(produto.c.id == produto_id)
        ).one_or_none()
        return Produto(**linha._mapping) if linha else None

    def listar(self, nome: str | None, limit: int, offset: int) -> list[Produto]:
        consulta = (
            select(produto)
            .where(*_filtros(nome))
            .order_by(produto.c.id)
            .limit(limit)
            .offset(offset)
        )
        return [Produto(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self, nome: str | None) -> int:
        consulta = select(func.count()).select_from(produto).where(*_filtros(nome))
        return self._conexao.execute(consulta).scalar_one()

    def inserir(self, dados: DadosProduto) -> Produto:
        comando = insert(produto).values(**asdict(dados)).returning(produto)
        return Produto(**self._conexao.execute(comando).one()._mapping)

    def atualizar(self, produto_id: int, dados: DadosProduto, ativo: bool) -> Produto:
        comando = (
            update(produto)
            .where(produto.c.id == produto_id)
            .values(**asdict(dados), ativo=ativo)
            .returning(produto)
        )
        return Produto(**self._conexao.execute(comando).one()._mapping)

    def listar_cardapio(
        self, unidade_id: int, hoje: date, limit: int, offset: int
    ) -> list[ItemCardapio]:
        consulta = (
            select(
                produto.c.id.label("produto_id"),
                produto.c.nome,
                produto.c.descricao,
                produto.c.preco,
                (estoque.c.quantidade > 0).label("disponivel"),
            )
            .select_from(_PRODUTO_COM_ESTOQUE)
            .where(*_no_cardapio(unidade_id, hoje))
            .order_by(produto.c.id)
            .limit(limit)
            .offset(offset)
        )
        return [ItemCardapio(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar_cardapio(self, unidade_id: int, hoje: date) -> int:
        consulta = (
            select(func.count())
            .select_from(_PRODUTO_COM_ESTOQUE)
            .where(*_no_cardapio(unidade_id, hoje))
        )
        return self._conexao.execute(consulta).scalar_one()

    def desativar(self, produto_id: int) -> Produto:
        comando = (
            update(produto).where(produto.c.id == produto_id).values(ativo=False).returning(produto)
        )
        return Produto(**self._conexao.execute(comando).one()._mapping)

    def buscar_por_ids(self, produto_ids: list[int]) -> dict[int, Produto]:
        consulta = select(produto).where(produto.c.id.in_(produto_ids))
        return {linha.id: Produto(**linha._mapping) for linha in self._conexao.execute(consulta)}

    def listar_ids_no_cardapio(
        self, unidade_id: int, produto_ids: list[int], hoje: date
    ) -> set[int]:
        consulta = (
            select(produto.c.id)
            .select_from(_PRODUTO_COM_ESTOQUE)
            .where(*_no_cardapio(unidade_id, hoje), produto.c.id.in_(produto_ids))
        )
        return set(self._conexao.execute(consulta).scalars())
