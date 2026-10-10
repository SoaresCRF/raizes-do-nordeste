import logging
import time
import uuid
from http import HTTPStatus

from sqlalchemy.exc import DBAPIError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.api.erros import ERRO_INTERNO, MENSAGEM_ERRO_INTERNO, resposta_de_erro
from src.infrastructure.logging.logger import request_id_atual

logger = logging.getLogger(__name__)


def _registrar_erro_inesperado(scope: Scope, erro: Exception) -> None:
    if isinstance(erro, DBAPIError):
        # O DETAIL do Postgres repete valores da linha (e-mail, nome): sem a mensagem nem o
        # traceback, só o tipo e o SQLSTATE vão para o log (RNF07).
        logger.error(
            "Erro de banco em %s %s",
            scope["method"],
            scope["path"],
            extra={
                "tipo_erro": type(erro.orig).__name__,
                "sqlstate": getattr(erro.orig, "sqlstate", None),
            },
        )
        return
    logger.exception("Erro inesperado em %s %s", scope["method"], scope["path"])


class MiddlewareRequisicao:
    """Gera o requestId, registra o acesso e converte erro inesperado em 500 padronizado."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        token = request_id_atual.set(str(uuid.uuid4()))
        inicio = time.perf_counter()
        status = HTTPStatus.INTERNAL_SERVER_ERROR
        resposta_iniciada = False

        async def enviar(mensagem: Message) -> None:
            nonlocal status, resposta_iniciada
            if mensagem["type"] == "http.response.start":
                status = mensagem["status"]
                resposta_iniciada = True
            await send(mensagem)

        try:
            await self.app(scope, receive, enviar)
        except Exception as erro:
            _registrar_erro_inesperado(scope, erro)
            if resposta_iniciada:
                raise
            resposta = resposta_de_erro(
                HTTPStatus.INTERNAL_SERVER_ERROR, ERRO_INTERNO, MENSAGEM_ERRO_INTERNO, scope["path"]
            )
            await resposta(scope, receive, send)
        finally:
            # Só o caminho: a query string pode trazer dado pessoal (RNF07).
            logger.info(
                "Requisição concluída",
                extra={
                    "metodo": scope["method"],
                    "caminho": scope["path"],
                    "status": int(status),
                    "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1),
                },
            )
            request_id_atual.reset(token)
