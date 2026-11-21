import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.erros import (
    ERRO_INTERNO,
    JSON_INVALIDO,
    MENSAGEM_ERRO_INTERNO,
    MENSAGEM_JSON_INVALIDO,
    METODO_NAO_PERMITIDO,
    RECURSO_NAO_ENCONTRADO,
    STATUS_POR_ERRO,
    DetalheResposta,
    resposta_de_erro,
)
from src.api.validacao import detalhes_de_validacao
from src.domain.erros import MENSAGEM_DADOS_INVALIDOS, DadosInvalidos, ErroDominio

logger = logging.getLogger(__name__)


async def _tratar_erro_de_dominio(request: Request, erro: ErroDominio) -> JSONResponse:
    detalhes = [DetalheResposta(field=d.campo, issue=d.problema) for d in erro.detalhes]
    return resposta_de_erro(
        STATUS_POR_ERRO[type(erro)], erro.codigo, erro.mensagem, request.url.path, detalhes
    )


async def _tratar_erro_de_validacao(request: Request, erro: RequestValidationError) -> JSONResponse:
    erros = erro.errors()
    if any(detalhe["type"] == "json_invalid" for detalhe in erros):
        return resposta_de_erro(
            HTTPStatus.BAD_REQUEST, JSON_INVALIDO, MENSAGEM_JSON_INVALIDO, request.url.path
        )
    return resposta_de_erro(
        HTTPStatus.UNPROCESSABLE_CONTENT,
        DadosInvalidos.codigo,
        MENSAGEM_DADOS_INVALIDOS,
        request.url.path,
        detalhes_de_validacao(erros),
    )


def _mapear_erro_http(request: Request, status: int) -> tuple[str, str] | None:
    caminho = request.url.path
    match status:
        case HTTPStatus.BAD_REQUEST:
            return JSON_INVALIDO, MENSAGEM_JSON_INVALIDO
        case HTTPStatus.NOT_FOUND:
            return RECURSO_NAO_ENCONTRADO, f"Rota {caminho} não encontrada"
        case HTTPStatus.METHOD_NOT_ALLOWED:
            return METODO_NAO_PERMITIDO, f"Método {request.method} não permitido em {caminho}"
    return None


async def _tratar_erro_http(request: Request, erro: StarletteHTTPException) -> JSONResponse:
    codigo_e_mensagem = _mapear_erro_http(request, erro.status_code)
    if codigo_e_mensagem is None:
        logger.error("HTTPException %s sem código de erro mapeado", erro.status_code)
        return resposta_de_erro(
            HTTPStatus.INTERNAL_SERVER_ERROR, ERRO_INTERNO, MENSAGEM_ERRO_INTERNO, request.url.path
        )
    codigo, mensagem = codigo_e_mensagem
    return resposta_de_erro(HTTPStatus(erro.status_code), codigo, mensagem, request.url.path)


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    app.add_exception_handler(ErroDominio, _tratar_erro_de_dominio)
    app.add_exception_handler(RequestValidationError, _tratar_erro_de_validacao)
    app.add_exception_handler(StarletteHTTPException, _tratar_erro_http)
