from sqlalchemy import Connection

from src.application.unidades.unidades import consultar_unidade
from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.produto.produto import (
    DadosProduto,
    ItemCardapio,
    Produto,
    produto_nao_encontrado,
)
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.produtos import RepositorioProdutos

ENTIDADE_PRODUTO = "Produto"


def listar_produtos(conexao: Connection, limit: int, offset: int) -> tuple[list[Produto], int]:
    repositorio = RepositorioProdutos(conexao)
    return repositorio.listar(limit, offset), repositorio.contar()


def consultar_produto(conexao: Connection, produto_id: int) -> Produto:
    produto = RepositorioProdutos(conexao).buscar_por_id(produto_id)
    if produto is None:
        raise produto_nao_encontrado(produto_id)
    return produto


def cadastrar_produto(conexao: Connection, dados: DadosProduto) -> Produto:
    return RepositorioProdutos(conexao).inserir(dados)


def consultar_cardapio(
    conexao: Connection, unidade_id: int, limit: int, offset: int
) -> tuple[list[ItemCardapio], int]:
    consultar_unidade(conexao, unidade_id)
    repositorio = RepositorioProdutos(conexao)
    return (
        repositorio.listar_cardapio(unidade_id, limit, offset),
        repositorio.contar_cardapio(unidade_id),
    )


def _para_auditoria(produto: Produto) -> dict:
    return {
        "nome": produto.nome,
        "descricao": produto.descricao,
        "preco": str(produto.preco),
        "ativo": produto.ativo,
    }


def _auditar(
    conexao: Connection, autor_id: int, acao: AcaoAuditoria, antes: Produto, depois: Produto
) -> None:
    RepositorioAuditoria(conexao).registrar(
        usuario_id=autor_id,
        unidade_id=None,
        acao=acao,
        entidade=ENTIDADE_PRODUTO,
        entidade_id=depois.id,
        dados_antes=_para_auditoria(antes),
        dados_depois=_para_auditoria(depois),
    )


def atualizar_produto(
    conexao: Connection, autor_id: int, produto_id: int, dados: DadosProduto, ativo: bool
) -> Produto:
    antes = consultar_produto(conexao, produto_id)
    depois = RepositorioProdutos(conexao).atualizar(produto_id, dados, ativo)
    _auditar(conexao, autor_id, AcaoAuditoria.PRODUTO_ALTERADO, antes, depois)
    return depois


def desativar_produto(conexao: Connection, autor_id: int, produto_id: int) -> None:
    antes = consultar_produto(conexao, produto_id)
    if not antes.ativo:
        return
    depois = RepositorioProdutos(conexao).desativar(produto_id)
    _auditar(conexao, autor_id, AcaoAuditoria.PRODUTO_DESATIVADO, antes, depois)
