from dataclasses import asdict

from sqlalchemy import ColumnElement, Connection, func, insert, select, update

from src.domain.produto.produto import DadosProduto, ItemCardapio, Produto
from src.infrastructure.database.tabelas import estoque, produto

_PRODUTO_COM_ESTOQUE = produto.join(estoque, estoque.c.produto_id == produto.c.id)


def _montar_condicoes_do_cardapio(unidade_id: int) -> list[ColumnElement[bool]]:
    return [estoque.c.unidade_id == unidade_id, produto.c.ativo.is_(True)]


class RepositorioProdutos:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def buscar_por_id(self, produto_id: int) -> Produto | None:
        linha = self._conexao.execute(
            select(produto).where(produto.c.id == produto_id)
        ).one_or_none()
        return Produto(**linha._mapping) if linha else None

    def listar(self, limit: int, offset: int) -> list[Produto]:
        consulta = select(produto).order_by(produto.c.id).limit(limit).offset(offset)
        return [Produto(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar(self) -> int:
        consulta = select(func.count()).select_from(produto)
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

    def listar_cardapio(self, unidade_id: int, limit: int, offset: int) -> list[ItemCardapio]:
        consulta = (
            select(
                produto.c.id.label("produto_id"),
                produto.c.nome,
                produto.c.descricao,
                produto.c.preco,
                (estoque.c.quantidade > 0).label("disponivel"),
            )
            .select_from(_PRODUTO_COM_ESTOQUE)
            .where(*_montar_condicoes_do_cardapio(unidade_id))
            .order_by(produto.c.id)
            .limit(limit)
            .offset(offset)
        )
        return [ItemCardapio(**linha._mapping) for linha in self._conexao.execute(consulta)]

    def contar_cardapio(self, unidade_id: int) -> int:
        consulta = (
            select(func.count())
            .select_from(_PRODUTO_COM_ESTOQUE)
            .where(*_montar_condicoes_do_cardapio(unidade_id))
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

    def listar_ids_no_cardapio(self, unidade_id: int, produto_ids: list[int]) -> set[int]:
        consulta = (
            select(produto.c.id)
            .select_from(_PRODUTO_COM_ESTOQUE)
            .where(*_montar_condicoes_do_cardapio(unidade_id), produto.c.id.in_(produto_ids))
        )
        return set(self._conexao.execute(consulta).scalars())
