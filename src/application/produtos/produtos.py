from datetime import UTC, datetime

from sqlalchemy import Connection

from src.application.unidades.unidades import consultar_unidade
from src.domain.auditoria.auditoria import AcaoAuditoria
from src.domain.erros.erros import RecursoNaoEncontrado
from src.domain.produto.produto import DadosProduto, ItemCardapio, Produto, validar_periodo
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.produtos import RepositorioProdutos

ENTIDADE_PRODUTO = "Produto"


def listar_produtos(
    conexao: Connection, nome: str | None, limit: int, offset: int
) -> tuple[list[Produto], int]:
    repositorio = RepositorioProdutos(conexao)
    return repositorio.listar(nome, limit, offset), repositorio.contar(nome)


def consultar_produto(conexao: Connection, produto_id: int) -> Produto:
    produto = RepositorioProdutos(conexao).buscar_por_id(produto_id)
    if produto is None:
        raise RecursoNaoEncontrado(f"Produto {produto_id} não encontrado")
    return produto


def cadastrar_produto(conexao: Connection, dados: DadosProduto) -> Produto:
    validar_periodo(dados.disponivel_de, dados.disponivel_ate)
    return RepositorioProdutos(conexao).inserir(dados)


def consultar_cardapio(
    conexao: Connection, unidade_id: int, limit: int, offset: int
) -> tuple[list[ItemCardapio], int]:
    consultar_unidade(conexao, unidade_id)
    # Datas do sistema em UTC; RN24 compara só o dia.
    hoje = datetime.now(UTC).date()
    repositorio = RepositorioProdutos(conexao)
    return (
        repositorio.listar_cardapio(unidade_id, hoje, limit, offset),
        repositorio.contar_cardapio(unidade_id, hoje),
    )


def _para_auditoria(produto: Produto) -> dict:
    # Chaves em camelCase como no resto da API (a auditoria sai em E32); preço como
    # texto para não perder centavos no JSON.
    return {
        "nome": produto.nome,
        "descricao": produto.descricao,
        "preco": str(produto.preco),
        "ativo": produto.ativo,
        "disponivelDe": produto.disponivel_de.isoformat() if produto.disponivel_de else None,
        "disponivelAte": produto.disponivel_ate.isoformat() if produto.disponivel_ate else None,
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
    validar_periodo(dados.disponivel_de, dados.disponivel_ate)
    antes = consultar_produto(conexao, produto_id)
    depois = RepositorioProdutos(conexao).atualizar(produto_id, dados, ativo)
    _auditar(conexao, autor_id, AcaoAuditoria.PRODUTO_ALTERADO, antes, depois)
    return depois


def desativar_produto(conexao: Connection, autor_id: int, produto_id: int) -> None:
    antes = consultar_produto(conexao, produto_id)
    # DELETE repetido não muda nada: responde igual e não gera outra auditoria.
    if not antes.ativo:
        return
    depois = RepositorioProdutos(conexao).desativar(produto_id)
    _auditar(conexao, autor_id, AcaoAuditoria.PRODUTO_DESATIVADO, antes, depois)
