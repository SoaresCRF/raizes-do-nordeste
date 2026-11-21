from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import StringConstraints

from src.api.autenticacao import GestorLogado
from src.api.dependencias import ConexaoBanco
from src.api.openapi import auditoria as documentacao
from src.api.schemas.auditoria import TAMANHO_MAXIMO_ENTIDADE, LogAuditoriaResposta
from src.api.schemas.campos import ID_MAXIMO, SemCaractereNulo
from src.api.schemas.paginacao import Pagina, ParametrosPaginacao, obter_paginacao
from src.application.auditoria import listar_auditoria
from src.domain.auditoria import FiltrosAuditoria

roteador = APIRouter(prefix="/auditoria", tags=["Auditoria"])


@roteador.get("", **documentacao.LISTAR_AUDITORIA)
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
) -> Pagina[LogAuditoriaResposta]:
    filtros = FiltrosAuditoria(entidade=entidade, entidade_id=entidade_id, unidade_id=None)
    registros, total = listar_auditoria(
        conexao, usuario, filtros, paginacao.limit, paginacao.offset
    )
    return Pagina[LogAuditoriaResposta].criar(
        [
            LogAuditoriaResposta.model_validate({**vars(registro), "log_id": registro.id})
            for registro in registros
        ],
        total,
        paginacao,
    )
