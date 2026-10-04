from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Connection

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
