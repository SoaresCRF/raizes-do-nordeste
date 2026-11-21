from dataclasses import asdict

from sqlalchemy import Connection

from src.domain.auditoria import AcaoAuditoria
from src.domain.unidade import DadosUnidade, Unidade, unidade_nao_encontrada
from src.infrastructure.database.repositorios.auditoria import RepositorioAuditoria
from src.infrastructure.database.repositorios.unidades import RepositorioUnidades

ENTIDADE_UNIDADE = "Unidade"


def listar_unidades(conexao: Connection, limit: int, offset: int) -> tuple[list[Unidade], int]:
    repositorio = RepositorioUnidades(conexao)
    return repositorio.listar(limit, offset), repositorio.contar()


def consultar_unidade(conexao: Connection, unidade_id: int) -> Unidade:
    unidade = RepositorioUnidades(conexao).buscar_por_id(unidade_id)
    if unidade is None:
        raise unidade_nao_encontrada(unidade_id)
    return unidade


def cadastrar_unidade(conexao: Connection, autor_id: int, dados: DadosUnidade) -> Unidade:
    unidade = RepositorioUnidades(conexao).inserir(dados)
    RepositorioAuditoria(conexao).registrar(
        usuario_id=autor_id,
        unidade_id=unidade.id,
        acao=AcaoAuditoria.UNIDADE_CRIADA,
        entidade=ENTIDADE_UNIDADE,
        entidade_id=unidade.id,
        dados_antes=None,
        dados_depois=asdict(dados),
    )
    return unidade


def atualizar_unidade(
    conexao: Connection, unidade_id: int, dados: DadosUnidade, ativa: bool
) -> Unidade:
    unidade = RepositorioUnidades(conexao).atualizar(unidade_id, dados, ativa)
    if unidade is None:
        raise unidade_nao_encontrada(unidade_id)
    return unidade
