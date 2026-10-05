from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints

from src.api.autenticacao import GestorLogado
from src.api.dependencias import ConexaoBanco
from src.api.schemas.auditoria import TAMANHO_MAXIMO_ENTIDADE, LogAuditoriaResposta
from src.api.schemas.campos import ID_MAXIMO, SemCaractereNulo
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.application.auditoria.auditoria import listar_auditoria
from src.domain.auditoria.auditoria import AcaoAuditoria, FiltrosAuditoria

roteador = APIRouter(prefix="/auditoria", tags=["Auditoria"])


@roteador.get("")
def listar_registros_de_auditoria(
    paginacao: Annotated[ParametrosPaginacao, Depends(obter_paginacao)],
    usuario: GestorLogado,
    conexao: ConexaoBanco,
    entidade: Annotated[
        str | None,
        StringConstraints(min_length=1, max_length=TAMANHO_MAXIMO_ENTIDADE),
        SemCaractereNulo,
        Query(),
    ] = None,
    entidade_id: Annotated[int | None, Query(alias="entidadeId", gt=0, le=ID_MAXIMO)] = None,
    acao: Annotated[AcaoAuditoria | None, Query()] = None,
    unidade_id: Annotated[int | None, Query(alias="unidadeId", gt=0, le=ID_MAXIMO)] = None,
) -> Pagina[LogAuditoriaResposta]:
    filtros = FiltrosAuditoria(
        entidade=entidade, entidade_id=entidade_id, acao=acao, unidade_id=unidade_id
    )
    registros, total = listar_auditoria(
        conexao, usuario, filtros, paginacao.limit, paginacao.offset
    )
    return Pagina[LogAuditoriaResposta].criar(
        [
            LogAuditoriaResposta(
                log_id=registro.id,
                usuario_id=registro.usuario_id,
                unidade_id=registro.unidade_id,
                acao=registro.acao,
                entidade=registro.entidade,
                entidade_id=registro.entidade_id,
                dados_antes=registro.dados_antes,
                dados_depois=registro.dados_depois,
                request_id=registro.request_id,
                created_at=registro.created_at,
            )
            for registro in registros
        ],
        total,
        paginacao,
    )
