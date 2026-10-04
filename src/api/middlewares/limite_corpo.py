from http import HTTPStatus

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.api.erros import CORPO_MUITO_GRANDE, resposta_de_erro

# Mesmo padrão do client_max_body_size do nginx; o maior body da API
# (pedido com itens) tem poucos KB.
TAMANHO_MAXIMO_CORPO_BYTES = 1024 * 1024


class MiddlewareLimiteCorpo:
    """Lê o body antes da aplicação e responde 413 se passar do limite, mesmo sem Content-Length."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        mensagens: list[Message] = []
        tamanho = 0
        while True:
            mensagem = await receive()
            mensagens.append(mensagem)
            if mensagem["type"] != "http.request":
                break
            tamanho += len(mensagem.get("body", b""))
            if tamanho > TAMANHO_MAXIMO_CORPO_BYTES:
                resposta = resposta_de_erro(
                    HTTPStatus.CONTENT_TOO_LARGE,
                    CORPO_MUITO_GRANDE,
                    f"Corpo da requisição excede {TAMANHO_MAXIMO_CORPO_BYTES} bytes",
                    scope["path"],
                )
                await resposta(scope, receive, send)
                return
            if not mensagem.get("more_body", False):
                break

        async def reenviar() -> Message:
            if mensagens:
                return mensagens.pop(0)
            return await receive()

        await self.app(scope, reenviar, send)
