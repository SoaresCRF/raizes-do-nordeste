from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import Connection

from src.application.gateway_pagamento import GatewayPagamento
from src.domain.pagamento import StatusPagamento
from src.infrastructure.gateway_mock import GatewayPagamentoMock
from src.infrastructure.seguranca.token import ServicoTokenJwt


def obter_conexao(request: Request) -> Iterator[Connection]:
    with request.app.state.engine.begin() as conexao:
        yield conexao


ConexaoBanco = Annotated[Connection, Depends(obter_conexao, scope="function")]


def obter_servico_token(request: Request) -> ServicoTokenJwt:
    return request.app.state.servico_token


ServicoToken = Annotated[ServicoTokenJwt, Depends(obter_servico_token)]


DESCRICAO_SIMULAR_RESULTADO = (
    "Só para o gateway simulado: escolhe o resultado do mock: `APROVADO` (padrão), "
    "`RECUSADO` ou `ERRO`."
)


def obter_gateway_pagamento(
    resultado: Annotated[
        StatusPagamento,
        Header(alias="X-Simular-Resultado", description=DESCRICAO_SIMULAR_RESULTADO),
    ] = StatusPagamento.APROVADO,
) -> GatewayPagamento:
    return GatewayPagamentoMock(resultado)


ServicoGatewayPagamento = Annotated[GatewayPagamento, Depends(obter_gateway_pagamento)]
