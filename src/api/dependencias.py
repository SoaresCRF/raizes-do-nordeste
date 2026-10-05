from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import Connection

from src.application.portas.gateway_pagamento import GatewayPagamento
from src.infrastructure.pagamento.gateway_mock import GatewayPagamentoMock, ResultadoSimulado
from src.infrastructure.seguranca.hash_senha import HashSenha
from src.infrastructure.seguranca.token import TokenJwt


def obter_conexao(request: Request) -> Iterator[Connection]:
    with request.app.state.engine.begin() as conexao:
        yield conexao


# scope="function": o commit acontece antes de a resposta sair. No escopo padrão
# ("request") o cliente receberia sucesso mesmo que o commit falhasse depois.
ConexaoBanco = Annotated[Connection, Depends(obter_conexao, scope="function")]


def obter_hash_senha(request: Request) -> HashSenha:
    return request.app.state.hash_senha


ServicoHashSenha = Annotated[HashSenha, Depends(obter_hash_senha)]


def obter_token_jwt(request: Request) -> TokenJwt:
    return request.app.state.token_jwt


ServicoToken = Annotated[TokenJwt, Depends(obter_token_jwt)]


def obter_gateway_pagamento(
    resultado: Annotated[
        ResultadoSimulado, Header(alias="X-Simular-Resultado")
    ] = ResultadoSimulado.APROVADO,
) -> GatewayPagamento:
    # O header só existe porque o gateway é simulado (Q06): não chega ao caso de uso.
    return GatewayPagamentoMock(resultado)


ServicoGatewayPagamento = Annotated[GatewayPagamento, Depends(obter_gateway_pagamento)]
